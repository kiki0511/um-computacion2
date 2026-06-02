#!/usr/bin/env python3
"""
Ejercicio 2 - 5 workers en paralelo.

Lanza 5 procesos que duermen un tiempo aleatorio (0.5–2 s). El main espera a
todos con join() y reporta el tiempo total, que es ~ el del worker más lento
(corren en paralelo), no la suma.
"""
import multiprocessing
import time
import random


def worker(wid):
    duracion = random.uniform(0.5, 2.0)
    print(f"[Worker-{wid}] arranca, dormirá {duracion:.2f}s")
    time.sleep(duracion)
    print(f"[Worker-{wid}] termina")


def main():
    inicio = time.time()

    procesos = []
    for i in range(5):
        p = multiprocessing.Process(target=worker, args=(i,))
        p.start()
        procesos.append(p)

    for p in procesos:
        p.join()

    total = time.time() - inicio
    print(f"\n[Main] Todos terminaron. Tiempo total: {total:.2f}s")
    print("(≈ el del worker más lento, no la suma de los 5)")


if __name__ == "__main__":
    main()
