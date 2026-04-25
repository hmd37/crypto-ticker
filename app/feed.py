import json
import asyncio
import websockets

from manager import ConnectionManager


async def binance_feed(manager: ConnectionManager):
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

        except Exception as e:
            print(f"Binance connection lost: {e}. Reconnecting in 3s...")
            await asyncio.sleep(3)   # wait before retrying