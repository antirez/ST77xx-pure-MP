This is a pure-MicroPython driver for the ST7789 / ST7735 display drivers, designed in order to use very little memory.

## Motivations

Display drivers are more easily implemented by allocating (and subclassing) a MicroPython framebuffer in order to use its drawing primitives. This way drawing happens in the device memory, without any need for I/O. Finally, to show the image on the screen, the framebuffer memory gets transfer to the display memory with a single long SPI write operation. This transfer is usually implemented in the .show() method of the driver.

However, even with a relatively small 160x128 display, this way of doing things requires allocating a bytearray of `160*128*2` bytes (2 bytes per pixel in RGB565 mode), which is 40k of total memory: more than what is available to a fresh ESP8266 MicroPython install. Even with more advanced MCUs, and especially if larger displays are used, the percentage of the available memory wasted on the framebuffer would often be prohibitive.

The alternative to this approach is writing directly to the display memory, which is often slow, since initiating SPI transfers for little data (for instance in the case of a single pixel drawing) is costly, especially in MicroPython.

**This driver's goal is to try to optimize direct memory access as much as possible** in order to have acceptable performances even if it's pure MicroPython code that uses SPI memory access to the display memory.

Why don't implement the driver directly in C? Because MicroPython default installs are what most people have access to :) And a C driver requires rebuilding MicroPython, which is not a trivial process involving installing embedded IDEs, cross compiling and so forth.

## Features

* Minimal driver code to communicate with ST77xx. It was initially based on [this driver](https://github.com/devbis/st7789py_mpy). While now the common code is minimal, a big thank you to the original author: it was very useful to get started with a very simple codebase.
* All the common graphical primitives, with very fast boxes, fill, hline, vline, and text. Other advanced shapes are also implemented trying to squeeze possible speedups: circles, triangles, and so forth.
* **Very low** memory usage in terms of allocations performed.
* Hopefully clean understandable code.

## Demo

This demo shows what the driver can do if used with an ESP8266EX.
Performances with a modern ESP32 will be much better. Click on the image to see the YouTube video.

[<img src="https://i.ytimg.com/vi/0iNZUMW-uXk/0.jpg" width="50%">](https://www.youtube.com/watch?v=0iNZUMW-uXk "ST77XX driver demo")


*Click the above image to see the video*

## Usage

This driver works with both ST7789 and ST7735 based displays. Other models are yet to be tested. The driver does not require the display to have any data output available (these devices are often MOSI-only).

First of all, you need to create the display object, providing an
SPI interface to communicate with the display (see below in this README what
pins you could use in your device).

Please note that phase/polarity sometimes must be set to '1', or the
display does not work, it depends on the actual display you got.

    import st7789_base, st7789_ext
    from machine import Pin

    display = st7789_ext.ST7789(
        SPI(1, baudrate=40000000, phase=0, polarity=0),
        160, 128,
        reset=machine.Pin(2, machine.Pin.OUT),
        dc=machine.Pin(4, machine.Pin.OUT),
        cs=machine.Pin(10, machine.Pin.OUT),
        inversion = False,
    )

*Note: there are two imports to lower the compile-time memory requirements for MicroPython, you may also want to import only the base module if you just need basic primitives and consume less memory, in this case initialize with st7789_base instead of st7789_ext.*

If colors look inverted, set inversion to True.

Then you need to initialize the display. See "Rotating the display"
section in this README. Here is just an example in case you want to
use a 128x160 display in portrait mode. If you want landscape make also
sure that the initialization of the object above has the width, height
arguments inverted, 128, 160. To initialize:

    display.init(landscape=True,mirror_y=True)

Then you are likely to require a backlight, if you want to see
what the display is displaying. This depends on the display technology
used. Here is an example in case the backlight led pin is connected
to pin 5 of our board:

    backlight = Pin(5,Pin.OUT)
    backlight.on()

At this point if everything went well, you can draw on the display.
Check `test.py` for an example and to verify your display is working.
After editing `test.py` to put your SPI configuration, pins, display
size and so forth, you can run it with:

    mpremote cp st7789*.py :
    mpremote cp lenna.565 :        # Optional, for image demo.
    mpremote run test.py

## Graphic primitives

The following is the list of the graphic primitives available.

    # Fast methods

    def fill(self,color) # Fill entire screen
    def pixel(self,x,y,color) # Draw pixel
    def hline(self,x0,x1,y,color) # Draw fast horizontal line
    def vline(self,y0,y1,x,color) # Draw fast vertical line
    def rect(self,x,y,w,h,color,fill=False) # Draw full or empty rectangle
    def text(self,x,y,txt,bgcolor,fgcolor)  # Draw text
    def image(self,x,y,filename)  # Show image in 565 format

    # Slower methods, they do what they say :)

    def line(self, x0, y0, x1, y1, color)
    def circle(self, x, y, radius, color, fill=False)
    def triangle(self, x0, y0, x1, y1, x2, y2, color, fill=False)
    def upscaled_text(self,x,y,txt,fgcolor,bgcolor=None,upscaling=2)

Everywhere there is to provide a color, you need to create the
color bytes with:

    mycolor = display.color(255,0,255) # RBB

Then use it like that:

    display.rect(10,10,50,50,mycolor,fill=True)

## Writing text

The main API to write text using an 8x8 font is the following one:

    def text(self,x,y,txt,fgcolor,bgcolor)  # Draw text

This method is designed to be fast enough, so it use a small 8x8 frame
buffer inside the device. When using this method, it is mandatory
to specify both the background and foreground color. This means that
what is in the 8x8 area where each character will be rendered will
be replaced with the background color.

There is an alternative **slower API** that has two advanced features:

* You can specify None as background color, if you want to leave the current graphics on the screen as text background.
* It supports upscaling (default 2). So by default this API writes bigger 16x16 characters. If you use 3 they will be 24x24 and so forth. Upscaling of 1 is also supported, in acse you are interested just in preserving the background specifying None, but you want normal sized text of 8x8 pixels.

This is the method signature:

    def upscaled_text(self,x,y,txt,fgcolor,bgcolor=None,upscaling=2)

Examples:

    # 8x8 text, bg preserved.
    display.upscaled_text(10,10,"Hey!",mycolor,upscaling=1)

    # 16x16 text, fg and bg colors specified.
    display.upscaled_text(10,10,"Big text",mycolor,mybg)

    # 32x32 text, background of target area preserved.
    display.upscaled_text(30,30,str(temperature),mycolor,upscaling=4)

## Drawing images

The library is able to display images in a very fast way, transferring
converted images from the filesystem inside the device directly to the
video memory, without wasting more than 256 bytes of local buffers.

In order to do this, images must be converted from PNG to RGB565
format. There is a tool to do this, inside the directory `pngto565`.
Compile it with `make`, then:

    pngto565 file.png file.565

Then transfer the file in the device with:

    mpremote cp file.565 :

And display it with:

    display.image(10,10,"file.565")

Please note that in order to be fast, this method can't do bound checking
so if you display an image at a location where the image will go outside
the limits of the display, the rendered image may look odd / corrupted.

## Rotating the display view

The ST77xx chip is quite able to transparently rotate / mirror the access
to the video memory, so that it is possible to select different rotations
and mirroring of the image without having to transform the image at
software level.

Normally these displays native orientation is portrait (vertical), so
for instance if I have a 128x160 display, by default it will show
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

## Connecting the display to the ESP8266 / ESP32

The ESP8266 and cheaper/older ESP32 models are probably one of the main
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
HSPI), because the SPI 0 is used in order to communicate with
the internal flash memory.

Make sure to set 'polarity' in the SPI interface according to your display specification. Sometimes it is 1 sometimes 0.
