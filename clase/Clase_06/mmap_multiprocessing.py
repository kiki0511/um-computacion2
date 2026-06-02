#!/usr/bin/env python3
"""
Ejercicio 4 - mmap entre procesos con multiprocessing.

Cuando los procesos no comparten memoria por herencia (fork), una opción es
respaldar el mmap con un ARCHIVO: cada proceso abre el mismo archivo y lo
mapea. Los cambios de uno son visibles para los demás a través del archivo.
"""
import mmap
import struct
from multiprocessing import Process
import os

ARCHIVO = "/tmp/mmap_mp.bin"
TAMANO = 256


def escribir_en_mmap(archivo, offset, mensaje):
    with open(archivo, "r+b") as f:
        mm = mmap.mmap(f.fileno(), TAMANO)
        encoded = mensaje.encode()
        struct.pack_into("i", mm, offset, len(encoded))
        mm[offset + 4:offset + 4 + len(encoded)] = encoded
        mm.close()


def main():
    with open(ARCHIVO, "wb") as f:
        f.write(b"\x00" * TAMANO)

    mensajes = [
        "Hola desde proceso 0",
        "Saludos del proceso 1",
        "Proceso 2 presente",
        "Proceso 3 reportando",
    ]

    procesos = []
    for i, msg in enumerate(mensajes):
        p = Process(target=escribir_en_mmap, args=(ARCHIVO, i * 64, msg))
        p.start()
        procesos.append(p)
    for p in procesos:
        p.join()

    with open(ARCHIVO, "r+b") as f:
        mm = mmap.mmap(f.fileno(), TAMANO)
        print("=== Mensajes de los procesos ===")
        for i in range(4):
            offset = i * 64
            largo = struct.unpack_from("i", mm, offset)[0]
            if largo > 0:
                msg = bytes(mm[offset + 4:offset + 4 + largo]).decode()
                print(f"  Proceso {i}: {msg}")
        mm.close()

    os.unlink(ARCHIVO)


if __name__ == "__main__":
    main()
