#!/usr/bin/env python3
"""
Ejercicio adicional - mmap vs lectura secuencial.

Genera un archivo grande (~10 MB) y compara el tiempo de contar un byte
recorriéndolo con lectura secuencial normal (read por bloques) vs mapeándolo
con mmap. Sirve para ver que mmap evita copias entre kernel y user-space.
"""
import mmap
import os
import time

ARCHIVO = "/tmp/grande.bin"
TAMANO = 10 * 1024 * 1024  # 10 MB


def generar_archivo():
    with open(ARCHIVO, "wb") as f:
        f.write(os.urandom(TAMANO))


def contar_secuencial(byte_objetivo):
    total = 0
    with open(ARCHIVO, "rb") as f:
        while True:
            bloque = f.read(65536)
            if not bloque:
                break
            total += bloque.count(byte_objetivo)
    return total


def contar_mmap(byte_objetivo):
    with open(ARCHIVO, "rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        total = mm[:].count(byte_objetivo)
        mm.close()
    return total


def main():
    print("Generando archivo de 10 MB...")
    generar_archivo()
    objetivo = 0x41  # 'A'

    t0 = time.time()
    c1 = contar_secuencial(objetivo)
    t1 = time.time()

    t2 = time.time()
    c2 = contar_mmap(objetivo)
    t3 = time.time()

    print(f"Lectura secuencial: {c1} ocurrencias en {t1 - t0:.4f}s")
    print(f"mmap:               {c2} ocurrencias en {t3 - t2:.4f}s")
    print(f"Coinciden los conteos: {c1 == c2}")

    os.unlink(ARCHIVO)


if __name__ == "__main__":
    main()
