# SPDX-FileCopyrightText: 2016 Scott Shawcroft for Adafruit Industries
#
# SPDX-License-Identifier: MIT
# pylint: disable=too-few-public-methods


import struct

from machine import I2C

from .typing import Any


class ROUnaryStruct:
    """
    Arbitrary single value structure register that is readable and writeable.

    Values map to the first value in the defined struct.  See struct
    module documentation for struct format string and its possible value types.

    :param int register_address: The register address to read the bit from
    :param str struct_format: The struct format string for this register.
    """

    def __init__(self, i2c: I2C, register_address: int, struct_format: str) -> None:
        self.i2c = i2c
        self.format = struct_format
        self.address = register_address

    async def get(self) -> Any:
        buf = bytearray(1 + struct.calcsize(self.format))
        buf[0] = self.address
        self.i2c.writeto(self.address, buf[:1])
        self.i2c.readfrom_into(self.address, buf[1:])
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
        self.i2c.write(buf)
