from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import TradePlan
from app.schemas import CreatePlanRequest, ExecutePlanRequest, PlanResponse
from app.services.plan_manager import create_plan, execute_plan

router = APIRouter()


@router.get("", response_model=list[PlanResponse])
async def list_plans(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TradePlan).order_by(TradePlan.created_at.desc()))
    plans = result.scalars().all()
    return [
        PlanResponse(
            id=p.id,
            symbol=p.symbol,
            expectation=p.expectation,
            clock_direction=p.clock_direction,
            target_price=p.target_price,
            stop_loss=p.stop_loss,
            stop_loss_type=p.stop_loss_type,
            max_loss_pct=p.max_loss_pct,
            entry_price=p.entry_price,
            position_type=p.position_type,
            position_size=p.position_size,
            risk_reward_ratio=p.risk_reward_ratio,
            status=p.status,
            signal_type=p.signal_type,
            signal_reasoning=p.signal_reasoning,
            created_at=p.created_at,
        )
        for p in plans
    ]


@router.post("", response_model=PlanResponse)
async def create_new_plan(
    req: CreatePlanRequest, db: AsyncSession = Depends(get_db)
):
    plan = await create_plan(req, db)
    return PlanResponse(
        id=plan.id,
        symbol=plan.symbol,
        expectation=plan.expectation,
        clock_direction=plan.clock_direction,
        target_price=plan.target_price,
        stop_loss=plan.stop_loss,
        stop_loss_type=plan.stop_loss_type,
        max_loss_pct=plan.max_loss_pct,
        entry_price=plan.entry_price,
        position_type=plan.position_type,
        position_size=plan.position_size,
        risk_reward_ratio=plan.risk_reward_ratio,
        status=plan.status,
        signal_type=plan.signal_type,
        signal_reasoning=plan.signal_reasoning,
        created_at=plan.created_at,
    )


@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(plan_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TradePlan).where(TradePlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return PlanResponse(
        id=plan.id,
        symbol=plan.symbol,
        expectation=plan.expectation,
        clock_direction=plan.clock_direction,
        target_price=plan.target_price,
        stop_loss=plan.stop_loss,
        stop_loss_type=plan.stop_loss_type,
        max_loss_pct=plan.max_loss_pct,
        entry_price=plan.entry_price,
        position_type=plan.position_type,
        position_size=plan.position_size,
        risk_reward_ratio=plan.risk_reward_ratio,
        status=plan.status,
        signal_type=plan.signal_type,
        signal_reasoning=plan.signal_reasoning,
        created_at=plan.created_at,
    )


@router.post("/{plan_id}/execute")
async def execute_plan_route(
    plan_id: int,
    req: ExecutePlanRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        position = await execute_plan(plan_id, req, db)
        return {"position_id": position.id, "status": "EXECUTED"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{plan_id}")
async def cancel_plan(plan_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TradePlan).where(TradePlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    plan.status = "CANCELLED"
    await db.commit()
    return {"status": "CANCELLED"}
