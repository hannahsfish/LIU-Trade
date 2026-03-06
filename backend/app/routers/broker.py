import logging
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import BrokerOrder, Command
from app.schemas import BrokerOrderResponse
from app.services.futu_broker import futu_broker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/broker", tags=["broker"])


@router.get("/status")
async def broker_status():
    result = {
        "connected": futu_broker.is_connected,
        "trd_env": futu_broker.trd_env_label,
    }
    if futu_broker.is_connected:
        try:
            info = await futu_broker.get_account_info()
            result["account"] = asdict(info)
        except Exception as e:
            result["account_error"] = str(e)
    return result


@router.post("/connect")
async def broker_connect():
    if futu_broker.is_connected:
        return {"status": "already_connected"}
    try:
        await futu_broker.connect()
        await futu_broker.unlock_trade()
        return {"status": "connected", "trd_env": futu_broker.trd_env_label}
    except Exception as e:
        logger.exception("Failed to connect to FutuOpenD")
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/disconnect")
async def broker_disconnect():
    if not futu_broker.is_connected:
        return {"status": "already_disconnected"}
    await futu_broker.disconnect()
    return {"status": "disconnected"}


@router.get("/orders", response_model=list[BrokerOrderResponse])
async def list_broker_orders(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(BrokerOrder).order_by(BrokerOrder.created_at.desc())
    )
    return result.scalars().all()


@router.post("/orders/{broker_order_id}/cancel")
async def cancel_broker_order(
    broker_order_id: int, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(BrokerOrder).where(BrokerOrder.id == broker_order_id)
    )
    bo = result.scalar_one_or_none()
    if not bo:
        raise HTTPException(status_code=404, detail="Broker order not found")
    if bo.status not in ("SUBMITTED", "PARTIAL"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel order in {bo.status} state")
    if not futu_broker.is_connected:
        raise HTTPException(status_code=400, detail="Broker not connected")

    try:
        await futu_broker.cancel_order(bo.futu_order_id)
    except Exception as e:
        logger.exception("Cancel order failed: %s", bo.futu_order_id)
        raise HTTPException(status_code=502, detail=str(e))

    bo.status = "CANCELLED"

    cmd_result = await db.execute(
        select(Command).where(Command.id == bo.command_id)
    )
    cmd = cmd_result.scalar_one_or_none()
    if cmd and cmd.status == "SUBMITTING":
        cmd.status = "PENDING"

    await db.commit()
    return {"status": "CANCELLED", "broker_order_id": bo.id, "command_id": bo.command_id}


@router.get("/account")
async def broker_account():
    if not futu_broker.is_connected:
        raise HTTPException(status_code=400, detail="Broker not connected")
    try:
        info = await futu_broker.get_account_info()
        return asdict(info)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/positions")
async def broker_positions():
    if not futu_broker.is_connected:
        raise HTTPException(status_code=400, detail="Broker not connected")
    try:
        positions = await futu_broker.get_positions()
        return [asdict(p) for p in positions]
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
