import asyncio
from collections.abc import AsyncGenerator


class PubSub:
    """In-process fan-out for subscriptions.

    Fine for one worker. With several workers, back this with Redis pub/sub
    (same interface) so every subscriber sees every event.
    """

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[int]] = set()

    def publish(self, incident_id: int) -> None:
        for queue in list(self._subscribers):
            queue.put_nowait(incident_id)

    async def subscribe(self) -> AsyncGenerator[int, None]:
        queue: asyncio.Queue[int] = asyncio.Queue()
        self._subscribers.add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._subscribers.discard(queue)


pubsub = PubSub()
