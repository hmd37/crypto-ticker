import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.websockets import WebSocketDisconnect
from sqlalchemy import select, desc

from database import async_session, PriceTick, create_tables
from feed import binance_feed
from manager import ConnectionManager

manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()                                    # create tables on startup
    task = asyncio.create_task(binance_feed(manager))
    yield
    task.cancel()

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def index():
    with open("index.html") as f:
        return HTMLResponse(f.read())

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)

@app.get("/history/{symbol}")
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