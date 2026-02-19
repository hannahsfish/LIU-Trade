from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import TechnicalAnalysis
from app.services.data_fetcher import fetch_ohlcv
from app.services.technical import run_full_analysis

router = APIRouter()


@router.get("/{symbol}/technical", response_model=TechnicalAnalysis)
async def get_technical_analysis(
    symbol: str, db: AsyncSession = Depends(get_db)
):
    sym = symbol.upper()
    df = await fetch_ohlcv(sym, db)

    if df.empty:
        return TechnicalAnalysis(
            symbol=sym,
            last_price=0,
            last_date="2000-01-01",
            mas=[],
            slopes=[],
            deduction_prices=[],
        )

    result = run_full_analysis(df)
    result["symbol"] = sym
    return TechnicalAnalysis(**result)
