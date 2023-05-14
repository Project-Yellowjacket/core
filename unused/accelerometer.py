# SPDX-FileCopyrightText: 2020 Bryan Siepert for Adafruit Industries
#
# SPDX-License-Identifier: MIT

from time import sleep

from .utils import i2c_device
from .utils.i2c_bit import RWBit
from .utils.i2c_bits import RWBits
from .utils.i2c_struct import ROUnaryStruct, Struct, UnaryStruct

_ICM20649_DEFAULT_ADDRESS = 0x68  # icm20649 default i2c address
_ICM20649_DEVICE_ID = 0xE1  # Correct content of WHO_AM_I register
_ICM20948_DEVICE_ID = 0xEA  # Correct content of WHO_AM_I register

# Functions using these bank-specific registers are responsible for ensuring
# that the correct bank is set
# Bank 0
_ICM20X_WHO_AM_I = 0x00  # device_id register
_ICM20X_REG_BANK_SEL = 0x7F  # register bank selection register
_ICM20X_PWR_MGMT_1 = 0x06  # primary power management register
_ICM20X_ACCEL_XOUT_H = 0x2D  # first byte of accel data
_ICM20X_GYRO_XOUT_H = 0x33  # first byte of accel data

_ICM20X_LP_CONFIG = 0x05  # Low Power config

# Bank 2
_ICM20X_GYRO_SMPLRT_DIV = 0x00
_ICM20X_GYRO_CONFIG_1 = 0x01
_ICM20X_ACCEL_SMPLRT_DIV_1 = 0x10
_ICM20X_ACCEL_CONFIG_1 = 0x14

_ICM20X_RAD_PER_DEG = 0.017453293  # Degrees/s to rad/s multiplier

G_TO_ACCEL = 9.80665


class CV:
    """struct helper"""

    @classmethod
    def add_values(cls, value_tuples):
        """Add CV values to the class"""
        cls.string = {}
        cls.lsb = {}

        for value_tuple in value_tuples:
            name, value, string, lsb = value_tuple
            setattr(cls, name, value)
            cls.string[value] = string
            cls.lsb[value] = lsb

    @classmethod
    def is_valid(cls, value):
        """Validate that a given value is a member"""
        return value in cls.string


class AccelRange(CV):
    """Options for :attr:`ICM20X.accelerometer_range`"""

    pass  # pylint: disable=unnecessary-pass


class GyroRange(CV):
    """Options for :attr:`ICM20X.gyro_data_range`"""

    pass  # pylint: disable=unnecessary-pass


class GyroDLPFFreq(CV):
    """Options for :attr:`ICM20X.gyro_dlpf_cutoff`"""

    pass  # pylint: disable=unnecessary-pass


class AccelDLPFFreq(CV):
    """Options for :attr:`ICM20X.accel_dlpf_cutoff`"""

    pass  # pylint: disable=unnecessary-pass


class ICM20X:  # pylint:disable=too-many-instance-attributes
    """Library for the ST ICM-20X Wide-Range 6-DoF Accelerometer and Gyro Family


    :param ~busio.I2C i2c_bus: The I2C bus the ICM20X is connected to.
    :param int address: The I2C address of the device.

    """

    AccelDLPFFreq.add_values(
        (
            (
                "DISABLED",
                -1,
                "Disabled",
                None,
            ),  # magical value that we will use do disable
            ("FREQ_246_0HZ_3DB", 1, 246.0, None),
            ("FREQ_111_4HZ_3DB", 2, 111.4, None),
            ("FREQ_50_4HZ_3DB", 3, 50.4, None),
            ("FREQ_23_9HZ_3DB", 4, 23.9, None),
            ("FREQ_11_5HZ_3DB", 5, 11.5, None),
            ("FREQ_5_7HZ_3DB", 6, 5.7, None),
            ("FREQ_473HZ_3DB", 7, 473, None),
        )
    )
    GyroDLPFFreq.add_values(
        (
            (
                "DISABLED",
                -1,
                "Disabled",
                None,
            ),  # magical value that we will use do disable
            ("FREQ_196_6HZ_3DB", 0, 196.6, None),
            ("FREQ_151_8HZ_3DB", 1, 151.8, None),
            ("FREQ_119_5HZ_3DB", 2, 119.5, None),
            ("FREQ_51_2HZ_3DB", 3, 51.2, None),
            ("FREQ_23_9HZ_3DB", 4, 23.9, None),
            ("FREQ_11_6HZ_3DB", 5, 11.6, None),
            ("FREQ_5_7HZ_3DB", 6, 5.7, None),
            ("FREQ_361_4HZ_3DB", 7, 361.4, None),
        )
    )

    def __init__(self, i2c_bus, address=_ICM20649_DEFAULT_ADDRESS):
        AccelRange.add_values(
            (
                ("RANGE_4G", 0, 4, 8192),
                ("RANGE_8G", 1, 8, 4096.0),
                ("RANGE_16G", 2, 16, 2048),
                ("RANGE_30G", 3, 30, 1024),
            )
        )

        GyroRange.add_values(
            (
                ("RANGE_500_DPS", 0, 500, 65.5),
                ("RANGE_1000_DPS", 1, 1000, 32.8),
                ("RANGE_2000_DPS", 2, 2000, 16.4),
                ("RANGE_4000_DPS", 3, 4000, 8.2),
            )
        )

        self.i2c_device = i2c_device.I2CDevice(i2c_bus, address)
        self._bank = 0
        self._device_id = ROUnaryStruct(self.i2c_device, _ICM20X_WHO_AM_I, ">B")
        self._bank_reg = UnaryStruct(self.i2c_device, _ICM20X_REG_BANK_SEL, ">B")
        self._reset = RWBit(self.i2c_device, _ICM20X_PWR_MGMT_1, 7)
        self._sleep_reg = RWBit(self.i2c_device, _ICM20X_PWR_MGMT_1, 6)
        self._low_power_en = RWBit(self.i2c_device, _ICM20X_PWR_MGMT_1, 5)
        self._clock_source = RWBits(self.i2c_device, 3, _ICM20X_PWR_MGMT_1, 0)
        self._raw_accel_data = Struct(self.i2c_device, _ICM20X_ACCEL_XOUT_H, ">hhh")  # ds says LE :|
        self._raw_gyro_data = Struct(self.i2c_device, _ICM20X_GYRO_XOUT_H, ">hhh")
        self._lp_config_reg = UnaryStruct(self.i2c_device, _ICM20X_LP_CONFIG, ">B")
        self._i2c_master_cycle_en = RWBit(self.i2c_device, _ICM20X_LP_CONFIG, 6)
        self._accel_cycle_en = RWBit(self.i2c_device, _ICM20X_LP_CONFIG, 5)
        self._gyro_cycle_en = RWBit(self.i2c_device, _ICM20X_LP_CONFIG, 4)
        self._gyro_dlpf_enable = RWBits(self.i2c_device, 1, _ICM20X_GYRO_CONFIG_1, 0)
        self._gyro_range = RWBits(self.i2c_device, 2, _ICM20X_GYRO_CONFIG_1, 1)
        self._gyro_dlpf_config = RWBits(self.i2c_device, 3, _ICM20X_GYRO_CONFIG_1, 3)
        self._accel_dlpf_enable = RWBits(self.i2c_device, 1, _ICM20X_ACCEL_CONFIG_1, 0)
        self._accel_range = RWBits(self.i2c_device, 2, _ICM20X_ACCEL_CONFIG_1, 1)
        self._accel_dlpf_config = RWBits(self.i2c_device, 3, _ICM20X_ACCEL_CONFIG_1, 3)
        self._accel_rate_divisor = UnaryStruct(self.i2c_device, _ICM20X_ACCEL_SMPLRT_DIV_1, ">H")
        self._gyro_rate_divisor = UnaryStruct(self.i2c_device, _ICM20X_GYRO_SMPLRT_DIV, ">B")

    async def initialize(self):
        """Configure the sensors with the default settings. For use after calling :meth:`reset`"""
        if await self._device_id.get() not in (_ICM20649_DEVICE_ID, _ICM20948_DEVICE_ID):
            raise RuntimeError("Failed to find an ICM20X sensor - check your wiring!")
        self._sleep = False
        self.accelerometer_range = AccelRange.RANGE_30G  # pylint: disable=no-member

        self.accelerometer_data_rate_divisor = 20  # ~53.57Hz
        self.gyro_data_rate_divisor = 10  # ~100Hz
        await self.reset()

    async def reset(self):
        """Resets the internal registers and restores the default settings"""
        self._bank = 0

        sleep(0.005)
        self._reset = True
        sleep(0.005)
        while self._reset:
            sleep(0.005)

    @property
    def _bank(self):
        return self._bank_reg >> 4

    @_bank.setter
    def _bank(self, value):
        self._bank_reg = value << 4

    @property
    def _sleep(self):
        self._bank = 0
        sleep(0.005)
        self._sleep_reg = False
        sleep(0.005)

    @_sleep.setter
    def _sleep(self, sleep_enabled):
        self._bank = 0
        sleep(0.005)
        self._sleep_reg = sleep_enabled
        sleep(0.005)

    async def acceleration(self) -> tuple[float, float, float]:
        """The x, y, z acceleration values returned in a 3-tuple and are in :math:`m / s ^ 2.`"""
        self._bank = 0
        raw_accel_data = await self._raw_accel_data.get()
        sleep(0.005)

        return tuple(
            map(
                lambda raw_measurement: raw_measurement / AccelRange.lsb[self._cached_accel_range] * G_TO_ACCEL,
                raw_accel_data,
            )
        )

    @property
    def accelerometer_range(self):
        """Adjusts the range of values that the sensor can measure, from +/- 4G to +/-30G
        Note that larger ranges will be less accurate. Must be an `AccelRange`"""
        return self._cached_accel_range

    async def set_accelerometer_range(self, value: int):
        if not AccelRange.is_valid(value):
            raise AttributeError("range must be an `AccelRange`")
        self._bank = 2
        sleep(0.005)
        await self._accel_range.set(value)
        sleep(0.005)
        self._cached_accel_range = value
        self._bank = 0

    async def accelerometer_data_rate_divisor(self):
        """
        The divisor for the rate at which accelerometer measurements are taken in Hz

        .. note::
            The data rates are set indirectly by setting a rate divisor according to the
            following formula:

            .. math::

                \\text{accelerometer_data_rate} = \\frac{1125}{1 + divisor}

        This function sets the raw rate divisor.

        """
        self._bank = 2
        raw_rate_divisor = await self._accel_rate_divisor.get()
        sleep(0.005)
        self._bank = 0
        # rate_hz = 1125/(1+raw_rate_divisor)
        return raw_rate_divisor

    async def set_accelerometer_data_rate_divisor(self, value):
        # check that value <= 4095
        self._bank = 2
        sleep(0.005)
        await self._accel_rate_divisor.set(value)
        sleep(0.005)

    def _accel_rate_calc(self, divisor: int):  # pylint:disable=no-self-use
        return 1125 / (1 + divisor)

    async def accelerometer_data_rate(self):
        """The rate at which accelerometer measurements are taken in Hz

        .. note::

            The data rates are set indirectly by setting a rate divisor according to the
            following formula:

            .. math::

                \\text{accelerometer_data_rate} = \\frac{1125}{1 + divisor}

        This function does the math to find the divisor from a given rate but it will not be
        exactly as specified.
        """
        return self._accel_rate_calc(await self.accelerometer_data_rate_divisor.get())

    async def set_accelerometer_data_rate(self, value):
        if value < self._accel_rate_calc(4095) or value > self._accel_rate_calc(0):
            raise AttributeError("Accelerometer data rate must be between 0.27 and 1125.0")
        self.accelerometer_data_rate_divisor = value

    async def accel_dlpf_cutoff(self):
        """The cutoff frequency for the accelerometer's digital low pass filter. Signals
        above the given frequency will be filtered out. Must be an ``AccelDLPFCutoff``.
        Use AccelDLPFCutoff.DISABLED to disable the filter

        .. note::
            Readings immediately following setting a cutoff frequency will be
            inaccurate due to the filter "warming up"

        """
        self._bank = 2
        return await self._accel_dlpf_config.get()

    def set_accel_dlpf_cutoff(self, cutoff_frequency):
        if not AccelDLPFFreq.is_valid(cutoff_frequency):
            raise AttributeError("accel_dlpf_cutoff must be an `AccelDLPFFreq`")
        self._bank = 2
        # check for shutdown
        if cutoff_frequency is AccelDLPFFreq.DISABLED:  # pylint: disable=no-member
            self._accel_dlpf_enable = False
            return
        self._accel_dlpf_enable = True
        self._accel_dlpf_config = cutoff_frequency

    @property
    def _low_power(self):
        self._bank = 0
        return self._low_power_en

    @_low_power.setter
    def _low_power(self, enabled):
        self._bank = 0
        self._low_power_en = enabled
