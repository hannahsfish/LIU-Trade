import asyncio
from app.database import async_session
from sqlalchemy import text

async def check():
    async with async_session() as db:
        r = await db.execute(text("SELECT date, close FROM price_history WHERE symbol='BSX' ORDER BY date DESC LIMIT 5"))
        print("BSX latest prices:")
        for row in r:
            print(f"  {row[0]}: {row[1]}")

        r2 = await db.execute(text("SELECT date FROM price_history WHERE symbol='BSX' ORDER BY date DESC LIMIT 1"))
        latest = r2.scalar()
        print(f"Latest date: {latest}")

asyncio.run(check())
