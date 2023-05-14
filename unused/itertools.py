# SPDX-FileCopyrightText: 2016 Scott Shawcroft for Adafruit Industries
#
# SPDX-License-Identifier: MIT
# pylint: disable=too-few-public-methods


import struct

from .i2c_device import I2CDevice
from .typing import Any


class Struct:
    """
    Arbitrary structure register that is readable and writeable.

    Values are tuples that map to the values in the defined struct.  See struct
    module documentation for struct format string and its possible value types.

    :param int register_address: The register address to read the bit from
    :param str struct_format: The struct format string for this register.
    """

    def __init__(self, i2c_device: I2CDevice, register_address: int, struct_format: str) -> None:
        self.i2c_device = i2c_device
        self.format = struct_format
        self.buffer = bytearray(1 + struct.calcsize(self.format))
        self.buffer[0] = register_address

    async def get(self) -> tuple[Any, ...]:
        async with self.i2c_device as i2c:
            i2c.write_then_readinto(self.buffer, self.buffer, out_end=1, in_start=1)
        return struct.unpack_from(self.format, memoryview(self.buffer)[1:])

    async def set(self, value: tuple[Any, ...]) -> None:
        struct.pack_into(self.format, self.buffer, 1, *value)
        async with self.i2c_device as i2c:
            i2c.write(self.buffer)


class ROUnaryStruct:
    """
    Arbitrary single value structure register that is readable and writeable.

    Values map to the first value in the defined struct.  See struct
    module documentation for struct format string and its possible value types.

    :param int register_address: The register address to read the bit from
    :param str struct_format: The struct format string for this register.
    """

    def __init__(self, i2c_device: I2CDevice, register_address: int, struct_format: str) -> None:
        self.i2c_device = i2c_device
        self.format = struct_format
        self.address = register_address

    async def get(self) -> Any:
        buf = bytearray(1 + struct.calcsize(self.format))
        buf[0] = self.address
        async with self.i2c_device as i2c:
            i2c.write_then_readinto(buf, buf, out_end=1, in_start=1)
        return struct.unpack_from(self.format, buf, 1)[0]


class UnaryStruct(ROUnaryStruct):
    """
    Arbitrary single value structure register that is read-only.

    Values map to the first value in the defined struct.  See struct
    module documentation for struct format string and its possible value types.

    :param int register_address: The register address to read the bit from
    :param type struct_format: The struct format string for this register.
    """

    async def set(self, value: Any) -> None:
        buf = bytearray(1 + struct.calcsize(self.format))
        buf[0] = self.address
        struct.pack_into(self.format, buf, 1, value)
        async with self.i2c_device as i2c:
            i2c.write(buf)
