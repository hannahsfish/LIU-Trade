from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Command, Position, TradePlan
from app.schemas import CreatePlanRequest, ExecutePlanRequest
from app.services.risk_manager import calculate_position_size

SIGNAL_LABELS = {
    "2B_STRUCTURE": "2B结构",
    "MA_CONCENTRATION_BREAKOUT": "均线密集突破",
    "MA_TURN_UP": "MA拐头向上",
}

DEFAULT_ACCOUNT_VALUE = 100_000.0


async def create_plan(req: CreatePlanRequest, db: AsyncSession) -> TradePlan:
    plan = TradePlan(
        symbol=req.symbol,
        expectation=req.expectation,
        clock_direction=req.clock_direction,
        target_price=req.target_price,
        stop_loss=req.stop_loss,
        stop_loss_type=req.stop_loss_type,
        max_loss_pct=req.max_loss_pct,
        entry_price=req.entry_price,
        position_type=req.position_type.value,
        position_size=req.position_size,
        risk_reward_ratio=req.risk_reward_ratio,
        status="DRAFT",
        signal_type=req.signal_type,
        signal_reasoning=req.signal_reasoning,
        created_at=datetime.utcnow(),
    )
    db.add(plan)
    await db.flush()

    suggested_qty = req.position_size
    if not suggested_qty:
        pos_result = calculate_position_size(
            account_value=DEFAULT_ACCOUNT_VALUE,
            entry_price=req.entry_price,
            stop_loss=req.stop_loss,
        )
        suggested_qty = pos_result.shares if pos_result.shares > 0 else None

    signal_label = SIGNAL_LABELS.get(req.signal_type or "", req.signal_type or "")
    priority = "RED" if req.position_type.value == "CONFIRM" else "YELLOW"

    command = Command(
        symbol=req.symbol,
        priority=priority,
        action="BUY",
        headline=f"{req.symbol} {signal_label}买入",
        detail=req.signal_reasoning or req.expectation,
        suggested_price=req.entry_price,
        suggested_quantity=suggested_qty,
        stop_loss=req.stop_loss,
        target_price=req.target_price,
        risk_reward_ratio=req.risk_reward_ratio,
        plan_id=plan.id,
        status="PENDING",
        created_at=datetime.utcnow(),
    )
    db.add(command)
    await db.commit()
    await db.refresh(plan)
    return plan


async def execute_plan(
    plan_id: int, req: ExecutePlanRequest, db: AsyncSession
) -> Position:
    result = await db.execute(select(TradePlan).where(TradePlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise ValueError(f"Plan {plan_id} not found")

    plan.status = "EXECUTED"

    position = Position(
        plan_id=plan.id,
        symbol=plan.symbol,
        quantity=req.actual_quantity,
        entry_price=req.actual_price,
        entry_date=date.today(),
        stop_loss=plan.stop_loss,
        target_price=plan.target_price,
        status="OPEN",
    )
    db.add(position)
    await db.commit()
    await db.refresh(position)
    return position


async def close_position(
    position_id: int, exit_price: float, exit_reason: str, db: AsyncSession
) -> Position:
    result = await db.execute(select(Position).where(Position.id == position_id))
    position = result.scalar_one_or_none()
    if not position:
        raise ValueError(f"Position {position_id} not found")

    position.exit_price = exit_price
    position.exit_date = date.today()
    position.exit_reason = exit_reason
    position.pnl = round((exit_price - position.entry_price) * position.quantity, 2)
    position.pnl_pct = round(
        (exit_price - position.entry_price) / position.entry_price * 100, 2
    )
    position.status = "CLOSED"

    if position.plan_id:
        plan_result = await db.execute(
            select(TradePlan).where(TradePlan.id == position.plan_id)
        )
        plan = plan_result.scalar_one_or_none()
        if plan:
            if exit_price <= plan.stop_loss:
                plan.status = "STOPPED_OUT"
            elif exit_price >= plan.target_price:
                plan.status = "TARGET_HIT"

    await db.commit()
    await db.refresh(position)
    return position
