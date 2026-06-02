#!/usr/bin/env python3
"""
Ejercicio 2 - Comparación secuencial vs paralelo (CPU-bound).

Mide el speedup de Pool con 1, 2, 4 y 8 workers sobre una tarea CPU-intensive.
El speedup crece hasta saturar los núcleos físicos; más workers que núcleos no
acelera (e incluso puede ralentizar por overhead y cambio de contexto).
"""
from multiprocessing import Pool
import time
import math

N = 500_000
TAREAS = 8


def cpu_task(n):
    return sum(math.sqrt(i) for i in range(n))


def main():
    # Secuencial
    inicio = time.time()
    [cpu_task(N) for _ in range(TAREAS)]
    t_seq = time.time() - inicio
    print(f"Secuencial:  {t_seq:.2f}s")

    for workers in [1, 2, 4, 8]:
        inicio = time.time()
        with Pool(workers) as pool:
            pool.map(cpu_task, [N] * TAREAS)
        t_par = time.time() - inicio
        speedup = t_seq / t_par
        print(f"Pool({workers}):    {t_par:.2f}s  (speedup: {speedup:.2f}x)")


if __name__ == "__main__":
    main()
