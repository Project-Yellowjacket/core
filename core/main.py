# from machine import I2C, Pin
import time

import adafruit_lsm9ds1
import adafruit_lsm9ds1 as lsm9ds1
import board

accelerometer_small = lsm9ds1.LSM9DS1()
# Create sensor object, communicating over the board's default I2C bus
i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
sensor = adafruit_lsm9ds1.LSM9DS1_I2C(i2c)

# Main loop will read the acceleration, magnetometer, gyroscope, Temperature
# values every second and print them out.
while True:
    # Read acceleration, magnetometer, gyroscope, temperature.
    accel_x, accel_y, accel_z = sensor.acceleration
    mag_x, mag_y, mag_z = sensor.magnetic
    gyro_x, gyro_y, gyro_z = sensor.gyro
    temp = sensor.temperature
    # Print values.
    print("Acceleration (m/s^2): ({0:0.3f},{1:0.3f},{2:0.3f})".format(accel_x, accel_y, accel_z))
    time.sleep(1.0)


# if __name__ == "__main__":
#     main()
