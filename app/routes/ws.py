from fastapi import APIRouter, WebSocket
from fastapi.websockets import WebSocketDisconnect

from alerts import Alert, watch_alert
from state import manager, connection_sem

router = APIRouter()


@router.websocket("/ws")
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


@router.websocket("/ws/alerts")
async def alert_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        data = await ws.receive_json()
        alert = Alert(
            symbol=data["symbol"].upper() + "USDT",
            target_price=float(data["target_price"]),
            direction=data["direction"],
            ws=ws,
        )
        await watch_alert(alert, manager)
    except WebSocketDisconnect:
        pass
