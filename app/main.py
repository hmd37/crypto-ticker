import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
from fastapi.websockets import WebSocketDisconnect
from sqlalchemy import select, desc

from alerts import Alert, watch_alert
from cleanup import cleanup_worker
from database import PriceTick, async_session, create_tables
from feed import binance_feed, db_worker
from manager import ConnectionManager

manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    feed_task = asyncio.create_task(binance_feed(manager))
    worker_task = asyncio.create_task(db_worker()) 
    cleanup_task = asyncio.create_task(cleanup_worker())
    yield
    feed_task.cancel()
    worker_task.cancel()  
    cleanup_task.cancel()


app = FastAPI(lifespan=lifespan)

import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ticker")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()

    response = await call_next(request)

    duration = (time.perf_counter() - start) * 1000
    response.headers["X-Response-Time"] = f"{duration:.1f}ms"

    logger.info(
        f"{request.method} {request.url.path} "
        f"→ {response.status_code} "
        f"({duration:.1f}ms)"
    )

    return response


@app.get("/")
async def index():
    with open("docs/index.html") as f:
        return HTMLResponse(f.read())


MAX_CONNECTIONS = 1
connection_sem  = asyncio.Semaphore(MAX_CONNECTIONS)

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    if connection_sem.locked():
        await ws.accept()
        await ws.send_json({"type": "error", "message": "server full"})
        await ws.close()
        return

    async with connection_sem:
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


@app.websocket("/ws/alerts")
async def alert_endpoint(ws: WebSocket):
    await ws.accept()

    try:
        # wait for client to send alert config
        data = await ws.receive_json()

        alert = Alert(
            symbol=data["symbol"].upper() + "USDT",
            target_price=float(data["target_price"]),
            direction=data["direction"],
            ws=ws,
        )

        # start watching — this blocks until alert triggers or client disconnects
        await watch_alert(alert, manager)

    except WebSocketDisconnect:
        pass  # client left, watcher will die naturally on next send attempt
