from unittest.mock import AsyncMock
from manager import ConnectionManager


async def test_connect():
    manager = ConnectionManager()
    mock_ws = AsyncMock()

    await manager.connect(mock_ws)

    mock_ws.accept.assert_called_once()
    assert mock_ws in manager.clients


async def test_disconnect():
    manager = ConnectionManager()
    mock_ws = AsyncMock()

    await manager.connect(mock_ws)
    manager.disconnect(mock_ws)

    assert mock_ws not in manager.clients


async def test_broadcast_sends_to_all():
    manager = ConnectionManager()
    ws1, ws2, ws3 = AsyncMock(), AsyncMock(), AsyncMock()

    await manager.connect(ws1)
    await manager.connect(ws2)
    await manager.connect(ws3)

    await manager.broadcast({"symbol": "BTCUSDT", "price": 65000.0})

    ws1.send_json.assert_called_once()
    ws2.send_json.assert_called_once()
    ws3.send_json.assert_called_once()


async def test_broadcast_removes_dead_client():
    manager = ConnectionManager()
    good_ws = AsyncMock()
    dead_ws = AsyncMock()
    dead_ws.send_json.side_effect = Exception("connection lost")

    await manager.connect(good_ws)
    await manager.connect(dead_ws)

    await manager.broadcast({"symbol": "BTCUSDT", "price": 65000.0})

    assert dead_ws not in manager.clients
    assert good_ws in manager.clients


async def test_snapshot_sent_on_connect():
    manager = ConnectionManager()
    manager.latest_prices = {
        "btcusdt": {"symbol": "BTCUSDT", "price": 65000.0}
    }

    mock_ws = AsyncMock()
    await manager.connect(mock_ws)

    mock_ws.send_json.assert_called_once()