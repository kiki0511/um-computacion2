#!/usr/bin/env python3
"""
Ejercicio 6 - SharedMemory y ShareableList.

shared_memory.SharedMemory crea un bloque de memoria compartida con NOMBRE,
accesible por procesos no emparentados (cada uno lo abre por su name). A
diferencia del mmap heredado por fork, sirve para procesos independientes.

ShareableList es una lista de tamaño/tipos fijos sobre SharedMemory, cómoda
para datos mixtos (int, float, str, bool).

Incluye:
  - 6.1 productor/consumidor con SharedMemory + flag de "listo"
  - 6.2 ShareableList con datos mixtos
"""
from multiprocessing import Process, shared_memory
import struct
import time


# ----------------------------------------------------------------------
# 6.1 - SharedMemory productor/consumidor
# ----------------------------------------------------------------------
def productor(shm_name, num_valores):
    shm = shared_memory.SharedMemory(name=shm_name)
    for i in range(num_valores):
        struct.pack_into("i", shm.buf, i * 4, i * i)
    shm.buf[-1] = 1  # marcar como listo (último byte = flag)
    print(f"[PRODUCTOR] Escribí {num_valores} valores")
    shm.close()


def consumidor(shm_name, num_valores):
    shm = shared_memory.SharedMemory(name=shm_name)
    while shm.buf[-1] != 1:  # esperar al productor (polling)
        time.sleep(0.01)
    valores = [struct.unpack_from("i", shm.buf, i * 4)[0]
               for i in range(num_valores)]
    print(f"[CONSUMIDOR] Leí: {valores}")
    shm.close()


def demo_shared_memory():
    print("=== 6.1: SharedMemory productor/consumidor ===")
    NUM = 10
    shm = shared_memory.SharedMemory(create=True, size=NUM * 4 + 1)

    p_prod = Process(target=productor, args=(shm.name, NUM))
    p_cons = Process(target=consumidor, args=(shm.name, NUM))
    p_cons.start()
    p_prod.start()
    p_prod.join()
    p_cons.join()

    shm.close()
    shm.unlink()


# ----------------------------------------------------------------------
# 6.2 - ShareableList con datos mixtos
# ----------------------------------------------------------------------
def actualizar_datos(nombre_shm):
    sl = shared_memory.ShareableList(name=nombre_shm)
    sl[0] = 42
    sl[1] = 3.14159
    sl[2] = "actualizado"   # no debe exceder el largo reservado
    sl[3] = False
    print(f"[WORKER] Lista actualizada: {list(sl)}")
    sl.shm.close()


def demo_shareable_list():
    print("\n=== 6.2: ShareableList con datos mixtos ===")
    # el largo máximo de cada str se fija al crear (de ahí los espacios)
    sl = shared_memory.ShareableList([0, 0.0, "            ", True])
    print(f"Antes:   {list(sl)}")

    p = Process(target=actualizar_datos, args=(sl.shm.name,))
    p.start()
    p.join()

    print(f"Después: {list(sl)}")
    sl.shm.close()
    sl.shm.unlink()


def main():
    demo_shared_memory()
    demo_shareable_list()


if __name__ == "__main__":
    main()
