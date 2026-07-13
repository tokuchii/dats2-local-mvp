"""Server-Sent Events hub for real-time updates."""
from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator


_subscribers: list[asyncio.Queue] = []


async def subscribe() -> AsyncGenerator[str, None]:
    queue: asyncio.Queue = asyncio.Queue(maxsize=256)
    _subscribers.append(queue)
    try:
        while True:
            try:
                data = await asyncio.wait_for(queue.get(), timeout=10)
                yield f"data: {data}\n\n"
            except asyncio.TimeoutError:
                yield ": heartbeat\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        try:
            _subscribers.remove(queue)
        except ValueError:
            pass


def publish(event: str, payload: dict | None = None) -> None:
    message = json.dumps({"event": event, **(payload or {})})
    for queue in _subscribers[:]:
        try:
            queue.put_nowait(message)
        except asyncio.QueueFull:
            pass
