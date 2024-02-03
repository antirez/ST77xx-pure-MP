This is a pure-MicroPython driver for the ST7789 / ST7735 display drivers, designed in order to use very little memory.

## Motivations

Display drivers are more easily implemented by allocating (and subclassing) a MicroPython framebuffer in order to use its drawing primitives. This way drawing happesn in the device memory, without any need for I/O. Finally, to show the image on the screen, the framebuffer memory gets transfer to the display memory with a single long SPI write operation. This transfer is usually implemented in the .show() method of the driver.

However, even with a relatively small 160x128 display, this way of doing things requires allocating a bytearray of `160*128*2` bytes (2 bytes per pixel in RGB565 mode), which is 40k of total memory: more than what is available to a fresh ESP2866 MicroPython install. Even with more advanced MCUs, and especially if larger displays are used, the percentage of the available memory wasted on the framebuffer would often be prohibitive.

The alternative to this approach is writing directly to the display memory, which is often slow, since initiating SPI transfers for little data (for instance in the case of a single pixel drawing) is costly, especially in MicroPython.

**This driver's goal is to try to optimize direct memory access as much as possible** in order to have acceptable performances even if it's pure MicroPython code that uses SPI memory access to the display memory.

Why don't implement the driver directly in C? Because MicroPython default installs are what most people have access to :) And a C driver requires rebuilding MicroPython, which is not a trivial process involving installing embedded IDEs, cross compiling and so forth.

## Features

* Minimal driver code to communicate with ST77xx. It was initially based on [this driver](https://github.com/devbis/st7789py_mpy) but nows the common code is minimal. Thank you to the author!
* All the common graphical primitives, with very fast boxes, fill, hline, vline, and text. Other advanced shapes are also implemented trying to squeeze possible speedups: circles, triangles, and so forth.
* **Very low** memory usage in terms of allocations performed.
* Hopefully clean understandable code.

## Demo

This demo shows what the driver can do if used with an ESP8266EX.
Performances with a modern ESP32 will be much better. Click on the image to see the YouTube video.

[<img src="https://i.ytimg.com/vi/0iNZUMW-uXk/0.jpg" width="50%">](https://www.youtube.com/watch?v=0iNZUMW-uXk "ST77XX driver demo")


*Click the above image to see the video*

## Usage

This driver works with both ST7789 and ST7735 based displays. Other models are yet to be tested. The driver does not require the display to have any data output avaiable (these devices are often MOSI-only).

First of all, you need to create the display object, providing an
SPI interface to communicate with the display (see below in this README what
pins you could use in your device).

Please note that phase/polarity sometimes must be set to '1', or the
display does not work, it depends on the actual display you got.

    import st7789
    from machine import Pin

    display = st7789.ST7789(
        SPI(1, baudrate=40000000, phase=0, polarity=0),
        160, 128,
        reset=machine.Pin(2, machine.Pin.OUT),
        dc=machine.Pin(4, machine.Pin.OUT),
        cs=machine.Pin(10, machine.Pin.OUT),
        inversion = False,
    )

If colors look inverted, set inversion to True.

Then you need to initialize the display. See "Rotating the display"
section in this README. Here is just an example in case you want to
use a 128x160 display in portrait mode. If you want landscape make also
sure that the initialization of the object above has the width, height
arguments inverted, 128, 160. To initialize:

    display.init(landscape=True,mirror_y=True)

Then you are likely to require a backlight, if you want to see
what the display is dislaying. This depends on the display technology
used. Here is an example in case the backlight led pin is connected
to pin 5 of our board:

    backlight = Pin(5,Pin.OUT)
    backlight.on()

At this point if everything went well, you can draw on the display.
Check `test.py` for an example and to verify your display is working.
After editing `test.py` to put your SPI configuration, pins, display
size and so forth, you can run it with:

    mpremote cp st7789.py :
    mpremote run test.py

## Graphic primitives

The following is the list of the graphic primitives available.

    # Fast methods

    def fill(self,color) # Fill entire screen
    def pixel(self,x,y,color) # Draw pixel
    def hline(self,x0,x1,y,color) # Draw fast horizontal line
    def vline(self,y0,y1,x,color) # Draw fast vertical line
    def rect(self,x,y,w,h,color,fill=False) # Draw full or empty rectangle
    def char(self,x,y,char,bgcolor,fgcolor) # Draw a single character
    def text(self,x,y,txt,bgcolor,fgcolor)  # Draw text

    # Slower methods, what they do should be clear

    def line(self, x0, y0, x1, y1, color)
    def circle(self, x, y, radius, color, fill=False)
    def triangle(self, x0, y0, x1, y1, x2, y2, color, fill=False)

Everywhere there is to provide a color, you need to create the
color bytes with:

    mycolor = display.color(255,0,255) # RBB

Then use it like that:

    display.rect(10,10,50,50,mycolor,fill=True)

## Rotating the display view

The ST77xx chip is quite able to transparently rotate / mirror the access
to the video memory, so that it is possible to select different rotations
and mirroring of the image without having to transform the image at
software level.

Normally these displays native orientation is portrait (vertical), so
for instance if I have a 128x160 diplay, by default it will show
its content oriented as a tall rectangle.

The default behavior may be changed at initialization, by passing
the following parameters to the init() method:

    mirror_x: True/False        Mirror pixels horizontally
    mirror_y: True/False        Mirror pixels vertically
    landsacpe: True/False       Select landscape mode.
    ir_bgr: True/False          Display is not RGB but BGR.

Note that if you select landscape, you should no longer initialize the
display as 128x160, but as 160x128, passing 160 ad width and 128 as
height of the display when creating the object.

Mirroring will be likely be needed as well, depending on how the display
is rotated. Also if you see the colors are off, try selecting the
BGR mode.

## CS pin handling

Changing the state of pins takes a non trivial amount of time. During the
development of this driver it was experimentally observed that not
commuting the state of chip-select pin improves the performances by a
measurable amount. At the same time, most users will hardly have other
devices connected to the same SPI line, so this driver after the initialization
holds the CS pin off and leave it like that.

In case you really want to do multiplexing with some other device, once
you are no longer using the display you should call:

    dispaly.cs.on()

And only then use other devices connected to the same SPI interface.

## Connecting the display to the ESP2866 / ESP32

The ESP2866 and cheaper/older ESP32 models are probably one of the main
targets for this library being a lot more slow and memory constrained than
the recent models.

Often they can do hardware SPI only with a specific set of pins, so I
suggest you to connect the TFT display in this way:

Backlight led -> Pin 5 (D1 on some board)
SCK/Clock -> Pin 14    (D5 on some board)
SDA/MOSI  -> Pin 13    (D7 on some board)
A0/DC     -> Pin 4     (D2 on some board)
Reset     -> Pin 2     (D4 on some board)
CS        -> Pin 10    (SD3 on some board)
GND       -> GND       (one of the many)
VCC       -> 3V3       (one of the many)

Please note that this corresponds to the SPI interface 1 (known as
HSPI), becuase the SPI 0 is used in order to communicate with
the internal flash memory.

Make sure to set 'polarity' in the SPI interface according to your display specification. Sometimes it is 1 sometimes 0.
