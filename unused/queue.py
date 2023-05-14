"""Apparently there is no queue implementation in uasyncio so we need our own."""

import uasyncio

from .typing import Generic, TypeVar

T = TypeVar("T")


class Queue(Generic[T]):
    def __init__(self) -> None:
        self._queue: list[T] = []  # should use a dequeue but it's pretty bad in micropython
        self._ev = uasyncio.Event()

    def put_nowait(self, item: T, /) -> None:
        self._queue.append(item)

        if not self._ev.is_set():
            self._ev.set()

    async def get(self) -> T:
        await self._ev.wait()
        try:
            return self._queue.pop(0)
        finally:
            if not self._queue:
                self._ev.clear()
