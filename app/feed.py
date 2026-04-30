import asyncio
import json

import websockets
from alerts import price_events
from database import PriceTick, async_session
from manager import ConnectionManager

# shared queue — producer puts, consumer takes
tick_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)


async def bulk_insert(ticks: list[dict]):
    async with async_session() as session:
        session.add_all(
            [
                PriceTick(
                    symbol=t["symbol"],
                    price=t["price"],
                    change=t["change"],
                    high=t["high"],
                    low=t["low"],
                )
                for t in ticks
            ]
        )
        await session.commit()


async def db_worker():
    while True:
        batch = []

        # wait for first item
        first = await tick_queue.get()
        batch.append(first)

        # now wait up to 2 seconds collecting more
        try:
            while len(batch) < 100:
                item = await asyncio.wait_for(
                    tick_queue.get(),
                    timeout=2.0,  # wait max 2 seconds for next item
                )
                batch.append(item)
        except asyncio.TimeoutError:
            pass  # 2 seconds passed, insert whatever we have

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
                        "volume": float(data["q"]),
                    }

                    manager.latest_prices[price_data["symbol"].lower()] = price_data
                    await manager.broadcast(price_data)

                    # drop in queue — never blocks the feed
                    if not tick_queue.full():
                        await tick_queue.put(price_data)

                    # wake up any watchers for this coin
                    symbol = price_data["symbol"]
                    if symbol in price_events:
                        price_events[symbol].set()  # all watchers for this coin wake up

        except Exception as e:
            print(f"Binance connection lost: {e}. Reconnecting in 3s...")
            await asyncio.sleep(3)
