from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from sqlalchemy import desc, select

from database import PriceTick, async_session

router = APIRouter()


@router.get("/")
async def index():
    with open("docs/index.html") as f:
        return HTMLResponse(f.read())


@router.get("/history/{symbol}")
async def get_history(symbol: str, limit: int = 50):
    async with async_session() as session:
        result = await session.execute(
            select(PriceTick)
            .where(PriceTick.symbol == symbol.upper() + "USDT")
            .order_by(desc(PriceTick.timestamp))
            .limit(limit)
        )
        ticks = result.scalars().all()
        return [
            {
                "symbol": t.symbol,
                "price": t.price,
                "change": t.change,
                "high": t.high,
                "low": t.low,
                "timestamp": t.timestamp,
            }
            for t in ticks
        ]
