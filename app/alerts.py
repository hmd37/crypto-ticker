import asyncio
from dataclasses import dataclass

from fastapi import WebSocket

from manager import ConnectionManager


@dataclass
class Alert:
    symbol: str
    target_price: float
    direction: str
    ws: WebSocket


# one event per tracked coin
price_events: dict[str, asyncio.Event] = {
    "BTCUSDT": asyncio.Event(),
    "ETHUSDT": asyncio.Event(),
    "BNBUSDT": asyncio.Event(),
    "SOLUSDT": asyncio.Event(),
    "XRPUSDT": asyncio.Event(),
    "DOGEUSDT": asyncio.Event(),
}


async def watch_alert(alert: Alert, manager: ConnectionManager):
    event = price_events[alert.symbol]

    while True:
        await event.wait()
        event.clear()

        current = manager.latest_prices.get(alert.symbol.lower())
        if not current:
            continue

        price = current["price"]

        triggered = (
            alert.direction == "above"
            and price >= alert.target_price
            or alert.direction == "below"
            and price <= alert.target_price
        )

        if triggered:
            try:
                await alert.ws.send_json(
                    {
                        "type": "alert",
                        "symbol": alert.symbol,
                        "price": price,
                        "target": alert.target_price,
                        "direction": alert.direction,
                    }
                )
            except Exception:
                pass
            break
