from machine import Pin

from .utils.queue import Queue


class Radio:
    def __init__(self, data_pin: Pin) -> None:
        self.data_pin = data_pin
        self._queue = Queue[bytes]()

    def send(self, data: bytes, /) -> None:
        self._queue.put_nowait(data)

    async def send_loop(self):
        while True:
            message = await self._queue.get()
            self.data_pin.write(message)
