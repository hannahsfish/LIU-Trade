import asyncio

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Signal, Watchlist
from app.services.scanner import get_scanner_status, run_scan

router = APIRouter()


@router.get("/status")
async def scanner_status():
    return get_scanner_status()


@router.post("/run")
async def trigger_scan(full: bool = Query(False)):
    from app.services.scanner import scanner_state

    status = get_scanner_status()
    if status["running"]:
        return {"message": "扫描正在进行中", "status": status}
    scanner_state.running = True
    scanner_state.current_symbol = "启动中..."
    asyncio.create_task(run_scan(full=full))
    return {"message": "扫描已启动", "full": full}


@router.get("/watchlist")
async def get_watchlist(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Watchlist).order_by(Watchlist.added_at.desc()))
    items = result.scalars().all()

    watchlist_data = []
    for w in items:
        latest_signal = await db.execute(
            select(Signal)
            .where(Signal.symbol == w.symbol, Signal.direction == "BUY")
            .order_by(Signal.created_at.desc())
            .limit(1)
        )
        sig = latest_signal.scalar_one_or_none()

        watchlist_data.append({
            "symbol": w.symbol,
            "added_at": w.added_at.isoformat() if w.added_at else None,
            "notes": w.notes,
            "latest_signal": {
                "signal_type": sig.signal_type,
                "entry_price": sig.entry_price,
                "stop_loss": sig.stop_loss,
                "target_price": sig.target_price,
                "risk_reward_ratio": sig.risk_reward_ratio,
                "position_advice": sig.position_advice,
                "reasoning": sig.reasoning,
                "strength": sig.strength,
                "created_at": sig.created_at.isoformat() if sig.created_at else None,
            } if sig else None,
        })

    return watchlist_data


@router.delete("/watchlist/{symbol}")
async def remove_from_watchlist(symbol: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Watchlist).where(Watchlist.symbol == symbol.upper()))
    item = result.scalar_one_or_none()
    if not item:
        return {"message": "不在关注列表中"}
    await db.delete(item)
    await db.commit()
    return {"message": f"已移除 {symbol.upper()}"}


@router.post("/watchlist/{symbol}")
async def add_to_watchlist(symbol: str, db: AsyncSession = Depends(get_db)):
    sym = symbol.upper()
    existing = await db.execute(select(Watchlist).where(Watchlist.symbol == sym))
    if existing.scalar_one_or_none():
        return {"message": f"{sym} 已在关注列表中"}
    from datetime import datetime
    db.add(Watchlist(symbol=sym, added_at=datetime.utcnow(), notes="手动添加"))
    await db.commit()
    return {"message": f"已添加 {sym}"}
