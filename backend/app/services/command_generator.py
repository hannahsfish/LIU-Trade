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


async def _get_latest_close(symbol: str, db: AsyncSession) -> float | None:
    from app.models import PriceHistory
    from app.services.data_fetcher import get_realtime_price

    # Try realtime price first (15min delayed during market hours)
    realtime = await get_realtime_price(symbol)
    if realtime:
        return realtime
    # Fall back to cached daily close
    result = await db.execute(
        select(PriceHistory.close)
        .where(PriceHistory.symbol == symbol)
        .order_by(PriceHistory.date.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def _classify_position(
    current_price: float,
    entry_price: float,
    stop_loss: float,
    target_price: float,
) -> tuple[str, str, str, str]:
    pnl_pct = (current_price - entry_price) / entry_price * 100
    stop_dist = (current_price - stop_loss) / current_price * 100
    target_dist = (target_price - current_price) / current_price * 100

    pnl_str = f"{'盈利' if pnl_pct >= 0 else '亏损'}{abs(pnl_pct):.1f}%"

    if current_price <= stop_loss:
        return (
            "RED", "STOP_LOSS",
            "已触止损，立即平仓",
            f"当前价 {current_price} 已跌破止损位 {stop_loss}，{pnl_str}。立即执行止损。",
        )

    if stop_dist <= 3:
        return (
            "RED", "WATCH",
            "接近止损位，密切关注",
            f"当前价 {current_price} 距止损 {stop_loss} 仅 {stop_dist:.1f}%，{pnl_str}。准备好止损指令。",
        )

    if current_price >= target_price:
        return (
            "RED", "SELL",
            "已达目标价，考虑止盈",
            f"当前价 {current_price} 已达目标 {target_price}，{pnl_str}。可分批止盈或上移止损。",
        )

    if target_dist <= 5:
        return (
            "YELLOW", "WATCH",
            "接近目标价，准备止盈",
            f"当前价 {current_price} 距目标 {target_price} 仅 {target_dist:.1f}%，{pnl_str}。关注量价配合。",
        )

    return (
        "GREEN", "HOLD",
        "继续持有观察",
        f"当前价 {current_price}，{pnl_str}。距止损 {stop_dist:.1f}%，距目标 {target_dist:.1f}%。无需操作。",
    )


async def sync_position_commands(db: AsyncSession) -> None:
    from sqlalchemy import delete as sql_delete

    positions = await db.execute(
        select(Position).where(Position.status == "OPEN")
    )
    open_positions = positions.scalars().all()

    await db.execute(
        sql_delete(Command).where(
            Command.position_id.isnot(None),
            Command.status == "PENDING",
        )
    )

    for pos in open_positions:
        current_price = await _get_latest_close(pos.symbol, db)
        if current_price is None:
            current_price = pos.entry_price

        priority, action, headline_suffix, detail = _classify_position(
            current_price, pos.entry_price, pos.stop_loss, pos.target_price,
        )

        db.add(Command(
            symbol=pos.symbol,
            priority=priority,
            action=action,
            headline=f"{pos.symbol} {headline_suffix}",
            detail=detail,
            suggested_price=current_price,
            suggested_quantity=pos.quantity,
            stop_loss=pos.stop_loss,
            target_price=pos.target_price,
            plan_id=pos.plan_id,
            position_id=pos.id,
            status="PENDING",
            created_at=datetime.utcnow(),
        ))

    await db.flush()
