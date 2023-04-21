import os

import adafruit_gps
import adafruit_lsm9ds1
import board
import busio
import machine
import uasyncio

from .radio import Radio

gps = adafruit_gps.GPS(busio.UART(board.TX, board.RX, baudrate=9600, timeout=10), debug=False)
sensor = adafruit_lsm9ds1.LSM9DS1_I2C(board.I2C())
radio = Radio(busio.SPI())
sd = machine.SDCard()
buzzer = machine.Pin(board.D7, machine.Pin.OUT, value=0)

os.mount(sd, "/sd")


async def init_gps():
    # Turn on the basic GGA and RMC info
    gps.send_command(b"PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0")
    # Set polling rate to 1Hz
    gps.send_command(b"PMTK220,1000")
    # love me some good string based API
    while not gps.has_fix:
        gps.update()
        await uasyncio.sleep_ms(10)


def start_buzzer():
    buzzer.value(1)


async def main():
    with open("/sd/log.txt", "w+") as log:
        # log = cast(BinaryIO, log)  # not sure why this isn't being inferred
        launched = False
        hit_apogee = False
        uasyncio.create_task(radio.send_loop())

        log.write("Starting the main loop")

        while True:
            accel_x, accel_y, accel_z = sensor.acceleration

            if accel_z > 9.81:
                log.write("Detected launch, starting GPS")
                launched = True
                await init_gps()

            if accel_z < 0:  # might need a running mean for a bit?
                if hit_apogee:
                    hit_ground = True
                    log.write("Hit the ground starting the buzzer")
                    start_buzzer()
                    break
                else:
                    hit_apogee = True

            if launched:
                ...
    await uasyncio.sleep_ms(30 * 60 * 1000)  # if we can't find it in 30 minutes then it's probably lost anyway


if __name__ == "__main__":
    uasyncio.run(main())
