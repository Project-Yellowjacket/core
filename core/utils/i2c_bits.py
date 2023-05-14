# SPDX-FileCopyrightText: 2016 Scott Shawcroft for Adafruit Industries
#
# SPDX-License-Identifier: MIT
# pylint: disable=too-few-public-methods

from machine import I2C


class ROBits:
    """
    Multibit register (less than a full byte) that is read-only. This must be
    within a byte register.

    Values are `int` between 0 and 2 ** ``num_bits`` - 1.

    :param int num_bits: The number of bits in the field.
    :param int register_address: The register address to read the bit from
    :param type lowest_bit: The lowest bits index within the byte at ``register_address``
    :param int register_width: The number of bytes in the register. Defaults to 1.
    """

    def __init__(  # pylint: disable=too-many-arguments
        self,
        i2c: I2C,
        num_bits: int,
        register_address: int,
        lowest_bit: int,
        register_width: int = 1,
        lsb_first: bool = True,
        signed: bool = False,
    ) -> None:
        self.i2c = i2c
        self.bit_mask = ((1 << num_bits) - 1) << lowest_bit
        if self.bit_mask >= 1 << (register_width * 8):
            raise ValueError("Cannot have more bits than register size")
        self.lowest_bit = lowest_bit
        self.buffer = bytearray(1 + register_width)
        self.address = register_address
        self.buffer[0] = register_address
        self.lsb_first = lsb_first
        self.sign_bit = (1 << (num_bits - 1)) if signed else 0

    async def get(self) -> int:
        self.i2c.writeto(self.address, self.buffer[:1])
        self.i2c.readfrom_into(self.address, self.buffer[1:])
        # read the number of bytes into a single variable
        reg = 0
        order = range(len(self.buffer) - 1, 0, -1)
        if not self.lsb_first:
            order = reversed(order)
        for i in order:
            reg = (reg << 8) | self.buffer[i]
        reg = (reg & self.bit_mask) >> self.lowest_bit
        # If the value is signed and negative, convert it
        if reg & self.sign_bit:
            reg -= 2 * self.sign_bit
        return reg


class RWBits(ROBits):
    """
    Multibit register (less than a full byte) that is readable and writeable.
    This must be within a byte register.

    Values are `int` between 0 and 2 ** ``num_bits`` - 1.

    :param int num_bits: The number of bits in the field.
    :param int register_address: The register address to read the bit from
    :param int lowest_bit: The lowest bits index within the byte at ``register_address``
    :param int register_width: The number of bytes in the register. Defaults to 1.
    :param bool lsb_first: Is the first byte we read from I2C the LSB? Defaults to true
    :param bool signed: If True, the value is a "two's complement" signed value.
                        If False, it is unsigned.
    """

    async def set(self, value: int) -> None:
        value <<= self.lowest_bit  # shift the value over to the right spot
        self.i2c.writeto(self.address, self.buffer[:1])
        self.i2c.readfrom_into(self.address, self.buffer[1:])
        reg = 0
        order = range(len(self.buffer) - 1, 0, -1)
        if not self.lsb_first:
            order = range(1, len(self.buffer))
        for i in order:
            reg = (reg << 8) | self.buffer[i]
        reg &= ~self.bit_mask  # mask off the bits we're about to change
        reg |= value  # then or in our new value
        for i in reversed(order):
            self.buffer[i] = reg & 0xFF
            reg >>= 8
        self.i2c.write(self.buffer)
