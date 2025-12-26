set -e

CC=cc
CFLAGS=
CLIBS="-lSDL2 -lGL -lGLU -lX11 -lXrandr -lm -I./include"
ENGINE_SRC=engine/*.c
GAME_SRC=game/*.c
OUTPUT=game.elf

set -x

$CC $CFLAGS $ENGINE_SRC $GAME_SRC -o $OUTPUT $CLIBS
