import dht, machine, time, random
from machine import Pin, SPI
import st7789

display = st7789.ST7789(
    SPI(1, baudrate=40000000, phase=0, polarity=0),
    128, 160,
    reset=machine.Pin(2, machine.Pin.OUT),
    dc=machine.Pin(4, machine.Pin.OUT),
    cs=machine.Pin(10, machine.Pin.OUT),
    inversion = False,
)

display.init()
backlight = Pin(5,Pin.OUT)
backlight.on()

color = display.color(0,0,0)
display.fill(color)
color = display.color(255,0,0)

while True:

    # Write some text.
    display.char(10,10,'a',display.color(10,10,10),display.color(255,255,255))
    display.text(30,30,'Hello World',display.color(0,0,0),display.color(255,255,255))

    # Random points using raw pixels.
    start = time.ticks_ms()
    for i in range(1000):
        x = random.getrandbits(8)
        y = random.getrandbits(8)
        display.pixel(x,y,color)
    elapsed = time.ticks_ms()-start
    print(f"1k pixels in {elapsed} ms")

    # Random circles, empty and full.
    full = True
    for i in range(100):
        fill_color = display.color(random.getrandbits(8),
                                   random.getrandbits(8),
                                   random.getrandbits(8))
        display.circle(
            random.getrandbits(8),
            random.getrandbits(8),
            random.getrandbits(6),
            fill_color,
            full)
        full = not full # Switch between full and empty circles.

    # Random lines
    display.fill(display.color(0,0,0))
    full = True
    for i in range(100):
        fill_color = display.color(random.getrandbits(8),
                                   random.getrandbits(8),
                                   random.getrandbits(8))
        display.line(
            random.getrandbits(8),
            random.getrandbits(8),
            random.getrandbits(8),
            random.getrandbits(8),
            fill_color)

while True:
    print("HERE")
    time.sleep(1)

while False:
    d = dht.DHT22(Pin(12))
    time.sleep(1)
    d.measure()
    print("%.1f, %.1f" % (d.temperature(), d.humidity()))
