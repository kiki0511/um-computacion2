#!/usr/bin/env python3
"""
Ejercicio 3 - mmap anónimo entre padre e hijo.

mmap.mmap(-1, tam) crea memoria anónima (sin archivo de respaldo). Si se crea
ANTES del fork, el hijo la hereda y ambos ven la misma región física: es una
forma simple de memoria compartida entre procesos emparentados.

Incluye:
  - 3.1 comunicación simple (un hijo escribe, el padre lee)
  - 3.2 múltiples hijos en regiones separadas
  - Tarea: cada hijo suma un rango y el padre totaliza
"""
import mmap
import os
import struct


def parte_3_1():
    print("=== 3.1: comunicación simple padre-hijo ===")
    mm = mmap.mmap(-1, 256)

    pid = os.fork()
    if pid == 0:
        # HIJO
        struct.pack_into("i", mm, 0, 42)
        mensaje = b"Hola desde el hijo!"
        struct.pack_into("i", mm, 4, len(mensaje))
        mm[8:8 + len(mensaje)] = mensaje
        os._exit(0)
    else:
        # PADRE
        os.wait()
        numero = struct.unpack_from("i", mm, 0)[0]
        largo = struct.unpack_from("i", mm, 4)[0]
        mensaje = bytes(mm[8:8 + largo]).decode()
        print(f"[PADRE] Número: {numero}")
        print(f"[PADRE] Mensaje: {mensaje}")
        mm.close()


def tarea_suma_rangos():
    """Tarea: cada hijo suma un rango de números; el padre totaliza."""
    print("=== Tarea: suma por rangos con mmap anónimo ===")
    NUM_HIJOS = 4
    TAM_POR_HIJO = 8  # un entero de resultado (con margen)
    TOPE = 100        # sumar 1..100 repartido entre los hijos
    por_hijo = TOPE // NUM_HIJOS

    mm = mmap.mmap(-1, NUM_HIJOS * TAM_POR_HIJO)

    hijos = []
    for i in range(NUM_HIJOS):
        pid = os.fork()
        if pid == 0:
            inicio = i * por_hijo + 1
            fin = (i + 1) * por_hijo
            parcial = sum(range(inicio, fin + 1))
            struct.pack_into("i", mm, i * TAM_POR_HIJO, parcial)
            os._exit(0)
        else:
            hijos.append(pid)

    for pid in hijos:
        os.waitpid(pid, 0)

    total = 0
    for i in range(NUM_HIJOS):
        parcial = struct.unpack_from("i", mm, i * TAM_POR_HIJO)[0]
        inicio = i * por_hijo + 1
        fin = (i + 1) * por_hijo
        print(f"  Hijo {i} sumó {inicio}..{fin} = {parcial}")
        total += parcial

    print(f"\nTotal calculado: {total}")
    print(f"Esperado (1..{TOPE}): {TOPE * (TOPE + 1) // 2}")
    mm.close()


def main():
    parte_3_1()
    print()
    tarea_suma_rangos()


if __name__ == "__main__":
    main()
