import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from cleanup import cleanup_worker
from database import create_tables
from feed import binance_feed, db_worker
from state import manager  
from routes.http import router as http_router
from routes.ws import router as ws_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ticker")


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


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration = (time.perf_counter() - start) * 1000
    response.headers["X-Response-Time"] = f"{duration:.1f}ms"
    logger.info(
        f"{request.method} {request.url.path} → {response.status_code} ({duration:.1f}ms)"
    )
    return response


app.include_router(http_router)
app.include_router(ws_router)
