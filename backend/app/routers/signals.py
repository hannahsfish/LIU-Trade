from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Signal, Watchlist
from app.schemas import BuySignalResponse
from app.services.data_fetcher import fetch_ohlcv
from app.services.signal_generator import scan_buy_signals

router = APIRouter()


@router.get("/{symbol}/buy", response_model=list[BuySignalResponse])
async def get_buy_signals(symbol: str, db: AsyncSession = Depends(get_db)):
    sym = symbol.upper()
    df = await fetch_ohlcv(sym, db)
    if df.empty:
        return []
    return scan_buy_signals(df, sym)


@router.get("/opportunities", response_model=list[BuySignalResponse])
async def get_opportunities(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Watchlist))
    watchlist = result.scalars().all()

    all_signals = []
    for item in watchlist:
        df = await fetch_ohlcv(item.symbol, db)
        if not df.empty:
            signals = scan_buy_signals(df, item.symbol)
            all_signals.extend(signals)

    all_signals.sort(key=lambda s: s.risk_reward_ratio, reverse=True)
    return all_signals
