# SPDX-FileCopyrightText: 2016 Scott Shawcroft for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import uasyncio

from .typing import TYPE_CHECKING, Any, Self

if TYPE_CHECKING:
    from _typeshed import ReadableBuf, WritableBuf
    from machine import I2C


def slice_buf(buf: ReadableBuf, start: int = 0, end: int | None = None) -> memoryview:
    view = memoryview(buf)
    if start and end is not None:
        return view[start:end]
    elif start:
        return view[start:]
    elif end is not None:
        return view[:end]
    return view


# this class must be used for all I2C devices on the same pin because locking is only implemented python side
class I2CDevice:
    """Represents a single I2C device and manages locking the bus and the device address."""

    def __init__(self, i2c: I2C, device_address: int, probe: bool = True) -> None:
        self.i2c = i2c
        self.device_address = device_address
        self.lock = uasyncio.Lock()

        if probe:
            self._t = uasyncio.create_task(self.__probe_for_device())

    def readinto(
        self,
        buf: WritableBuf,
        *,
        start: int = 0,
        end: int | None = None,
    ) -> None:
        """
        Read into ``buf`` from the device. The number of bytes read will be the
        length of ``buf``.

        If ``start`` or ``end`` is provided, then the buffer will be sliced
        as if ``buf[start:end]``. This will not cause an allocation like
        ``buf[start:end]`` will so it saves memory.

        :param ~AnyWritableBuf buffer: buffer to write into
        :param int start: Index to start writing at
        :param int end: Index to write up to but not include; if None, use ``len(buf)``
        """
        self.i2c.readfrom_into(self.device_address, slice_buf(buf, start, end))

    def write(
        self,
        buf: ReadableBuf,
        *,
        start: int = 0,
        end: int | None = None,
    ) -> None:
        """
        Write the bytes from ``buffer`` to the device, then transmit a stop
        bit.

        If ``start`` or ``end`` is provided, then the buffer will be sliced
        as if ``buffer[start:end]``. This will not cause an allocation like
        ``buffer[start:end]`` will so it saves memory.

        :param ~AnyReadableBuf buffer: buffer containing the bytes to write
        :param int start: Index to start writing from
        :param int end: Index to read up to but not include; if None, use ``len(buf)``
        """
        self.i2c.writeto(self.device_address, slice_buf(buf, start, end))

    def write_then_readinto(
        self,
        out_buffer: ReadableBuf,
        in_buffer: WritableBuf,
        *,
        out_start: int = 0,
        out_end: int | None = None,
        in_start: int = 0,
        in_end: int | None = None,
    ) -> None:
        """
        Write the bytes from ``out_buffer`` to the device, then immediately
        reads into ``in_buffer`` from the device. The number of bytes read
        will be the length of ``in_buffer``.

        If ``out_start`` or ``out_end`` is provided, then the output buffer
        will be sliced as if ``out_buffer[out_start:out_end]``. This will
        not cause an allocation like ``buffer[out_start:out_end]`` will so
        it saves memory.

        If ``in_start`` or ``in_end`` is provided, then the input buffer
        will be sliced as if ``in_buffer[in_start:in_end]``. This will not
        cause an allocation like ``in_buffer[in_start:in_end]`` will so
        it saves memory.

        :param ~AnyReadableBuf out_buffer: buffer containing the bytes to write
        :param ~AnyWritableBuf in_buffer: buffer containing the bytes to read into
        :param int out_start: Index to start writing from
        :param int out_end: Index to read up to but not include; if None, use ``len(out_buffer)``
        :param int in_start: Index to start writing at
        :param int in_end: Index to write up to but not include; if None, use ``len(in_buffer)``
        """

        self.i2c.writeto(self.device_address, slice_buf(out_buffer, out_start, out_end))
        self.i2c.readfrom_into(self.device_address, slice_buf(in_buffer, in_start, in_end))

    async def __aenter__(self) -> Self:
        await self.lock.acquire()
        return self

    def __aexit__(self, *args: Any) -> None:
        return self.lock.release()

    async def __probe_for_device(self) -> None:
        """
        Try to read a byte from an address,
        if you get an OSError it means the device is not there
        or that the device does not support these means of probing
        """
        async with self.lock:
            try:
                self.i2c.writeto(self.device_address, b"")
            except OSError:
                # some OS's dont like writing an empty bytesting...
                # Retry by reading a byte
                try:
                    result = bytearray(1)
                    self.i2c.readfrom_into(self.device_address, result)
                except OSError:
                    raise ValueError("No I2C device at address: 0x%x" % self.device_address)
