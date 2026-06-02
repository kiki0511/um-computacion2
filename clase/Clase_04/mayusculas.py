#!/usr/bin/env python3
"""
Ejercicio 6.1 - Filtro Unix: convierte a mayúsculas.

Un "filtro" lee de stdin y escribe en stdout, lo que permite encadenarlo
en pipelines:

    echo "hola mundo" | python3 mayusculas.py
    cat archivo.txt | python3 mayusculas.py | head -5
"""
import sys


def main():
    for linea in sys.stdin:
        sys.stdout.write(linea.upper())


if __name__ == "__main__":
    main()
