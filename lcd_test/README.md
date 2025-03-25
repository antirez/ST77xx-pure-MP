# LCD colors setup test tool

This is simple program to test configuration of your LCD.

Many displays with ST77xx and ILI947x controllers on market has got different type of connections and HW configurations.

For your display to function properly, it is necessary to set not only the communication parameters and its connection to the MCU correctly, but also the correct orientation and display settings.

## Communication settings

If you see only a white or black area on your display, even though you have sent image data to it, it may be due to incorrect communication settings via the SPI bus.
In this case, try setting the _polarity_ parameter to 0 or 1 and the _phase_ to 0 or 1.

If errors appear in the image on your display, check the connection to your display and the baud rate of communication over the SPI bus.

## Screen are upsidedown or mirrored

If you see the image upside down and/or mirrored, change the mirror_x or mirror_y parameters.

If you see a portrait image even though your display is landscape, check the _width_ and _height_ parameters of your display and the _landscape_ parameter.

## Bad colors displayed

If you are seeing incorrect colors, this simple tool should help. LCDs may need to be set to inverse display due to their internal wiring, or may have the red and blue channels swapped (RGB vs BGR).
If you run _lcdcolors.py_ on your device, you should see 6 rectangles and labels in the base colors (red, green, blue, yellow, magenta, cyan) on a black background.

If the background is white, you probably need to change the inversion value to the opposite.

If the colors of the rectangles and texts do not match the color names, you probably need to change the _is_bgr_ parameter to the opposite.
