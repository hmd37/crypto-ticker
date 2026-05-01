import asyncio
from datetime import datetime, timedelta, UTC
from sqlalchemy import delete

from database import async_session, PriceTick


async def delete_old_ticks(session=None):
    cutoff = datetime.now(UTC) - timedelta(days=7)

    if session is None:
        async with async_session() as s:
            result = await s.execute(
                delete(PriceTick).where(PriceTick.timestamp < cutoff)
            )
            await s.commit()
            print(f"cleanup: deleted {result.rowcount} old ticks")
    else:
        result = await session.execute(
            delete(PriceTick).where(PriceTick.timestamp < cutoff)
        )
        await session.commit()
        print(f"cleanup: deleted {result.rowcount} old ticks")


async def cleanup_worker():
    while True:
        await asyncio.sleep(60)   
        try:
            await delete_old_ticks()
        except Exception as e:
            print(f"cleanup error: {e}")