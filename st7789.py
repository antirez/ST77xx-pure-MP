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
                 xstart=None, ystart=None, inversion=False, fbmode=None):
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
        if xstart and ystart:
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

    # That's the color format our API takes. We take r, g, b, translate
    # to 16 bit value and pack it as as two bytes.
    def color(self, r=0, g=0, b=0):
        # Convert red, green and blue values (0-255) into a 16-bit 565 encoding.
        c = (r & 0xf8) << 8 | (g & 0xfc) << 3 | b >> 3
        return struct.pack(_ENCODE_PIXEL, c)

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

    def init(self, landscape=False, mirror_x=False, mirror_y=False, is_bgr=False):
        self.cs.off() # This this like that forever, much faster than
                      # continuously setting it on/off and rarely the
                      # SPI is connected to any other hardware.
        self.hard_reset()
        self.soft_reset()
        self.sleep_mode(False)

        color_mode=ColorMode_65K | ColorMode_16bit
        self._set_color_mode(color_mode)
        time.sleep_ms(50)
        self._set_mem_access_mode(landscape, mirror_x, mirror_y, is_bgr)
        self.inversion_mode(self.inversion)
        time.sleep_ms(10)
        self.write(ST77XX_NORON)
        time.sleep_ms(10)
        self.fill(self.color(0,0,0))
        self.write(ST77XX_DISPON)
        time.sleep_ms(500)

    def _set_mem_access_mode(self, landscape, mirror_x, mirror_y, is_bgr):
        value = 0
        if landscape: value |= ST7789_MADCTL_MV
        if mirror_x: value |= ST7789_MADCTL_MX
        if mirror_y: value |= ST7789_MADCTL_MY
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

    # Set the video memory windows that will be receive our
    # SPI data writes. Note that this function assumes that
    # x0 <= x1 and y0 <= y1.
    def set_window(self, x0, y0, x1, y1):
        self._set_columns(x0, x1)
        self._set_rows(y0, y1)
        self.write(ST77XX_RAMWR)

    # Drawing raw pixels is a fundamental operation so we go low
    # level avoiding function calls. This and other optimizations
    # made drawing 10k pixels with an ESP2866 from 420ms to 100ms.
    @micropython.native
    def pixel(self,x,y,color):
        if x < 0 or x >= self.width or y < 0 or y >= self.height: return
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
    def fill(self,color):
        self.set_window(0, 0, self.width-1, self.height-1)
        buf = color*self.width
        for i in range(self.height): self.write(None, buf)

    # We can draw horizontal and vertical lines very fast because
    # we can just set a 1 pixel wide/tall window and fill it.
    def hline(self,x0,x1,y,color):
        if y < 0 or y >= self.height: return
        x0,x1 = max(min(x0,x1),0),min(max(x0,x1),self.width-1)
        self.set_window(x0, y, x1, y)
        self.write(None, color*(x1-x0+1))

    # Same as hline() but for vertical lines.
    def vline(self,y0,y1,x,color):
        y0,y1 = max(min(y0,y1),0),min(max(y0,y1),self.height-1)
        self.set_window(x, y0, x, y1)
        self.write(None, color*(y1-y0+1))

    # Bresenham's algorithm with fast path for horizontal / vertical lines.
    # Note that here a further optimization is possible exploiting how the
    # ST77xx addresses memory: we should always trace lines from smaller x,y
    # to higher x,y values, then as long as we keep incrementing the "x" or
    # "y" coordinate we could not change the set memory window, and just
    # write the color bytes the ST77xx. Only when we change which variable
    # we increment, we set the window again.
    def line(self, x0, y0, x1, y1, color):
        if y0 == y1: return self.hline(x0, x1, y0, color)
        if x0 == x1: return self.vline(y0, y1, x0, color)

        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy  # Error value for xy

        while True:
            self.pixel(x0, y0, color)
            if x0 == x1 and y0 == y1: break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    # Midpoint Circle algorithm for filled circle.
    def circle(self, x, y, radius, color, fill=False):
        f = 1 - radius
        dx = 1
        dy = -2 * radius
        x0 = 0
        y0 = radius

        if fill:
            self.hline(x - radius, x + radius, y, color) # Draw diameter
        else:
            self.pixel(x - radius, y, color) # Left-most point
            self.pixel(x + radius, y, color) # Right-most point

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
                self.hline(x - x0, x + x0, y + y0, color) # Upper half
                self.hline(x - x0, x + x0, y - y0, color) # Lower half
                self.hline(x - y0, x + y0, y + x0, color) # Right half
                self.hline(x - y0, x + y0, y - x0, color) # Left half
            else:
				# Plot points in each of the eight octants
				self.pixel(x + x0, y + y0, color)
				self.pixel(x - x0, y + y0, color)
				self.pixel(x + x0, y - y0, color)
				self.pixel(x - x0, y - y0, color)
				self.pixel(x + y0, y + x0, color)
				self.pixel(x - y0, y + x0, color)
				self.pixel(x + y0, y - x0, color)
				self.pixel(x - y0, y - x0, color)

	# This function draws a filled triangle: it is an
	# helper of .triangle when the fill flag is true.
    def fill_triangle(self, x0, y0, x1, y1, x2, y2, color):
        # Vertex are required to be ordered by y.
        if y0 > y1: x0, y0, x1, y1 = x1, y1, x0, y0
        if y0 > y2: x0, y0, x2, y2 = x2, y2, x0, y0
        if y1 > y2: x1, y1, x2, y2 = x2, y2, x1, y1

        # Calculate slopes.
        inv_slope1 = (x1 - x0) / (y1 - y0) if y1 - y0 != 0 else 0
        inv_slope2 = (x2 - x0) / (y2 - y0) if y2 - y0 != 0 else 0
        inv_slope3 = (x2 - x1) / (y2 - y1) if y2 - y1 != 0 else 0

        x_start, x_end = x0, x0

        # Fill upper part.
        for y in range(y0, y1 + 1):
            self.hline(int(x_start), int(x_end), y, color)
            x_start += inv_slope1
            x_end += inv_slope2

        # Adjust for the middle segment.
        x_start = x1

        # Fill the lower part.
        for y in range(y1 + 1, y2 + 1):
            self.hline(int(x_start), int(x_end), y, color)
            x_start += inv_slope3
            x_end += inv_slope2

    # Draw full or empty triangles.
    def triangle(self, x0, y0, x1, y1, x2, y2, color, fill=False):
        if fill:
            return self.fill_triangle(x0,y0,x1,y1,x2,y2,color)
        else:
            self.line(x0,y0,x1,y1,color)
            self.line(x1,y1,x2,y2,color)
            self.line(x2,y2,x0,y0,color)

    # Draw a single character 'char' using the font in the MicroPython
    # framebuffer implementation. It is possible to specify the background and
    # foreground color in RGB.
    # Note: in order to uniform this API with all the rest, that takes
    # the color as two bytes, we convert the colors back into a 16 bit
    # rgb565 value since this is the format that the framebuffer
    # implementation expects.
    def char(self,x,y,char,bgcolor,fgcolor):
        if x >= self.width or y >= self.height:
            return # Totally out of display area

        # Obtain the character representation in our
        # 8x8 framebuffer.
        self.charfb.fill(struct.unpack(">H",bgcolor)[0])
        self.charfb.text(char,0,0,struct.unpack(">H",fgcolor)[0])

        if x+7 >= self.width:
            # Right side of char does not fit on the screen.
            # Partial update.
            width = self.width-x # Visible width pixels
            self.set_window(x, y, x+width-1, y+7)
            copy = bytearray(width*8*2)
            for dy in range(8):
                src_idx = (dy*8)*2
                dst_idx = (dy*width)*2
                copy[dst_idx:dst_idx+width*2] = self.charfb_data[src_idx:src_idx+width*2]
            self.write(None,copy)
        else:
            self.set_window(x, y, x+7, y+7)
            self.write(None,self.charfb_data)

    # Write text. Like 'char' but for full strings.
    def text(self,x,y,txt,bgcolor,fgcolor):
        for i in range(len(txt)):
            self.char(x+i*8,y,txt[i],bgcolor,fgcolor)

    def contrast(self,level):
        # TODO: implement me!
        pass
