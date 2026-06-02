#!/usr/bin/env python3
"""
Ejercicio 3 - Productor / Consumidor con multiprocessing.Queue.

Queue es una cola FIFO segura entre procesos (maneja el locking internamente).
El productor encola 10 items; el consumidor los procesa hasta recibir un
valor centinela (None) que indica "no hay más".
"""
import multiprocessing
import time
import random

CENTINELA = None


def productor(cola, n):
    for i in range(n):
        item = f"item-{i}"
        cola.put(item)
        print(f"[PRODUCTOR] encolé {item}")
        time.sleep(random.uniform(0.05, 0.2))
    cola.put(CENTINELA)  # avisar fin
    print("[PRODUCTOR] terminé")


def consumidor(cola):
    while True:
        item = cola.get()
        if item is CENTINELA:
            break
        print(f"[CONSUMIDOR] proceso {item}")
        time.sleep(random.uniform(0.05, 0.2))
    print("[CONSUMIDOR] terminé")


def main():
    cola = multiprocessing.Queue()

    p_prod = multiprocessing.Process(target=productor, args=(cola, 10))
    p_cons = multiprocessing.Process(target=consumidor, args=(cola,))

    p_prod.start()
    p_cons.start()
    p_prod.join()
    p_cons.join()

    print("[Main] Productor y consumidor finalizados")


if __name__ == "__main__":
    main()
