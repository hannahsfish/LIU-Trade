import logging
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import BrokerOrder, Command, Position, TradePlan
from app.schemas import CommandResponse, ExecuteCommandRequest
from app.services.command_generator import sync_position_commands
from app.services.futu_broker import futu_broker

logger = logging.getLogger(__name__)

router = APIRouter()

PRIORITY_ORDER = {"RED": 0, "YELLOW": 1, "GREEN": 2}


@router.get("", response_model=list[CommandResponse])
async def list_commands(db: AsyncSession = Depends(get_db)):
    await sync_position_commands(db)

    result = await db.execute(
        select(Command)
        .where(Command.status.in_(["PENDING", "SUBMITTING"]))
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

    if futu_broker.is_connected:
        return await _execute_via_broker(cmd, req, db)

    return await _execute_local(cmd, req, db)


async def _execute_via_broker(
    cmd: Command, req: ExecuteCommandRequest, db: AsyncSession
):
    side = "BUY" if cmd.action in ("BUY",) else "SELL"
    order_type = req.order_type if req.order_type in ("LIMIT", "MARKET") else "LIMIT"

    try:
        placed = await futu_broker.place_order(
            symbol=cmd.symbol,
            side=side,
            price=req.actual_price,
            quantity=req.actual_quantity,
            order_type=order_type,
        )
    except Exception as e:
        logger.exception("Futu place_order failed for command %s", cmd.id)
        raise HTTPException(status_code=502, detail=f"Broker order failed: {e}")

    broker_order = BrokerOrder(
        command_id=cmd.id,
        futu_order_id=placed.futu_order_id,
        symbol=cmd.symbol,
        side=side,
        order_type=order_type,
        price=req.actual_price,
        quantity=req.actual_quantity,
        status="SUBMITTED",
    )
    db.add(broker_order)

    cmd.status = "SUBMITTING"
    cmd.actual_price = req.actual_price
    cmd.actual_quantity = req.actual_quantity

    await db.commit()

    return {
        "status": "SUBMITTING",
        "command_id": cmd.id,
        "broker_order_id": broker_order.id,
        "futu_order_id": placed.futu_order_id,
    }


async def _execute_local(
    cmd: Command, req: ExecuteCommandRequest, db: AsyncSession
):
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
