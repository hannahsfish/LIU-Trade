import os
from datetime import datetime, date as date_type, timedelta

import pandas as pd
import requests
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PriceHistory, PriceHistoryWeekly, Stock
from app.services.rate_limiter import av_limiter

AV_BASE = "https://www.alphavantage.co/query"
API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")


def _av_request_sync(params: dict) -> dict:
    params["apikey"] = API_KEY
    resp = requests.get(AV_BASE, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if "Error Message" in data:
        raise ValueError(data["Error Message"])
    if "Note" in data or "Information" in data:
        raise ValueError(data.get("Note") or data.get("Information"))
    return data


async def _av_request(params: dict) -> dict:
    await av_limiter.acquire()
    return _av_request_sync(params)


async def search_stocks(query: str) -> list[dict]:
    try:
        data = await _av_request({"function": "SYMBOL_SEARCH", "keywords": query})
        matches = data.get("bestMatches", [])
        return [
            {
                "symbol": m.get("1. symbol", ""),
                "name": m.get("2. name"),
                "sector": None,
                "industry": None,
                "market_cap": None,
            }
            for m in matches
            if m.get("4. region") == "United States"
        ]
    except Exception:
        return []


async def get_stock_info(symbol: str, db: AsyncSession) -> dict | None:
    result = await db.execute(select(Stock).where(Stock.symbol == symbol))
    stock = result.scalar_one_or_none()
    if stock:
        return {
            "symbol": stock.symbol,
            "name": stock.name,
            "sector": stock.sector,
            "industry": stock.industry,
            "market_cap": stock.market_cap,
        }

    try:
        data = await _av_request({"function": "OVERVIEW", "symbol": symbol})
        if not data or data.get("Symbol") is None:
            return None

        market_cap_raw = data.get("MarketCapitalization")
        market_cap = int(market_cap_raw) if market_cap_raw and market_cap_raw != "None" else None

        new_stock = Stock(
            symbol=data.get("Symbol", symbol),
            name=data.get("Name"),
            sector=data.get("Sector"),
            industry=data.get("Industry"),
            market_cap=market_cap,
            last_updated=datetime.utcnow(),
        )
        db.add(new_stock)
        await db.commit()
        return {
            "symbol": new_stock.symbol,
            "name": new_stock.name,
            "sector": new_stock.sector,
            "industry": new_stock.industry,
            "market_cap": new_stock.market_cap,
        }
    except Exception:
        return None


def _parse_av_daily(data: dict) -> pd.DataFrame:
    ts = data.get("Time Series (Daily)", {})
    if not ts:
        return pd.DataFrame()

    rows = []
    for date_str, values in ts.items():
        rows.append(
            {
                "date": datetime.strptime(date_str, "%Y-%m-%d").date(),
                "open": float(values["1. open"]),
                "high": float(values["2. high"]),
                "low": float(values["3. low"]),
                "close": float(values["4. close"]),
                "volume": int(values["5. volume"]),
            }
        )
    df = pd.DataFrame(rows)
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def _parse_av_weekly(data: dict) -> pd.DataFrame:
    ts = data.get("Weekly Time Series", {})
    if not ts:
        return pd.DataFrame()

    rows = []
    for date_str, values in ts.items():
        rows.append(
            {
                "date": datetime.strptime(date_str, "%Y-%m-%d").date(),
                "open": float(values["1. open"]),
                "high": float(values["2. high"]),
                "low": float(values["3. low"]),
                "close": float(values["4. close"]),
                "volume": int(values["5. volume"]),
            }
        )
    df = pd.DataFrame(rows)
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


async def _upsert_daily_rows(symbol: str, df: pd.DataFrame, db: AsyncSession):
    for _, row in df.iterrows():
        existing = await db.execute(
            select(PriceHistory).where(
                PriceHistory.symbol == symbol,
                PriceHistory.date == row["date"],
            )
        )
        record = existing.scalar_one_or_none()
        if record is None:
            db.add(
                PriceHistory(
                    symbol=symbol,
                    date=row["date"],
                    open=round(float(row["open"]), 4),
                    high=round(float(row["high"]), 4),
                    low=round(float(row["low"]), 4),
                    close=round(float(row["close"]), 4),
                    volume=int(row["volume"]),
                )
            )
        else:
            record.open = round(float(row["open"]), 4)
            record.high = round(float(row["high"]), 4)
            record.low = round(float(row["low"]), 4)
            record.close = round(float(row["close"]), 4)
            record.volume = int(row["volume"])
    await db.commit()


async def _load_daily_from_db(symbol: str, db: AsyncSession) -> pd.DataFrame:
    result = await db.execute(
        select(PriceHistory)
        .where(PriceHistory.symbol == symbol)
        .order_by(PriceHistory.date)
    )
    rows = result.scalars().all()
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(
        [
            {
                "date": r.date,
                "open": r.open,
                "high": r.high,
                "low": r.low,
                "close": r.close,
                "volume": r.volume,
            }
            for r in rows
        ]
    )


async def get_latest_date(symbol: str, db: AsyncSession) -> date_type | None:
    result = await db.execute(
        select(func.max(PriceHistory.date)).where(PriceHistory.symbol == symbol)
    )
    return result.scalar_one_or_none()


async def get_cached_row_count(symbol: str, db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count()).select_from(PriceHistory).where(PriceHistory.symbol == symbol)
    )
    return result.scalar_one()


def is_data_stale(latest_date: date_type | None, max_age_days: int = 1) -> bool:
    if latest_date is None:
        return True
    today = date_type.today()
    weekday = today.weekday()
    if weekday == 0:
        threshold = today - timedelta(days=3)
    elif weekday == 6:
        threshold = today - timedelta(days=2)
    else:
        threshold = today - timedelta(days=max_age_days)
    return latest_date < threshold


async def fetch_ohlcv(
    symbol: str, db: AsyncSession, period: str = "2y"
) -> pd.DataFrame:
    row_count = await get_cached_row_count(symbol, db)
    latest = await get_latest_date(symbol, db)

    if row_count >= 120 and not is_data_stale(latest):
        return await _load_daily_from_db(symbol, db)

    try:
        outputsize = "compact" if row_count >= 120 else "full"
        data = await _av_request({
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": outputsize,
        })
        df = _parse_av_daily(data)
    except Exception:
        if row_count > 0:
            return await _load_daily_from_db(symbol, db)
        return pd.DataFrame()

    if df.empty:
        return await _load_daily_from_db(symbol, db)

    await _upsert_daily_rows(symbol, df, db)
    return await _load_daily_from_db(symbol, db)


async def fetch_weekly_ohlcv(
    symbol: str, db: AsyncSession, period: str = "5y"
) -> pd.DataFrame:
    result = await db.execute(
        select(PriceHistoryWeekly)
        .where(PriceHistoryWeekly.symbol == symbol)
        .order_by(PriceHistoryWeekly.week_start)
    )
    rows = result.scalars().all()

    if len(rows) > 50:
        latest = max(r.week_start for r in rows)
        if not is_data_stale(latest, max_age_days=7):
            return pd.DataFrame(
                [
                    {
                        "date": r.week_start,
                        "open": r.open,
                        "high": r.high,
                        "low": r.low,
                        "close": r.close,
                        "volume": r.volume,
                    }
                    for r in rows
                ]
            )

    try:
        data = await _av_request({
            "function": "TIME_SERIES_WEEKLY",
            "symbol": symbol,
        })
        df = _parse_av_weekly(data)
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        if rows:
            return pd.DataFrame(
                [{"date": r.week_start, "open": r.open, "high": r.high,
                  "low": r.low, "close": r.close, "volume": r.volume}
                 for r in rows]
            )
        return pd.DataFrame()

    for _, row in df.iterrows():
        existing = await db.execute(
            select(PriceHistoryWeekly).where(
                PriceHistoryWeekly.symbol == symbol,
                PriceHistoryWeekly.week_start == row["date"],
            )
        )
        if existing.scalar_one_or_none() is None:
            db.add(
                PriceHistoryWeekly(
                    symbol=symbol,
                    week_start=row["date"],
                    open=round(float(row["open"]), 4),
                    high=round(float(row["high"]), 4),
                    low=round(float(row["low"]), 4),
                    close=round(float(row["close"]), 4),
                    volume=int(row["volume"]),
                )
            )
    await db.commit()

    result = await db.execute(
        select(PriceHistoryWeekly)
        .where(PriceHistoryWeekly.symbol == symbol)
        .order_by(PriceHistoryWeekly.week_start)
    )
    rows = result.scalars().all()
    return pd.DataFrame(
        [
            {
                "date": r.week_start,
                "open": r.open,
                "high": r.high,
                "low": r.low,
                "close": r.close,
                "volume": r.volume,
            }
            for r in rows
        ]
    )
