# SPDX-FileCopyrightText: 2016 Scott Shawcroft for Adafruit Industries
#
# SPDX-License-Identifier: MIT
# pylint: disable=too-few-public-methods


from machine import I2C


class ROBit:
    """
    Single bit register that is readable and writeable.

    Values are `bool`

    :param int register_address: The register address to read the bit from
    :param int bit: The bit index within the byte at ``register_address``
    :param int register_width: The number of bytes in the register. Defaults to 1.
    :param bool lsb_first: Is the first byte we read from I2C the LSB? Defaults to true

    """

    def __init__(
        self,
        i2c: I2C,
        register_address: int,
        bit: int,
        register_width: int = 1,
        lsb_first: bool = True,
    ) -> None:
        self.i2c = i2c
        self.address = register_address
        self.bit_mask = 1 << (bit % 8)  # the bitmask *within* the byte!
        self.buffer = bytearray(1 + register_width)
        self.buffer[0] = register_address
        self.byte = bit // 8 + 1 if lsb_first else register_width - (bit // 8)

    async def get(self) -> bool:
        self.i2c.writeto(self.address, self.buffer[:1])
        self.i2c.readfrom_into(self.address, self.buffer[1:])
        return bool(self.buffer[self.byte] & self.bit_mask)


class RWBit(ROBit):
    """Single bit register that is read only. Subclass of `RWBit`.

    Values are `bool`

    :param int register_address: The register address to read the bit from
    :param type bit: The bit index within the byte at ``register_address``
    :param int register_width: The number of bytes in the register. Defaults to 1.

    """

    async def set(self, value: bool) -> None:
        self.i2c.writeto(self.address, self.buffer[:1])
        self.i2c.readfrom_into(self.address, self.buffer[1:])
        if value:
            self.buffer[self.byte] |= self.bit_mask
        else:
            self.buffer[self.byte] &= ~self.bit_mask
        self.i2c.write(self.buffer)
