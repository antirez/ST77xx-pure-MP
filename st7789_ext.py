# This code is originally from https://github.com/devbis/st7789py_mpy
# It's under the MIT license as well.
#
# Rewritten by Salvatore Sanfilippo.
#
# Copyright (C) 2024 Salvatore Sanfilippo <antirez@gmail.com>
# All Rights Reserved
# All the changes released under the MIT license as the original code.

import st7789_base, framebuf, struct

class ST7789(st7789_base.ST7789_base):
    # Bresenham's algorithm with fast path for horizontal / vertical lines.
    # Note that accumulating partial successive small horizontal/vertical
    # lines is actually slower than the vanilla pixel approach.
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

    # Write an upscaled character. Slower, but allows for big characters
    # and to set the background color to None.
    def upscaled_char(self,x,y,char,fgcolor,bgcolor,upscaling):
        bitmap = bytearray(8) # 64 bits of total image data.
        fb = framebuf.FrameBuffer(bitmap,8,8,framebuf.MONO_HMSB)
        fb.text(char,0,0,fgcolor[1]<<8|fgcolor[0])
        charsize = 8*upscaling
        if bgcolor: self.rect(x,y,charsize,charsize,bgcolor,fill=True)
        for py in range(8):
            for px in range(8):
                if not (bitmap[py] & (1<<px)): continue # Background
                if upscaling > 1:
                    self.rect(x+px*upscaling,y+py*upscaling,upscaling,upscaling,fgcolor,fill=True)
                else:
                    self.pixel(x+px,y+py,fgcolor)

    def upscaled_text(self,x,y,txt,fgcolor,*,bgcolor=None,upscaling=2):
        for i in range(len(txt)):
            self.upscaled_char(x+i*(8*upscaling),y,txt[i],fgcolor,bgcolor,upscaling)

    # Show a 565 file (see conversion tool into "pngto565".
    def image(self,x,y,filename):
        try:
            f = open(filename,"rb")
        except:
            print("Warning: file not found displaying image:", filename)
            return
        hdr = f.read(4)
        w,h = struct.unpack(">HH",hdr)
        self.set_window(x,y,x+w-1,y+h-1)
        buf = bytearray(256)
        nocopy = memoryview(buf)
        while True:
            nread = f.readinto(buf)
            if nread == 0: return
            self.write(None, nocopy[:nread])


