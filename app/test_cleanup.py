from datetime import datetime, timedelta, UTC
from sqlalchemy import select
from database import PriceTick
from cleanup import delete_old_ticks


async def test_deletes_old_ticks(session):
    session.add(PriceTick(
        symbol="BTCUSDT",
        price=65000.0,
        change=1.5,
        high=66000.0,
        low=64000.0,
        timestamp=datetime.now(UTC) - timedelta(days=10)
    ))
    await session.commit()

    await delete_old_ticks(session=session)
    session.expire_all()

    result = await session.execute(select(PriceTick))
    ticks = result.scalars().all()
    assert len(ticks) == 0


async def test_keeps_recent_ticks(session):
    session.add(PriceTick(
        symbol="ETHUSDT",
        price=3200.0,
        change=0.5,
        high=3300.0,
        low=3100.0,
        timestamp=datetime.now(UTC) - timedelta(minutes=30)
    ))
    await session.commit()

    await delete_old_ticks(session=session)
    session.expire_all()

    result = await session.execute(select(PriceTick))
    ticks = result.scalars().all()
    assert len(ticks) == 1