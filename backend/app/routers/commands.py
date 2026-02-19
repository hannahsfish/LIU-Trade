from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Command, Position, TradePlan
from app.schemas import CommandResponse, ExecuteCommandRequest
from app.services.command_generator import sync_position_commands

router = APIRouter()

PRIORITY_ORDER = {"RED": 0, "YELLOW": 1, "GREEN": 2}


@router.get("", response_model=list[CommandResponse])
async def list_commands(db: AsyncSession = Depends(get_db)):
    await sync_position_commands(db)

    result = await db.execute(
        select(Command)
        .where(Command.status == "PENDING")
        .order_by(Command.created_at.desc())
    )
    commands = result.scalars().all()

    sorted_commands = sorted(
        commands, key=lambda c: PRIORITY_ORDER.get(c.priority, 99)
    )

    return [
        CommandResponse(
            id=c.id,
            symbol=c.symbol,
            priority=c.priority,
            action=c.action,
            headline=c.headline,
            detail=c.detail,
            suggested_price=c.suggested_price,
            suggested_quantity=c.suggested_quantity,
            stop_loss=c.stop_loss,
            target_price=c.target_price,
            risk_reward_ratio=c.risk_reward_ratio,
            status=c.status,
            created_at=c.created_at,
        )
        for c in sorted_commands
    ]


@router.post("/{command_id}/execute")
async def execute_command(
    command_id: int,
    req: ExecuteCommandRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Command).where(Command.id == command_id))
    cmd = result.scalar_one_or_none()
    if not cmd:
        raise HTTPException(status_code=404, detail="Command not found")

    cmd.status = "EXECUTED"
    cmd.actual_price = req.actual_price
    cmd.actual_quantity = req.actual_quantity
    cmd.executed_at = datetime.utcnow()

    position_id = None
    if cmd.plan_id:
        plan_result = await db.execute(
            select(TradePlan).where(TradePlan.id == cmd.plan_id)
        )
        plan = plan_result.scalar_one_or_none()
        if plan:
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
            await db.flush()
            position_id = position.id

    await db.commit()

    return {"status": "EXECUTED", "command_id": cmd.id, "position_id": position_id}


@router.post("/{command_id}/dismiss")
async def dismiss_command(command_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Command).where(Command.id == command_id))
    cmd = result.scalar_one_or_none()
    if not cmd:
        raise HTTPException(status_code=404, detail="Command not found")

    cmd.status = "DISMISSED"
    await db.commit()
    return {"status": "DISMISSED"}
