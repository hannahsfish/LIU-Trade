from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import OHLCVBar, OHLCVResponse, StockSearchResult
from app.services.data_fetcher import fetch_ohlcv, fetch_weekly_ohlcv, get_stock_info, search_stocks

router = APIRouter()


@router.get("/search", response_model=list[StockSearchResult])
async def search(q: str = Query(..., min_length=1)):
    return await search_stocks(q)


@router.get("/{symbol}", response_model=StockSearchResult)
async def get_stock(symbol: str, db: AsyncSession = Depends(get_db)):
    info = await get_stock_info(symbol.upper(), db)
    if not info:
        return StockSearchResult(symbol=symbol.upper())
    return StockSearchResult(**info)


@router.get("/{symbol}/ohlcv", response_model=OHLCVResponse)
async def get_ohlcv(
    symbol: str,
    interval: str = Query("daily", regex="^(daily|weekly)$"),
    period: str = Query("2y"),
    db: AsyncSession = Depends(get_db),
):
    sym = symbol.upper()
    if interval == "weekly":
        df = await fetch_weekly_ohlcv(sym, db, period)
    else:
        df = await fetch_ohlcv(sym, db, period)

    bars = []
    if not df.empty:
        for _, row in df.iterrows():
            bars.append(
                OHLCVBar(
                    date=row["date"],
                    open=round(row["open"], 2),
                    high=round(row["high"], 2),
                    low=round(row["low"], 2),
                    close=round(row["close"], 2),
                    volume=int(row["volume"]),
                )
            )

    return OHLCVResponse(symbol=sym, interval=interval, bars=bars)
