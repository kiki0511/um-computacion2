#!/usr/bin/env python3
"""
Ejercicio 7.1 - Lector de un named pipe (FIFO).

Abre el FIFO en modo lectura y consume mensajes hasta que el escritor
cierra su extremo (lo que produce EOF y termina el for).

Uso:
    terminal 1:  python3 escritor_fifo.py
    terminal 2:  python3 lector_fifo.py
"""
import os

FIFO = "/tmp/mi_canal"


def main():
    if not os.path.exists(FIFO):
        os.mkfifo(FIFO)

    print(f"Leyendo de {FIFO}...")

    with open(FIFO, "r") as f:
        for linea in f:
            print(f"Recibido: {linea.strip()}")

    print("Lectura completada (el escritor cerró el pipe)")


if __name__ == "__main__":
    main()
