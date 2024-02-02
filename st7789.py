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

# commands
ST77XX_NOP = bytes([0x00])
ST77XX_SWRESET = bytes([0x01])
ST77XX_RDDID = bytes([0x04])
ST77XX_RDDST = bytes([0x09])

ST77XX_SLPIN = bytes([0x10])
ST77XX_SLPOUT = bytes([0x11])
ST77XX_PTLON = bytes([0x12])
ST77XX_NORON = bytes([0x13])

ST77XX_INVOFF = bytes([0x20])
ST77XX_INVON = bytes([0x21])
ST77XX_DISPOFF = bytes([0x28])
ST77XX_DISPON = bytes([0x29])
ST77XX_CASET = bytes([0x2A])
ST77XX_RASET = bytes([0x2B])
ST77XX_RAMWR = bytes([0x2C])
ST77XX_RAMRD = bytes([0x2E])

ST77XX_PTLAR = bytes([0x30])
ST77XX_VSCRDEF = bytes([0x33])
ST77XX_COLMOD = bytes([0x3A])
ST7789_MADCTL = bytes([0x36])

# MADCTL flags
ST7789_MADCTL_MY = const(0x80)
ST7789_MADCTL_MX = const(0x40)
ST7789_MADCTL_MV = const(0x20)
ST7789_MADCTL_ML = const(0x10)
ST7789_MADCTL_BGR = const(0x08)
ST7789_MADCTL_MH = const(0x04)
ST7789_MADCTL_RGB = const(0x00)

# Color mode flags
ColorMode_65K = const(0x50)
ColorMode_262K = const(0x60)
ColorMode_12bit = const(0x03)
ColorMode_16bit = const(0x05)
ColorMode_18bit = const(0x06)
ColorMode_16M = const(0x07)

# Color definitions
BLACK = const(0x0000)
BLUE = const(0x001F)
RED = const(0xF800)
GREEN = const(0x07E0)
CYAN = const(0x07FF)
MAGENTA = const(0xF81F)
YELLOW = const(0xFFE0)
WHITE = const(0xFFFF)

_ENCODE_PIXEL = ">H"
_ENCODE_POS = ">HH"
_DECODE_PIXEL = ">BBB"

class ST7789:
    def __init__(self, spi, width, height, reset, dc, cs=None, backlight=None,
                 xstart=-1, ystart=-1, inversion=False, mono=False):
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
        self.mono = mono
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

        if self.mono:
            self.rawbuffer = bytearray(width*height//8)
            self.fb = framebuf.FrameBuffer(self.rawbuffer,width,height,
                                           framebuf.MONO_HLSB)
            self.mono_row = bytearray(self.width*2) # Mono -> RGB565 row conv.
            # See the show() method. The conversion map is useful
            # to speedup rendering a bitmap as RGB565.
            self.mono_conv_map = {
                byte: bytes(sum(((0xFF, 0xFF) if (byte >> bit) & 1 else (0x00, 0x00) for bit in range(7, -1, -1)), ()))
                for byte in range(256)
            }
        else:
            self.rawbuffer = bytearray(width*height*2)
            self.fb = framebuf.FrameBuffer(self.rawbuffer,width,height,
                                           framebuf.RGB565)
        self.fill = self.fb.fill
        self.pixel = self.fb.pixel
        self.hline = self.fb.hline
        self.vline = self.fb.vline
        self.line = self.fb.line
        self.rect = self.fb.rect
        self.fill_rect = self.fb.fill_rect
        # self.ellipse = self.fb.ellipse
        # self.poly = self.fb.poly
        self.text = self.fb.text
        self.scroll = self.fb.scroll
        self.blit = self.fb.blit

    def color565(self, r=0, g=0, b=0):
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
        self.fill(0)
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
        if start > end or end >= self.width:
            return
        start += self.xstart
        end += self.xstart
        self.write(ST77XX_CASET, self._encode_pos(start, end))

    def _set_rows(self, start, end):
        if start > end or end >= self.height:
            return
        start += self.ystart
        end += self.ystart
        self.write(ST77XX_RASET, self._encode_pos(start, end))

    def set_window(self, x0, y0, x1, y1):
        self._set_columns(x0, x1)
        self._set_rows(y0, y1)
        self.write(ST77XX_RAMWR)

    @micropython.native
    def show(self):
        self.set_window(0, 0, self.width-1,self.height-1)
        if self.mono:
            for i in range(0,len(self.rawbuffer),self.width//8):
                for j in range(self.width//8):
                    self.mono_row[j*16:(j+1)*16] = self.mono_conv_map[self.rawbuffer[i+j]]
                self.write(None, self.mono_row)
        else:
            self.write(None, self.rawbuffer)

    def raw_pixel(self,x,y,color):
        self.set_window(x, y, x, y)
        self.write(None, color)

    @micropython.native
    def raw_pixel_fast(self,x,y,color):
        if True:
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

        if False:
            self.write(ST77XX_CASET, self._encode_pos(x, x))
            self.write(ST77XX_RASET, self._encode_pos(y, y))
            self.write(ST77XX_RAMWR, color)

    def raw_fill(self,color):
        self.set_window(0, 0, self.width-1, self.height-1)
        left = self.width*self.height
        buflen = 64
        buf = color*buflen
        while left >= len(buf):
            self.write(None, buf)
            left -= buflen
        while left:
            self.write(None, color)
            left -= 1

    def contrast(self,level):
        # TODO: implement me!
        pass
