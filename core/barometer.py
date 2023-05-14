# SPDX-FileCopyrightText: 2020 Bryan Siepert for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import machine
import uasyncio

from .utils.i2c_bit import ROBit, RWBit
from .utils.i2c_bits import ROBits, RWBits
from .utils.i2c_struct import ROUnaryStruct, UnaryStruct

_DPS310_DEFAULT_ADDRESS = 0x77  # DPS310 default i2c address
_DPS310_PRSB2 = 0x00  # Highest byte of pressure data
_DPS310_TMPB2 = 0x03  # Highest byte of temperature data
_DPS310_PRSCFG = 0x06  # Pressure configuration
_DPS310_TMPCFG = 0x07  # Temperature configuration
_DPS310_MEASCFG = 0x08  # Sensor configuration
_DPS310_CFGREG = 0x09  # Interrupt/FIFO configuration
_DPS310_RESET = 0x0C  # Soft reset
_DPS310_PRODREVID = 0x0D  # Register that contains the part ID
_DPS310_TMPCOEFSRCE = 0x28  # Temperature calibration src


def twos_complement(val: int, bits: int) -> int:
    return val - (1 << bits) if val & (1 << (bits - 1)) != 0 else val


class Barometer:
    """Library for the DPS310 Precision Barometric Pressure Sensor."""

    # Register definitions
    def __init__(self, i2c: machine.I2C, address: int = _DPS310_DEFAULT_ADDRESS) -> None:
        self.address = address
        self.i2c = i2c
        self._device_id = ROUnaryStruct(i2c, _DPS310_PRODREVID, ">B")
        self._reset_register = UnaryStruct(i2c, _DPS310_RESET, ">B")
        self._mode_bits = RWBits(i2c, 3, _DPS310_MEASCFG, 0)  #
        self._pressure_osbits = RWBits(i2c, 4, _DPS310_PRSCFG, 0)
        self._temp_osbits = RWBits(i2c, 4, _DPS310_TMPCFG, 0)
        self._temp_measurement_src_bit = RWBit(i2c, _DPS310_TMPCFG, 7)
        self._pressure_shiftbit = RWBit(i2c, _DPS310_CFGREG, 2)
        self._temp_shiftbit = RWBit(i2c, _DPS310_CFGREG, 3)
        self._coefficients_ready = RWBit(i2c, _DPS310_MEASCFG, 7)
        self._sensor_ready = RWBit(i2c, _DPS310_MEASCFG, 6)
        self._temp_ready = RWBit(i2c, _DPS310_MEASCFG, 5)
        self._pressure_ready = RWBit(i2c, _DPS310_MEASCFG, 4)
        self._raw_pressure = ROBits(i2c, 24, _DPS310_PRSB2, 0, 3, lsb_first=False)
        self._raw_temperature = ROBits(i2c, 24, _DPS310_TMPB2, 0, 3, lsb_first=False)
        self._calib_coeff_temp_src_bit = ROBit(i2c, _DPS310_TMPCOEFSRCE, 7)
        self._reg0e = RWBits(i2c, 8, 0x0E, 0)
        self._reg0f = RWBits(i2c, 8, 0x0F, 0)
        self._reg62 = RWBits(i2c, 8, 0x62, 0)

        self._oversample_scalefactor = (
            524288,
            1572864,
            3670016,
            7864320,
            253952,
            516096,
            1040384,
            2088960,
        )
        self._sea_level_pressure = 1013.25

    async def initialize(self) -> None:
        """Initialize the sensor to continuous measurement"""

        await self.reset()

        self._pressure_osbits = 6
        self._pressure_shiftbit = True
        self._pressure_scale = self._oversample_scalefactor[6]

        self._temp_osbits = 6
        self._temp_scale = self._oversample_scalefactor[6]
        self._temp_shiftbit = True

        self._mode_bits = 7

        # wait until we have at least one good measurement
        await self.wait_temperature_ready()
        await self.wait_pressure_ready()

    # (https://github.com/Infineon/DPS310-Pressure-Sensor#temperature-measurement-issue)
    # similar to DpsClass::correctTemp(void) from infineon's c++ library
    async def _correct_temp(self) -> None:
        """Correct temperature readings on ICs with a fuse bit problem"""
        self._reg0e = 0xA5
        self._reg0f = 0x96
        self._reg62 = 0x02
        self._reg0e = 0
        self._reg0f = 0

        # perform a temperature measurement
        # the most recent temperature will be saved internally
        # and used for compensation when calculating pressure
        _unused = await self._raw_temperature.get()

    async def reset(self) -> None:
        """Reset the sensor"""
        self._reset_register = 0x89
        # wait for hardware reset to finish
        await uasyncio.sleep(0.010)
        while not self._sensor_ready:
            await uasyncio.sleep(0.001)
        await self._correct_temp()
        await self._read_calibration()
        # make sure we're using the temperature source used for calibration
        self._temp_measurement_src_bit = self._calib_coeff_temp_src_bit

    async def pressure(self) -> float:
        """Returns the current pressure reading in hectoPascals (hPa)"""

        temp_reading = await self._raw_temperature.get()
        raw_temperature = twos_complement(temp_reading, 24)

        pressure_reading = await self._raw_pressure.get()
        raw_pressure = twos_complement(pressure_reading, 24)

        scaled_rawtemp = raw_temperature / self._temp_scale
        scaled_rawpres = raw_pressure / self._pressure_scale

        pres_calc = (
            self._c00
            + scaled_rawpres * (self._c10 + scaled_rawpres * (self._c20 + scaled_rawpres * self._c30))
            + scaled_rawtemp * (self._c01 + scaled_rawpres * (self._c11 + scaled_rawpres * self._c21))
        )

        return pres_calc / 100

    async def altitude(self) -> float:
        """The altitude in meters based on the sea level pressure
        (:attr:`sea_level_pressure`) - which you must enter
        ahead of time
        """
        return 44330 * (1.0 - (await self.pressure() / self._sea_level_pressure) ** 0.1903)

    @property
    def sea_level_pressure(self) -> float:
        """The local sea level pressure in hectoPascals (aka millibars). This is used
        for calculation of :attr:`altitude`. Values are typically in the range
        980 - 1030."""
        return self._sea_level_pressure

    @sea_level_pressure.setter
    def sea_level_pressure(self, value: float) -> None:
        self._sea_level_pressure = value

    async def wait_temperature_ready(self) -> None:
        """Wait until a temperature measurement is available."""

        while self._temp_ready is False:
            await uasyncio.sleep_ms(10)

    async def wait_pressure_ready(self) -> None:
        """Wait until a pressure measurement is available"""

        while self._pressure_ready is False:
            await uasyncio.sleep_ms(10)

    async def _read_calibration(self) -> None:
        while not self._coefficients_ready:
            await uasyncio.sleep_ms(10)

        buffer = bytearray(19)
        coeffs = [0] * 18
        for offset in range(18):
            buffer = bytearray(2)
            buffer[0] = 0x10 + offset

            self.i2c.writeto(self.address, buffer[:1])
            self.i2c.readfrom_into(self.address, buffer[1:])

            coeffs[offset] = buffer[1]

        self._c0 = (coeffs[0] << 4) | ((coeffs[1] >> 4) & 0x0F)
        self._c0 = twos_complement(self._c0, 12)

        self._c1 = twos_complement(((coeffs[1] & 0x0F) << 8) | coeffs[2], 12)

        self._c00 = (coeffs[3] << 12) | (coeffs[4] << 4) | ((coeffs[5] >> 4) & 0x0F)
        self._c00 = twos_complement(self._c00, 20)

        self._c10 = ((coeffs[5] & 0x0F) << 16) | (coeffs[6] << 8) | coeffs[7]
        self._c10 = twos_complement(self._c10, 20)

        self._c01 = twos_complement((coeffs[8] << 8) | coeffs[9], 16)
        self._c11 = twos_complement((coeffs[10] << 8) | coeffs[11], 16)
        self._c20 = twos_complement((coeffs[12] << 8) | coeffs[13], 16)
        self._c21 = twos_complement((coeffs[14] << 8) | coeffs[15], 16)
        self._c30 = twos_complement((coeffs[16] << 8) | coeffs[17], 16)
