#!/usr/bin/env python3
"""
Ejercicio 2 - mmap como estructura de datos binaria.

Con el módulo struct se empaquetan tipos de C (enteros, floats, strings) en
bytes y se escriben directamente en el mmap a un offset dado. Así el mmap
funciona como un arreglo binario de tamaño fijo.

Incluye:
  - 2.1 almacenar y leer 10 enteros
  - Tarea: registros con formato 'i f 20s' (id, nota, nombre)
"""
import mmap
import struct
import os


def parte_2_1():
    print("=== 2.1: almacenar y leer enteros ===")
    archivo = "/tmp/numeros.bin"
    num = 10
    tam = num * 4  # 4 bytes por entero ('i')

    with open(archivo, "wb") as f:
        f.write(b"\x00" * tam)

    with open(archivo, "r+b") as f:
        mm = mmap.mmap(f.fileno(), tam)

        for i in range(num):
            struct.pack_into("i", mm, i * 4, (i + 1) * 100)

        print("Leyendo:")
        for i in range(num):
            valor = struct.unpack_from("i", mm, i * 4)[0]
            print(f"  Posición {i}: {valor}")

        struct.pack_into("i", mm, 3 * 4, 9999)
        print(f"\nPosición 3 modificada a: "
              f"{struct.unpack_from('i', mm, 3 * 4)[0]}")
        mm.close()

    os.unlink(archivo)


def tarea_registros():
    """Tarea: 5 registros (id:int, nota:float, nombre:20 bytes)."""
    print("=== Tarea: registros estructurados ===")
    archivo = "/tmp/registros.bin"
    FORMATO = "i f 20s"
    TAM_REG = struct.calcsize(FORMATO)
    NUM = 5

    datos = [
        (1, 8.5, b"Ana"),
        (2, 7.0, b"Bruno"),
        (3, 9.25, b"Carla"),
        (4, 6.75, b"Diego"),
        (5, 10.0, b"Elena"),
    ]

    with open(archivo, "wb") as f:
        f.write(b"\x00" * (TAM_REG * NUM))

    with open(archivo, "r+b") as f:
        mm = mmap.mmap(f.fileno(), TAM_REG * NUM)

        # Escribir
        for i, (rid, nota, nombre) in enumerate(datos):
            struct.pack_into(FORMATO, mm, i * TAM_REG, rid, nota, nombre)

        # Leer
        print(f"Tamaño de cada registro: {TAM_REG} bytes")
        for i in range(NUM):
            rid, nota, nombre = struct.unpack_from(FORMATO, mm, i * TAM_REG)
            nombre = nombre.rstrip(b"\x00").decode()
            print(f"  Registro {i}: id={rid}, nota={nota:.2f}, nombre='{nombre}'")
        mm.close()

    os.unlink(archivo)


def main():
    parte_2_1()
    print()
    tarea_registros()


if __name__ == "__main__":
    main()
