"""In-process event bus -> Server-Sent Events for the live UI."""
from __future__ import annotations

import asyncio
import json
from collections import deque


class EventBus:
    def __init__(self, history: int = 200):
        self._subscribers: list[asyncio.Queue] = []
        self._history: deque = deque(maxlen=history)

    def publish(self, event: dict) -> None:
        self._history.append(event)
        for q in list(self._subscribers):
            q.put_nowait(event)

    async def subscribe(self):
        q: asyncio.Queue = asyncio.Queue()
        for event in self._history:  # replay recent history to new viewers
            q.put_nowait(event)
        self._subscribers.append(q)
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=10.0)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            if q in self._subscribers:
                self._subscribers.remove(q)


bus = EventBus()
