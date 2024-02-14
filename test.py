import dht, machine, time, random, os
from machine import Pin, SPI
import st7789_base, st7789_ext

display = st7789_ext.ST7789(
    SPI(1, baudrate=40000000, phase=0, polarity=0),
    160, 128,
    reset=machine.Pin(2, machine.Pin.OUT),
    dc=machine.Pin(4, machine.Pin.OUT),
    cs=machine.Pin(10, machine.Pin.OUT),
)

display.init(landscape=True,mirror_y=True,inversion=False)
backlight = Pin(5,Pin.OUT)
backlight.on()

color = display.color(0,0,0)
display.fill(color)
color = display.color(255,0,0)

while True:

    upscaled = ["START","TEST","NOW..."]
    for i in range(3):
        display.upscaled_text(20*i,20*i,upscaled[i],display.color(15+80*i,15+80*i,15+80*i),upscaling=3)

    # Write some text.
    x = -15 
    y = 0
    for i in range(20):
        x += 2
        y += 8
        display.text(x,y,'Text drawing,Hello!',display.color(255,255,255),display.color(0,0,0))

    # If the file lenna.565 was lodaded in the device, show
    # it on the screen.
    for i in range(20):
        x = random.getrandbits(6)
        y = random.getrandbits(6)
        display.image(x,y,"lenna.565")

    # Random points using raw pixels.
    start = time.ticks_ms()
    for i in range(1000):
        x = random.getrandbits(8)
        y = random.getrandbits(8)
        display.pixel(x,y,color)
    elapsed = time.ticks_ms()-start
    print(f"1k pixels in {elapsed} ms")

    # Random rectangles, empty and full.
    full = True
    for i in range(500):
        fill_color = display.color(random.getrandbits(8),
                                   random.getrandbits(8),
                                   random.getrandbits(8))
        display.rect(
            random.getrandbits(8),
            random.getrandbits(8),
            random.getrandbits(6),
            random.getrandbits(6),
            fill_color,
            full)
        full = not full # Switch between full and empty circles.

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
    start = time.ticks_ms()
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
    elapsed = time.ticks_ms()-start
    print(f"Milliseconds per random line {elapsed/100} ms")

    # Random triangles
    full = True
    for i in range(100):
        fill_color = display.color(random.getrandbits(8),
                                   random.getrandbits(8),
                                   random.getrandbits(8))
        display.triangle(
            random.getrandbits(7),
            random.getrandbits(7),
            random.getrandbits(7),
            random.getrandbits(7),
            random.getrandbits(7),
            random.getrandbits(7),
            fill_color, full)
        full = not full # Switch between full and empty triangles.
