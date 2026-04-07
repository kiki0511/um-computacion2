#!/usr/bin/env python3
"""Ejercicio 1.1 - Saludo desde argumentos de línea de comandos."""

import sys


def main():
    if len(sys.argv) < 2:
        print(f"Uso: {sys.argv[0]} <nombre>")
        sys.exit(1)

    # Unir todos los argumentos para soportar nombres compuestos
    nombre = " ".join(sys.argv[1:])
    print(f"Hola, {nombre}!")
    sys.exit(0)


if __name__ == "__main__":
    main()
