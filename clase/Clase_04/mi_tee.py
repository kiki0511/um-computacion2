#!/usr/bin/env python3
"""
Ejercicio adicional - tee casero.

Replica el comando `tee`: lee de stdin y duplica la salida a stdout Y a uno
o más archivos.

Uso:
    ls -la | python3 mi_tee.py salida.txt
    ls -la | python3 mi_tee.py -a salida.txt   # modo append
    ls -la | python3 mi_tee.py a.txt b.txt     # varios archivos
"""
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Duplica stdin hacia stdout y hacia uno o más archivos."
    )
    parser.add_argument("archivos", nargs="+", help="archivos de destino")
    parser.add_argument("-a", "--append", action="store_true",
                        help="agregar al final en vez de truncar")
    args = parser.parse_args()

    modo = "a" if args.append else "w"
    destinos = []
    try:
        for ruta in args.archivos:
            destinos.append(open(ruta, modo))
    except OSError as e:
        print(f"mi_tee: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        for linea in sys.stdin:
            sys.stdout.write(linea)   # a pantalla
            for f in destinos:
                f.write(linea)        # a cada archivo
    finally:
        for f in destinos:
            f.close()


if __name__ == "__main__":
    main()
