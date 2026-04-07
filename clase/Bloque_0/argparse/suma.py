#!/usr/bin/env python3
"""Ejercicio 1.2 - Suma de argumentos numéricos."""

import sys


def main():
    if len(sys.argv) == 1:
        print("Suma: 0")
        sys.exit(0)

    total = 0.0
    hay_decimal = False
    for arg in sys.argv[1:]:
        try:
            valor = float(arg)
            if "." in arg:
                hay_decimal = True
            total += valor
        except ValueError:
            print(f"Error: '{arg}' no es un número válido.")
            sys.exit(1)

    # Mostrar con decimales si algún argumento los tenía, o si el resultado los tiene
    if hay_decimal or total != int(total):
        print(f"Suma: {total}")
    else:
        print(f"Suma: {int(total)}")

    sys.exit(0)


if __name__ == "__main__":
    main()
