"""Live stream to the dashboard (Phase 7).

Plan: a background task subscribes to seashield/verdicts/# on MQTT and
broadcasts every Assessment to connected browsers.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()
_clients: set[WebSocket] = set()


@router.websocket("/ws/live")
async def live(ws: WebSocket) -> None:
    await ws.accept()
    _clients.add(ws)
    try:
        while True:
            await ws.receive_text()  # keep-alive; the client does not send data
    except WebSocketDisconnect:
        _clients.discard(ws)


async def broadcast(payload: str) -> None:
    for ws in list(_clients):
        try:
            await ws.send_text(payload)
        except (WebSocketDisconnect, RuntimeError):  # client gone / socket already closed
            _clients.discard(ws)
