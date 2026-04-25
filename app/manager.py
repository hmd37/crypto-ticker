from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.clients = set()
        self.latest_prices = {}   # snapshot storage

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.clients.add(ws)
        if self.latest_prices:                              # only if we have data
            await ws.send_json({
                "type": "snapshot",
                "data": self.latest_prices
            })

    def disconnect(self, ws: WebSocket):
        self.clients.discard(ws)

    async def broadcast(self, data: dict):
        dead = set()

        for client in self.clients:
            try:
                await client.send_json({"type": "tick", "data": data})
            except Exception:
                dead.add(client)

        for client in dead:
            self.clients.discard(client)