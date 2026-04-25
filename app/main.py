import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.websockets import WebSocketDisconnect
from fastapi.responses import HTMLResponse

from feed import binance_feed
from manager import ConnectionManager

manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(binance_feed(manager))
    yield
    task.cancel()

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def index():
    with open("app/index.html") as f:
        return HTMLResponse(f.read())

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)