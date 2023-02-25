from machine import I2C, Pin
import adafruit_lsm9ds1 as lsm9ds1


def main():
    setup()
    while True:
        loop()


if __name__ == "__main__":
    main()
