from machine import SPI

from .utils.queue import Queue


class Radio:
    def __init__(self, spi: SPI) -> None:
        self.spi = spi
        self._queue = Queue[bytes]()

    def send(self, data: bytes, /) -> None:
        self._queue.put_nowait(data)

    async def send_loop(self):
        while True:
            message = await self._queue.get()
            self.spi.write(message)
