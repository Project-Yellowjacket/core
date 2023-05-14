from .machine import I2C

class LSM9DS1:
    def __init__(self, i2c: I2C, accel_scale: int = 4) -> None: ...
    def accel(self) -> tuple[float, float, float]: ...  # tuple of gs
