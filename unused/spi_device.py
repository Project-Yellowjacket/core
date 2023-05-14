# SPDX-FileCopyrightText: 2016 Scott Shawcroft for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import uasyncio
from machine import SPI, Pin

from .typing import Any


class SPIDevice:
    """
    Represents a single SPI device and manages locking the bus and the device
    address.

    :param ~busio.SPI spi: The SPI bus the device is on
    :param ~digitalio.DigitalInOut chip_select: The chip select pin object that implements the
        DigitalInOut API.
    :param bool cs_active_value: Set to true if your device requires CS to be active high.
        Defaults to false.
    :param int baudrate: The SPI baudrate
    :param int polarity: The SPI polarity
    :param int phase: The SPI phase
    :param int extra_clocks: The minimum number of clock cycles to cycle the bus after CS is high.
        (Used for SD cards.)

    .. note:: This class is **NOT** built into CircuitPython. See
      :ref:`here for install instructions <bus_device_installation>`.

    Example:

    .. code-block:: python

        import busio
        import digitalio
        from board import *
        from adafruit_bus_device.spi_device import SPIDevice

        with busio.SPI(SCK, MOSI, MISO) as spi_bus:
            cs = digitalio.DigitalInOut(D10)
            device = SPIDevice(spi_bus, cs)
            bytes_read = bytearray(4)
            # The object assigned to spi in the with statements below
            # is the original spi_bus object. We are using the busio.SPI
            # operations busio.SPI.readinto() and busio.SPI.write().
            with device as spi:
                spi.readinto(bytes_read)
            # A second transaction
            with device as spi:
                spi.write(bytes_read)
    """

    def __init__(
        self,
        spi: SPI,
        chip_select: Pin | None = None,
        *,
        cs_active_value: bool = False,
        baudrate: int = 100000,
        polarity: int = 0,
        phase: int = 0,
        extra_clocks: int = 0
    ) -> None:
        self.spi = spi
        self.baudrate = baudrate
        self.polarity = polarity
        self.phase = phase
        self.extra_clocks = extra_clocks
        self.pin = chip_select
        self.cs_active_value = cs_active_value
        self.lock = uasyncio.Lock()
        if self.pin:
            self.pin.mode(Pin.OUT)
            self.pin.on()

    async def __aenter__(self) -> SPI:
        await self.lock.acquire()
        self.spi.init(baudrate=self.baudrate, polarity=self.polarity, phase=self.phase)
        if self.pin:
            self.pin.value(self.cs_active_value)
        return self.spi

    async def __aexit__(self, *args: Any) -> None:
        if self.pin:
            self.pin.value(not self.cs_active_value)
        if self.extra_clocks > 0:
            buf = bytearray(1)
            buf[0] = 0xFF
            clocks = self.extra_clocks // 8
            if self.extra_clocks % 8 != 0:
                clocks += 1
            for _ in range(clocks):
                self.spi.write(buf)
        self.lock.release()
