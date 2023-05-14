import uasyncio

import machine

buzzer = machine.Pin(46, machine.Pin.OUT)
while True:
    buzzer.off()
    await uasyncio.sleep_us(50)
    buzzer.on()
    time.sleep_us(100)
