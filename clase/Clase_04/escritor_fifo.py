#!/usr/bin/env python3
"""
Ejercicio 7.1 - Escritor de un named pipe (FIFO).

Un named pipe (FIFO) es un pipe con nombre en el filesystem, creado con
os.mkfifo(). A diferencia de os.pipe(), permite comunicar procesos que NO
tienen relación padre-hijo: cada uno lo abre por su ruta.

Uso (en dos terminales):
    terminal 1:  python3 escritor_fifo.py
    terminal 2:  python3 lector_fifo.py

Nota: open() del FIFO en modo escritura BLOQUEA hasta que haya un lector
del otro lado (y viceversa). Eso es el comportamiento normal de un FIFO.
"""
import os
import time

FIFO = "/tmp/mi_canal"


def main():
    if not os.path.exists(FIFO):
        os.mkfifo(FIFO)

    print(f"Escribiendo a {FIFO}...")
    print("(Ejecutá lector_fifo.py en otra terminal)")

    with open(FIFO, "w") as f:
        for i in range(10):
            mensaje = f"Mensaje {i}: {time.ctime()}"
            print(f"Enviando: {mensaje}")
            f.write(mensaje + "\n")
            f.flush()
            time.sleep(1)

    print("Escritura completada")


if __name__ == "__main__":
    main()
