import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from dotenv import load_dotenv
from fastapi import FastAPI
from zoneinfo import ZoneInfo

load_dotenv()
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db, async_session
from app.routers import analysis, backtest, commands, plans, positions, scanner, signals, stocks
from app.services.scanner import run_scan
from app.services.data_fetcher import get_realtime_price

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")


def _seconds_until(hour: int, minute: int) -> float:
    now = datetime.now(ET)
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


SCAN_SCHEDULE = [
    (range(0, 5), 16, 30, False, "Post-market scan (16:30 ET)"),
    (range(5, 6), 10, 0, True, "Weekend full scan"),
]


def _next_scan():
    now = datetime.now(ET)
    candidates = []
    for weekdays, hour, minute, full, label in SCAN_SCHEDULE:
        for offset in range(7):
            candidate = (now + timedelta(days=offset)).replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )
            if candidate > now and candidate.weekday() in weekdays:
                candidates.append((candidate, full, label))
                break
    candidates.sort(key=lambda x: x[0])
    return candidates[0] if candidates else None


async def _scheduled_scanner():
    while True:
        scan = _next_scan()
        if not scan:
            await asyncio.sleep(3600)
            continue
        target, full, label = scan
        wait = (target - datetime.now(ET)).total_seconds()
        if wait > 0:
            await asyncio.sleep(wait)
        logger.info(f"{label} starting")
        await run_scan(full=full)


async def _update_position_prices():
    """Update realtime prices for open positions every 15 minutes during market hours."""
    from sqlalchemy import select
    from app.models import Position

    while True:
        # Check if US market is open (9:30-16:00 ET)
        now_et = datetime.now(ET)
        market_open = now_et.hour >= 9 and now_et.hour < 16
        weekday = now_et.weekday()

        if market_open and weekday < 5:
            try:
                async with async_session() as db:
                    result = await db.execute(
                        select(Position).where(Position.status == "OPEN")
                    )
                    positions = result.scalars().all()

                    for pos in positions:
                        price = await get_realtime_price(pos.symbol)
                        if price:
                            logger.info(f"{pos.symbol}: realtime ${price}")

                    await db.commit()
                    if positions:
                        logger.info(f"Price update: {len(positions)} positions")
            except Exception as e:
                logger.error(f"Price update failed: {e}")

        await asyncio.sleep(900)  # 15 minutes


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    scanner_task = asyncio.create_task(_scheduled_scanner())
    price_task = asyncio.create_task(_update_position_prices())
    yield
    scanner_task.cancel()
    price_task.cancel()


app = FastAPI(
    title="LIU Trading System",
    description="LIU 框架自动分析美股并生成操作指令",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stocks.router, prefix="/api/stocks", tags=["stocks"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(signals.router, prefix="/api/signals", tags=["signals"])
app.include_router(plans.router, prefix="/api/plans", tags=["plans"])
app.include_router(positions.router, prefix="/api/positions", tags=["positions"])
app.include_router(commands.router, prefix="/api/commands", tags=["commands"])
app.include_router(scanner.router, prefix="/api/scanner", tags=["scanner"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["backtest"])


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
