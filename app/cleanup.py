import asyncio
from datetime import datetime, timedelta, UTC
from sqlalchemy import delete

from database import async_session, PriceTick


async def delete_old_ticks():
    cutoff = datetime.now(UTC) - timedelta(hours=1)

    async with async_session() as session:
        result = await session.execute(
            delete(PriceTick).where(PriceTick.timestamp < cutoff)
        )
        await session.commit()
        print(f"cleanup: deleted {result.rowcount} old ticks")


async def cleanup_worker():
    while True:
        await asyncio.sleep(3600)   
        try:
            await delete_old_ticks()
        except Exception as e:
            print(f"cleanup error: {e}")