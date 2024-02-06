all: pngto565

pngto565: pngto565.c
	$(CC) -O3 pngto565.c `libpng-config --cflags` `libpng-config --L_opts` `libpng-config --libs` -lm -o pngto565 -Wall -W

clean:
	rm -f pngto565
