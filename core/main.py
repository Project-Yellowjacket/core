from collections import deque
from time import ticks_diff, ticks_ms

import lsm9ds1
import machine
import uasyncio

from .barometer import Barometer
from .utils.typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from typing import TextIO
accelerometer_internal = lsm9ds1.LSM9DS1(machine.I2C(1, scl=machine.Pin(15), sda=machine.Pin(14)))
buzzer = machine.Pin(46, machine.Pin.OUT)
barometer = Barometer(machine.I2C(1))


async def start_buzzer():
    while True:
        buzzer.off()
        await uasyncio.sleep(50e-6)
        buzzer.on()
        await uasyncio.sleep(100e-6)


def normalised_acceleration() -> tuple[float, float, float]:
    z, x, y = accelerometer_internal.accel()
    return -x * 9.81, y * 9.81, -z * 9.81


async def main():
    await uasyncio.wait_for(start_buzzer(), 3)
    await uasyncio.sleep(30 * 60)
    await uasyncio.wait_for(start_buzzer(), 5)
    accels = deque((), 3)
    with open("log.txt", "w+") as log:
        log = cast("TextIO", log)
        hit_apogee = False
        await barometer.initialize()
        log.write("Starting the main loop")
        max_accel = 0.0
        max_height = 0.0
        launch_time = 0
        while True:
            accel_x, accel_y, accel_z = normalised_acceleration()
            if accel_z > max_accel:
                max_accel = accel_z
            height = await barometer.altitude()
            accels.append(accel_z)
            rolling_total = sum(accels)
            if height > max_height:
                max_height = height
            if rolling_total > 30:
                log.write("L")
                launched = True
                launch_time = ticks_ms()

            if rolling_total < 0:
                if hit_apogee:
                    log.write("H {}".format(ticks_diff(ticks_ms(), launch_time)))
                    log.write("{} {}".format(max_accel, max_height))

                    await uasyncio.wait_for(start_buzzer(), 30 * 60)
                    break
                else:
                    log.write(f"A {ticks_diff(ticks_ms(), launch_time)}s")
                    hit_apogee = True


if __name__ == "__main__":
    uasyncio.run(main())
