import st7789_base, st7789_ext as st7789
from machine import freq, Pin, SPI

# Set your own SPI params
SPI_BUS = 0
SPI_SCK = Pin(18)
SPI_MOSI = Pin(19)
# SPI_MISO = None # Optional
SPI_POLARITY = 1
SPI_PHASE = 1
SPI_BAUDRATE = 24000000

# Set your own LCD params
LCD_WIDTH = 320
LCD_HEIGHT = 240
LCD_DC = Pin(17, Pin.OUT)
LCD_RESET = Pin(20, Pin.OUT)
LCD_CS = Pin(21, Pin.OUT)
LCD_LANDSCAPE = True
LCD_MIRROR_X = True
LCD_MIRROR_Y = False
LCD_BGR = False # ST77xx usualy False; ILI934x usualy True
LCD_INVERSE = False
LCD_BACKLIGHT = Pin(16, Pin.OUT)

RECT_WIDTH = 100
RECT_HEIGHT = LCD_HEIGHT / 6
TEXT_UPSCALLING = 3

# Test colors
COLORS = (
    ('Red', 0xFF, 0, 0),
    ('Green', 0, 0xFF, 0),
    ('Blue', 0, 0, 0xFF),
    ('Yellow', 0xFF, 0xFF, 0),
    ('Magenta', 0xFF, 0, 0xFF),
    ('Cyan', 0, 0xFF, 0xFF)
)

lcd_spi = SPI(SPI_BUS, sck=SPI_SCK, mosi=SPI_MOSI, polarity=SPI_POLARITY, phase=SPI_PHASE, baudrate=SPI_BAUDRATE)
display = st7789.ST7789(lcd_spi, LCD_WIDTH, LCD_HEIGHT, dc=Pin(17, Pin.OUT), reset=Pin(20, Pin.OUT), cs=Pin(21, Pin.OUT))
display.init(landscape=LCD_LANDSCAPE, mirror_x=LCD_MIRROR_X, mirror_y=LCD_MIRROR_Y, is_bgr=LCD_BGR, inversion=LCD_INVERSE)
lcd_backlight = LCD_BACKLIGHT
lcd_backlight.on()

y = 0
for color_name, r, g, b in COLORS:
    display.rect(0, y, RECT_WIDTH, RECT_HEIGHT, display.color(r, g, b), fill=True)
    display.upscaled_text(RECT_WIDTH+20, y+8, color_name, display.color(r, g, b), upscaling=TEXT_UPSCALLING)
    y += RECT_HEIGHT
