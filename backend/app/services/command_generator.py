from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Command, Position, Signal
from app.schemas import BuySignalResponse


async def generate_commands_from_signals(
    symbol: str, signals: list[BuySignalResponse], db: AsyncSession
) -> list[Command]:
    commands = []
    for sig in signals:
        if sig.signal_type == "MA_CONCENTRATION_BREAKOUT":
            priority = "RED"
            action = "BUY"
            headline = f"入场机会 {symbol} | 买入 @ ${sig.entry_price} | 止损 ${sig.stop_loss} | 目标 ${sig.target_price}"
        elif sig.signal_type == "2B_STRUCTURE":
            priority = "YELLOW"
            action = "BUY"
            headline = f"试探机会 {symbol} | 轻仓买入 @ ${sig.entry_price} | 止损 ${sig.stop_loss}"
        else:
            priority = "YELLOW"
            action = "WATCH"
            headline = f"关注 {symbol} | {sig.reasoning[:50]}"

        db_signal = Signal(
            symbol=symbol,
            signal_type=sig.signal_type,
            direction="BUY",
            entry_price=sig.entry_price,
            stop_loss=sig.stop_loss,
            target_price=sig.target_price,
            risk_reward_ratio=sig.risk_reward_ratio,
            position_advice=sig.position_advice,
            reasoning=sig.reasoning,
            strength=sig.risk_reward_ratio,
            created_at=datetime.utcnow(),
        )
        db.add(db_signal)
        await db.flush()

        cmd = Command(
            symbol=symbol,
            priority=priority,
            action=action,
            headline=headline,
            detail=sig.reasoning,
            suggested_price=sig.entry_price,
            stop_loss=sig.stop_loss,
            target_price=sig.target_price,
            risk_reward_ratio=sig.risk_reward_ratio,
            signal_id=db_signal.id,
            status="PENDING",
            created_at=datetime.utcnow(),
        )
        db.add(cmd)
        commands.append(cmd)

    await db.commit()
    return commands


async def generate_position_commands(db: AsyncSession) -> list[Command]:
    result = await db.execute(
        select(Position).where(Position.status == "OPEN")
    )
    positions = result.scalars().all()
    commands = []

    for pos in positions:
        cmd = Command(
            symbol=pos.symbol,
            priority="GREEN",
            action="HOLD",
            headline=f"持仓正常 {pos.symbol} | {pos.quantity}股 @ ${pos.entry_price}",
            detail=f"止损: ${pos.stop_loss} | 目标: ${pos.target_price}",
            position_id=pos.id,
            status="PENDING",
            created_at=datetime.utcnow(),
        )
        db.add(cmd)
        commands.append(cmd)

    await db.commit()
    return commands
