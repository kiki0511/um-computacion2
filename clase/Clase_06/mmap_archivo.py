#!/usr/bin/env python3
"""
Ejercicio 1 - mmap sobre archivos.

mmap mapea un archivo (o memoria anónima) directamente en el espacio de
direcciones del proceso: se accede al contenido como si fuera un bytearray,
y los cambios se reflejan en el archivo en disco sin read()/write()
explícitos.

Incluye:
  - 1.1 mapear, leer, buscar y modificar
  - 1.2 modo solo lectura (ACCESS_READ)
  - Tarea: archivo de 5 líneas, find() + reemplazo del mismo largo
"""
import mmap
import os

ARCHIVO = "/tmp/mmap_test.txt"


def parte_1_1():
    print("=== 1.1: mapear, leer, modificar ===")
    with open(ARCHIVO, "wb") as f:
        f.write(b"Linea 1: Hola mundo\n")
        f.write(b"Linea 2: Computacion II\n")
        f.write(b"Linea 3: mmap es genial\n")

    with open(ARCHIVO, "r+b") as f:
        mm = mmap.mmap(f.fileno(), 0)

        print("Contenido completo:")
        print(mm[:].decode())

        print("Línea por línea:")
        mm.seek(0)
        while True:
            linea = mm.readline()
            if not linea:
                break
            print(f"  {linea.decode().strip()}")

        mm.seek(0)
        pos = mm.find(b"mmap")
        print(f"\n'mmap' encontrado en posición: {pos}")
        mm.seek(pos)
        mm.write(b"MMAP")  # reemplazo del mismo largo

        mm.seek(0)
        print("\nDespués de modificar:")
        print(mm[:].decode())
        mm.close()


def parte_1_2():
    print("=== 1.2: modo solo lectura ===")
    with open(ARCHIVO, "rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        print(f"Contenido: {mm[:40]}")
        print(f"Tamaño: {mm.size()} bytes")
        try:
            mm[0:4] = b"TEST"
        except TypeError as e:
            print(f"Error al escribir (esperado): {e}")
        mm.close()


def tarea_reemplazo():
    """Tarea: 5 líneas, find() + reemplazo del mismo largo, verificar en disco."""
    print("=== Tarea: reemplazo en archivo de 5 líneas ===")
    ruta = "/tmp/mmap_tarea.txt"
    with open(ruta, "wb") as f:
        f.write(b"perro gato pez\n")
        f.write(b"casa arbol sol\n")
        f.write(b"linea con gato adentro\n")
        f.write(b"otra linea cualquiera\n")
        f.write(b"ultima linea del archivo\n")

    with open(ruta, "r+b") as f:
        mm = mmap.mmap(f.fileno(), 0)
        # reemplazar "gato" (4) por "GATO" (4) en todas sus apariciones
        pos = mm.find(b"gato")
        while pos != -1:
            mm.seek(pos)
            mm.write(b"GATO")
            pos = mm.find(b"gato", pos + 4)
        mm.flush()
        mm.close()

    print("Contenido del archivo en disco tras el reemplazo:")
    with open(ruta) as f:
        print(f.read())
    os.unlink(ruta)


def main():
    parte_1_1()
    print()
    parte_1_2()
    print()
    tarea_reemplazo()
    os.unlink(ARCHIVO)


if __name__ == "__main__":
    main()
