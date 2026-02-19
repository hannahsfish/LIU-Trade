from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Position, TradePlan
from app.schemas import CreatePlanRequest, ExecutePlanRequest


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
