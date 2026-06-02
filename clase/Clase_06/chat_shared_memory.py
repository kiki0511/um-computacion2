#!/usr/bin/env python3
"""
Ejercicio adicional - Chat simple con SharedMemory.

Dos procesos se turnan para escribir mensajes en un bloque de memoria
compartida. Un byte de flag indica de quién es el turno / si hay mensaje
nuevo. Demuestra coordinación básica por memoria compartida sin sockets.

Layout del buffer:
  byte 0      : turno (0 = proceso A escribe, 1 = proceso B escribe)
  bytes 1..   : longitud (int) + texto del mensaje
"""
from multiprocessing import Process, shared_memory
import struct
import time

TAM = 256
NUM_TURNOS = 4


def escribir_mensaje(shm, texto):
    data = texto.encode()
    struct.pack_into("i", shm.buf, 1, len(data))
    shm.buf[5:5 + len(data)] = data


def leer_mensaje(shm):
    largo = struct.unpack_from("i", shm.buf, 1)[0]
    return bytes(shm.buf[5:5 + largo]).decode()


def proceso(shm_name, mi_turno, nombre, mensajes):
    shm = shared_memory.SharedMemory(name=shm_name)
    for i in range(NUM_TURNOS):
        # esperar mi turno
        while shm.buf[0] != mi_turno:
            time.sleep(0.01)
        # leer lo que dejó el otro (salvo el primer turno del que arranca)
        if not (mi_turno == 0 and i == 0):
            print(f"[{nombre}] recibí: {leer_mensaje(shm)}")
        # escribir mi mensaje y ceder el turno
        escribir_mensaje(shm, mensajes[i])
        print(f"[{nombre}] envié:   {mensajes[i]}")
        shm.buf[0] = 1 - mi_turno
    shm.close()


def main():
    shm = shared_memory.SharedMemory(create=True, size=TAM)
    shm.buf[0] = 0  # arranca el proceso A

    msgs_a = [f"A: hola ({i})" for i in range(NUM_TURNOS)]
    msgs_b = [f"B: que tal ({i})" for i in range(NUM_TURNOS)]

    pa = Process(target=proceso, args=(shm.name, 0, "ProcesoA", msgs_a))
    pb = Process(target=proceso, args=(shm.name, 1, "ProcesoB", msgs_b))
    pa.start()
    pb.start()
    pa.join()
    pb.join()

    shm.close()
    shm.unlink()


if __name__ == "__main__":
    main()
