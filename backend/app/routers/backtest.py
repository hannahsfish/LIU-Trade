from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.backtester import BacktestConfig, Backtester
from app.services.data_fetcher import fetch_ohlcv
from app.services.universe import get_universe

router = APIRouter()


class BacktestRequest(BaseModel):
    initial_capital: float = 100_000.0
    risk_per_trade: float = 0.02
    max_holding_days: int = 60
    trailing_stop_pct: float | None = None
    signal_types: list[str] | None = None
    cooldown_days: int = 15
    trend_filter: bool = False
    stop_loss_atr_mult: float | None = 2.0


def _make_config(req: BacktestRequest) -> BacktestConfig:
    return BacktestConfig(
        initial_capital=req.initial_capital,
        risk_per_trade=req.risk_per_trade,
        max_holding_days=req.max_holding_days,
        trailing_stop_pct=req.trailing_stop_pct,
        signal_types=req.signal_types,
        cooldown_days=req.cooldown_days,
        trend_filter=req.trend_filter,
        stop_loss_atr_mult=req.stop_loss_atr_mult,
    )


def _serialize_result(result) -> dict:
    data = asdict(result)
    for t in data.get("trades", []):
        t["entry_date"] = str(t["entry_date"])
        t["exit_date"] = str(t["exit_date"])
    data["equity_curve"] = [
        {"date": str(pt["date"]), "equity": round(pt["equity"], 2)}
        for pt in data.get("equity_curve", [])
    ]
    by_type = data.get("stats", {}).get("by_signal_type", {})
    for st in by_type.values():
        st["win_rate"] = round(st.get("win_count", 0) / st["trade_count"] * 100, 2) if st.get("trade_count") else 0.0
        st["profit_factor"] = round(st["gross_profit"] / st["gross_loss"], 2) if st.get("gross_loss", 0) > 0 else None
    return data


@router.post("/universe")
async def backtest_universe(
    req: BacktestRequest = BacktestRequest(),
    db: AsyncSession = Depends(get_db),
):
    symbols = get_universe()
    config = _make_config(req)

    summaries = []
    for sym in symbols:
        df = await fetch_ohlcv(sym, db)
        if df.empty or len(df) < 120:
            continue
        bt = Backtester(config)
        result = bt.run(df, sym)
        if result.trades:
            summaries.append({
                "symbol": sym,
                "trade_count": result.stats.trade_count,
                "win_rate": result.stats.win_rate,
                "total_return_pct": result.stats.total_return_pct,
                "profit_factor": result.stats.profit_factor,
                "max_drawdown_pct": result.stats.max_drawdown_pct,
                "sharpe_ratio": result.stats.sharpe_ratio,
            })

    summaries.sort(key=lambda x: x["total_return_pct"], reverse=True)
    return {
        "total_symbols": len(symbols),
        "symbols_with_trades": len(summaries),
        "results": summaries,
    }


@router.post("/{symbol}")
async def backtest_symbol(
    symbol: str,
    req: BacktestRequest = BacktestRequest(),
    db: AsyncSession = Depends(get_db),
):
    df = await fetch_ohlcv(symbol.upper(), db)
    if df.empty:
        return {"error": f"无法获取 {symbol} 的历史数据"}

    config = _make_config(req)
    bt = Backtester(config)
    result = bt.run(df, symbol.upper())
    return _serialize_result(result)


@router.post("/{symbol}/compare")
async def compare_signals(
    symbol: str,
    req: BacktestRequest = BacktestRequest(),
    db: AsyncSession = Depends(get_db),
):
    df = await fetch_ohlcv(symbol.upper(), db)
    if df.empty:
        return {"error": f"无法获取 {symbol} 的历史数据"}

    signal_types = ["2B_STRUCTURE", "MA_CONCENTRATION_BREAKOUT", "MA_TURN_UP"]
    comparison = {}

    for sig_type in signal_types:
        config = BacktestConfig(
            initial_capital=req.initial_capital,
            risk_per_trade=req.risk_per_trade,
            max_holding_days=req.max_holding_days,
            trailing_stop_pct=req.trailing_stop_pct,
            signal_types=[sig_type],
        )
        bt = Backtester(config)
        result = bt.run(df, symbol.upper())
        comparison[sig_type] = {
            "trade_count": result.stats.trade_count,
            "win_rate": result.stats.win_rate,
            "total_return_pct": result.stats.total_return_pct,
            "avg_win_pct": result.stats.avg_win_pct,
            "avg_loss_pct": result.stats.avg_loss_pct,
            "profit_factor": result.stats.profit_factor,
            "max_drawdown_pct": result.stats.max_drawdown_pct,
            "sharpe_ratio": result.stats.sharpe_ratio,
        }

    all_config = _make_config(req)
    all_config.signal_types = None
    bt_all = Backtester(all_config)
    result_all = bt_all.run(df, symbol.upper())

    return {
        "symbol": symbol.upper(),
        "combined": {
            "trade_count": result_all.stats.trade_count,
            "win_rate": result_all.stats.win_rate,
            "total_return_pct": result_all.stats.total_return_pct,
            "profit_factor": result_all.stats.profit_factor,
            "sharpe_ratio": result_all.stats.sharpe_ratio,
        },
        "by_signal_type": comparison,
    }
