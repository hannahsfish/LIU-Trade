import asyncio
from app.database import async_session
from app.services.data_fetcher import fetch_ohlcv

async def test():
    async with async_session() as db:
        df = await fetch_ohlcv("BSX", db)
        print(f"After fetch: {len(df)} rows")
        if len(df) > 0:
            latest = df.iloc[-1]
            print(f"Latest: {latest['date']} - ${latest['close']}")

asyncio.run(test())
