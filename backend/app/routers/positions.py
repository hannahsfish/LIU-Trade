from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Position
from app.schemas import ClosePositionRequest, PositionResponse
from app.services.plan_manager import close_position

router = APIRouter()


@router.get("", response_model=list[PositionResponse])
async def list_positions(
    status: str = "OPEN", db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Position)
        .where(Position.status == status)
        .order_by(Position.entry_date.desc())
    )
    positions = result.scalars().all()
    return [
        PositionResponse(
            id=p.id,
            plan_id=p.plan_id,
            symbol=p.symbol,
            quantity=p.quantity,
            entry_price=p.entry_price,
            entry_date=p.entry_date,
            stop_loss=p.stop_loss,
            target_price=p.target_price,
            pnl=p.pnl,
            pnl_pct=p.pnl_pct,
            status=p.status,
        )
        for p in positions
    ]


@router.get("/history", response_model=list[PositionResponse])
async def position_history(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Position)
        .where(Position.status == "CLOSED")
        .order_by(Position.exit_date.desc())
    )
    positions = result.scalars().all()
    return [
        PositionResponse(
            id=p.id,
            plan_id=p.plan_id,
            symbol=p.symbol,
            quantity=p.quantity,
            entry_price=p.entry_price,
            entry_date=p.entry_date,
            stop_loss=p.stop_loss,
            target_price=p.target_price,
            pnl=p.pnl,
            pnl_pct=p.pnl_pct,
            status=p.status,
        )
        for p in positions
    ]


@router.get("/{position_id}", response_model=PositionResponse)
async def get_position(position_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Position).where(Position.id == position_id))
    pos = result.scalar_one_or_none()
    if not pos:
        raise HTTPException(status_code=404, detail="Position not found")
    return PositionResponse(
        id=pos.id,
        plan_id=pos.plan_id,
        symbol=pos.symbol,
        quantity=pos.quantity,
        entry_price=pos.entry_price,
        entry_date=pos.entry_date,
        stop_loss=pos.stop_loss,
        target_price=pos.target_price,
        pnl=pos.pnl,
        pnl_pct=pos.pnl_pct,
        status=pos.status,
    )


@router.post("/{position_id}/close")
async def close_position_route(
    position_id: int,
    req: ClosePositionRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        pos = await close_position(position_id, req.exit_price, req.exit_reason, db)
        return {
            "position_id": pos.id,
            "pnl": pos.pnl,
            "pnl_pct": pos.pnl_pct,
            "status": "CLOSED",
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
