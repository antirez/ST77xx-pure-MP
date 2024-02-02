# This code is originally from https://github.com/devbis/st7789py_mpy
# It's under the MIT license as well.
#
# Rewritten in terms of MicroPython framebuffer by Salvatore Sanfilippo.
#
# Copyright (C) 2024 Salvatore Sanfilippo <antirez@gmail.com>
# All Rights Reserved
# All the changes released under the MIT license as the original code.

import time
from micropython import const
import ustruct as struct
import framebuf

# Commands. We use a small subset of what is
# available and assume no MISO pin to read
# from the display.
ST77XX_NOP = bytes([0x00])
ST77XX_SWRESET = bytes([0x01])
ST77XX_SLPIN = bytes([0x10])
ST77XX_SLPOUT = bytes([0x11])
ST77XX_NORON = bytes([0x13])
ST77XX_INVOFF = bytes([0x20])
ST77XX_INVON = bytes([0x21])
ST77XX_DISPON = bytes([0x29])
ST77XX_CASET = bytes([0x2A])
ST77XX_RASET = bytes([0x2B])
ST77XX_RAMWR = bytes([0x2C])
ST77XX_COLMOD = bytes([0x3A])
ST7789_MADCTL = bytes([0x36])

# MADCTL command flags
ST7789_MADCTL_MY = const(0x80)
ST7789_MADCTL_MX = const(0x40)
ST7789_MADCTL_MV = const(0x20)
ST7789_MADCTL_ML = const(0x10)
ST7789_MADCTL_BGR = const(0x08)
ST7789_MADCTL_MH = const(0x04)
ST7789_MADCTL_RGB = const(0x00)

# COLMOD command flags
ColorMode_65K = const(0x50)
ColorMode_262K = const(0x60)
ColorMode_12bit = const(0x03)
ColorMode_16bit = const(0x05)
ColorMode_18bit = const(0x06)
ColorMode_16M = const(0x07)

# Struct pack formats for pixel/pos encoding
_ENCODE_PIXEL = ">H"
_ENCODE_POS = ">HH"

class ST7789:
    def __init__(self, spi, width, height, reset, dc, cs=None, backlight=None,
                 xstart=-1, ystart=-1, inversion=False, fbmode=None):
        """
        display = st7789.ST7789(
            SPI(1, baudrate=40000000, phase=0, polarity=1),
            240, 240,
            reset=machine.Pin(5, machine.Pin.OUT),
            dc=machine.Pin(2, machine.Pin.OUT),
        )

        """
        self.width = width
        self.height = height
        self.spi = spi
        self.reset = reset
        self.dc = dc
        self.cs = cs
        self.backlight = backlight
        self.inversion = inversion

        # Configure display parameters that depend on the
        # screen size.
        if xstart >= 0 and ystart >= 0:
            self.xstart = xstart
            self.ystart = ystart
        elif (self.width, self.height) == (128, 160):
            self.xstart = 0
            self.ystart = 0
        elif (self.width, self.height) == (240, 240):
            self.xstart = 0
            self.ystart = 0
        elif (self.width, self.height) == (135, 240):
            self.xstart = 52
            self.ystart = 40
        else:
            self.xstart = 0
            self.ystart = 0

        # Always allocate a tiny 8x8 framebuffer in RGB565 for fast
        # single chars plotting. This is useful in order to draw text
        # using the framebuffer 8x8 font inside micropython and using
        # a single SPI write for each whole character.
        self.charfb_data = bytearray(8*8*2)
        self.charfb = framebuf.FrameBuffer(self.charfb_data,8,8,framebuf.RGB565)

    def color565(self, r=0, g=0, b=0):
        return (r & 0xf8) << 8 | (g & 0xfc) << 3 | b >> 3

    def color565_raw(self, r=0, g=0, b=0):
        # Convert red, green and blue values (0-255) into a 16-bit 565 encoding.
        return struct.pack(_ENCODE_PIXEL, self.color565(r,g,b))

    def write(self, command=None, data=None):
        """SPI write to the device: commands and data"""
        if command is not None:
            self.dc.off()
            self.spi.write(command)
        if data is not None:
            self.dc.on()
            self.spi.write(data)

    def hard_reset(self):
        if self.reset:
            self.reset.on()
            time.sleep_ms(50)
            self.reset.off()
            time.sleep_ms(50)
            self.reset.on()
            time.sleep_ms(150)

    def soft_reset(self):
        self.write(ST77XX_SWRESET)
        time.sleep_ms(150)

    def sleep_mode(self, value):
        if value:
            self.write(ST77XX_SLPIN)
        else:
            self.write(ST77XX_SLPOUT)

    def inversion_mode(self, value):
        if value:
            self.write(ST77XX_INVON)
        else:
            self.write(ST77XX_INVOFF)

    def _set_color_mode(self, mode):
        self.write(ST77XX_COLMOD, bytes([mode & 0x77]))

    def init(self, *args, **kwargs):
        self.cs.off() # This this like that forever, much faster than
                      # continuously setting it on/off and rarely the
                      # SPI is connected to any other hardware.
        self.hard_reset()
        self.soft_reset()
        self.sleep_mode(False)

        color_mode=ColorMode_65K | ColorMode_16bit
        self._set_color_mode(color_mode)
        time.sleep_ms(50)
        self._set_mem_access_mode(0, False, False, False)
        self.inversion_mode(self.inversion)
        time.sleep_ms(10)
        self.write(ST77XX_NORON)
        time.sleep_ms(10)
        self.raw_fill(self.color565_raw(0,0,0))
        self.write(ST77XX_DISPON)
        time.sleep_ms(500)

    def _set_mem_access_mode(self, rotation, vert_mirror, horz_mirror, is_bgr):
        rotation &= 7
        value = {
            0: 0,
            1: ST7789_MADCTL_MX,
            2: ST7789_MADCTL_MY,
            3: ST7789_MADCTL_MX | ST7789_MADCTL_MY,
            4: ST7789_MADCTL_MV,
            5: ST7789_MADCTL_MV | ST7789_MADCTL_MX,
            6: ST7789_MADCTL_MV | ST7789_MADCTL_MY,
            7: ST7789_MADCTL_MV | ST7789_MADCTL_MX | ST7789_MADCTL_MY,
        }[rotation]

        if vert_mirror: value |= ST7789_MADCTL_ML
        elif horz_mirror: value |= ST7789_MADCTL_MH
        if is_bgr: value |= ST7789_MADCTL_BGR

        self.write(ST7789_MADCTL, bytes([value]))

    def _encode_pos(self, x, y):
        """Encode a postion into bytes."""
        return struct.pack(_ENCODE_POS, x, y)

    def _set_columns(self, start, end):
        self.write(ST77XX_CASET, self._encode_pos(start+self.xstart, end+self.xstart))

    def _set_rows(self, start, end):
        start += self.ystart
        end += self.ystart
        self.write(ST77XX_RASET, self._encode_pos(start+self.ystart, end+self.ystart))

    def set_window(self, x0, y0, x1, y1):
        self._set_columns(x0, x1)
        self._set_rows(y0, y1)
        self.write(ST77XX_RAMWR)

    # Drawing raw pixels is a fundamental operation so we go low
    # level avoiding function calls. This and other optimizations
    # made drawing 10k pixels with an ESP2866 from 420ms to 100ms.
    @micropython.native
    def raw_pixel(self,x,y,color):
        if x >= self.width: return
        self.dc.off()
        self.spi.write(ST77XX_CASET)
        self.dc.on()
        self.spi.write(self._encode_pos(x, x))

        self.dc.off()
        self.spi.write(ST77XX_RASET)
        self.dc.on()
        self.spi.write(self._encode_pos(y, y))

        self.dc.off()
        self.spi.write(ST77XX_RAMWR)
        self.dc.on()
        self.spi.write(color)

    # Just fill the whole display memory with the specified color.
    # We use a buffer of screen-width pixels. Even in the worst case
    # of 320 pixels, it's just 640 bytes. Note that writing a scanline
    # per loop dramatically improves performances.
    def raw_fill(self,color):
        self.set_window(0, 0, self.width-1, self.height-1)
        buf = color*self.width
        for i in range(self.height): self.write(None, buf)

    # We can draw horizontal and vertical lines very fast because
    # we can just set a 1 pixel wide/tall window and fill it.
    def raw_hline(self,x0,x1,y,color):
        if x0 < 0: x0 = 0
        if x1 >= self.width: x1 = self.width-1
        self.set_window(x0, y, x1, y)
        self.write(None, color*(x1-x0+1))

    # Same as .raw_hline() but for vertical lines.
    def raw_vline(self,y0,y1,x,color):
        self.set_window(x, y0, x, y1)
        self.write(None, color*(y1-y0+1))

    # Midpoint Circle algorithm for filled circle.
    def raw_circle(self, x, y, radius, color, fill=False):
        f = 1 - radius
        dx = 1
        dy = -2 * radius
        x0 = 0
        y0 = radius

        if fill:
            self.raw_hline(x - radius, x + radius, y, color) # Draw diameter
        else:
            self.raw_pixel(x - radius, y, color) # Left-most point
            self.raw_pixel(x + radius, y, color) # Right-most point

        while x0 < y0:
            if f >= 0:
                y0 -= 1
                dy += 2
                f += dy
            x0 += 1
            dx += 2
            f += dx

            if fill:
				# We can exploit our relatively fast horizontal line
				# here, and just draw an h line for each two points at
				# the extremes.
                self.raw_hline(x - x0, x + x0, y + y0, color) # Upper half
                self.raw_hline(x - x0, x + x0, y - y0, color) # Lower half
                self.raw_hline(x - y0, x + y0, y + x0, color) # Right half
                self.raw_hline(x - y0, x + y0, y - x0, color) # Left half
            else:
				# Plot points in each of the eight octants
				self.raw_pixel(x + x0, y + y0, color)
				self.raw_pixel(x - x0, y + y0, color)
				self.raw_pixel(x + x0, y - y0, color)
				self.raw_pixel(x - x0, y - y0, color)
				self.raw_pixel(x + y0, y + x0, color)
				self.raw_pixel(x - y0, y + x0, color)
				self.raw_pixel(x + y0, y - x0, color)
				self.raw_pixel(x - y0, y - x0, color)

    # Draw a single character 'char' using the font in the MicroPython
    # framebuffer implementation. It is possible to specify the background and
    # foreground color in RGB.
    def char(self,x,y,char,bgcolor,fgcolor):
        self.charfb.fill(bgcolor)
        self.charfb.text(char,0,0,fgcolor)
        self.set_window(x, y, x+7, y+7)
        self.write(None,self.charfb_data)

    # Write text. Like 'char' but for full strings.
    def text(self,x,y,txt,bgcolor,fgcolor):
        for i in range(len(txt)):
            self.char(x+i*8,y,txt[i],bgcolor,fgcolor)

    def contrast(self,level):
        # TODO: implement me!
        pass
