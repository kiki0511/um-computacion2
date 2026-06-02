#!/usr/bin/env python3
"""
Ejercicio 4 - Manager para estructuras complejas.

Manager crea un proceso servidor que aloja objetos Python compartidos (dict,
list, etc.). Los demás procesos acceden vía proxies. Permite compartir
estructuras complejas que Value/Array no soportan.

Preguntas:
  - El orden en la lista es el de FINALIZACIÓN de los workers (duración
    aleatoria), no el de creación.
  - Manager es MÁS LENTO que Value/Array: cada acceso pasa por IPC al proceso
    servidor (serialización + comunicación), mientras Value/Array son memoria
    compartida directa. A cambio, Manager soporta estructuras arbitrarias.
"""
from multiprocessing import Process, Manager
import time
import random


def worker(shared_dict, shared_list, wid):
    duracion = random.uniform(0.2, 1.0)
    time.sleep(duracion)

    shared_dict[f"worker_{wid}"] = {
        "status": "done",
        "result": wid ** 2,
        "duracion": round(duracion, 2),
    }
    shared_list.append(f"Worker {wid} completó en {duracion:.2f}s")


def main():
    with Manager() as manager:
        d = manager.dict()
        lst = manager.list()

        procs = [Process(target=worker, args=(d, lst, i)) for i in range(5)]
        for p in procs:
            p.start()
        for p in procs:
            p.join()

        print("Diccionario compartido:")
        for k, v in d.items():
            print(f"  {k}: {v}")

        print("\nLista compartida (orden de finalización):")
        for item in lst:
            print(f"  {item}")


if __name__ == "__main__":
    main()
