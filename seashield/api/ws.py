"""Live stream to the dashboard: every engine event is pushed as JSON."""

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from seashield.api.live import hub

router = APIRouter()


@router.websocket("/ws/live")
async def live(ws: WebSocket) -> None:
    await ws.accept()
    queue = hub.subscribe()

    async def pump() -> None:
        while True:
            await ws.send_text(json.dumps(await queue.get()))

    sender = asyncio.create_task(pump())
    try:
        while True:
            await ws.receive_text()  # returns/raises when the browser goes away
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        sender.cancel()
        hub.unsubscribe(queue)
