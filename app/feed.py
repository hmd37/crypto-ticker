import json
import asyncio
import websockets

from manager import ConnectionManager
from database import async_session, PriceTick

# shared queue — producer puts, consumer takes
tick_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)


async def bulk_insert(ticks: list[dict]):
    async with async_session() as session:
        session.add_all([
            PriceTick(
                symbol=t["symbol"],
                price=t["price"],
                change=t["change"],
                high=t["high"],
                low=t["low"],
            )
            for t in ticks
        ])
        await session.commit()


async def db_worker():
    """Consumer — runs forever, drains the queue in batches"""
    while True:
        batch = []

        first = await tick_queue.get()      # wait for at least one tick
        batch.append(first)

        while not tick_queue.empty() and len(batch) < 100:
            batch.append(tick_queue.get_nowait())

        await bulk_insert(batch)
        print(f"saved batch of {len(batch)} ticks")


async def binance_feed(manager: ConnectionManager):
    """Producer — receives ticks, broadcasts, drops in queue"""
    symbols = ["btcusdt", "ethusdt", "bnbusdt", "solusdt", "xrpusdt", "dogeusdt"]
    streams = "/".join(f"{s}@ticker" for s in symbols)
    url = f"wss://stream.binance.com:9443/stream?streams={streams}"

    while True:
        try:
            async with websockets.connect(url) as ws:
                async for raw in ws:
                    envelope = json.loads(raw)
                    data = envelope["data"]

                    price_data = {
                        "symbol": data["s"],
                        "price": float(data["c"]),
                        "change": float(data["P"]),
                        "high": float(data["h"]),
                        "low": float(data["l"]),
                    }

                    manager.latest_prices[price_data["symbol"].lower()] = price_data
                    await manager.broadcast(price_data)

                    # drop in queue — never blocks the feed
                    if not tick_queue.full():
                        await tick_queue.put(price_data)

        except Exception as e:
            print(f"Binance connection lost: {e}. Reconnecting in 3s...")
            await asyncio.sleep(3)