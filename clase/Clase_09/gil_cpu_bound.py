#!/usr/bin/env python3
"""
Ejercicio 3 - GIL en acción (CPU-bound).

`cpu_task(n)` es CPU-intensive (suma raíces cuadradas de 0 a n).

Para que la comparación sea justa, cada bloque ejecuta la MISMA cantidad de
llamadas a cpu_task(N), variando solo cómo se distribuyen:

- 2 llamadas: secuencial vs 2 threads
- 4 llamadas: secuencial vs 4 threads vs 4 procesos (bonus)

Resultado esperado: con threads NO hay mejora (o incluso empeora un poco por
el overhead de crear hilos y el cambio de contexto del GIL). El GIL permite
que solo UN hilo ejecute bytecode de Python a la vez, así que para trabajo
CPU-bound los threads no paralelizan, solo se van turnando.

Como bonus, se repite la prueba con multiprocessing.Process: cada proceso
tiene su propio intérprete y su propio GIL, así que ahí sí se aprovechan
varios cores (si la máquina los tiene).
"""
import math
import multiprocessing
import threading
import time


def cpu_task(n):
    return sum(math.sqrt(i) for i in range(n))


N = 2_000_000


def correr_secuencial(veces):
    inicio = time.perf_counter()
    for _ in range(veces):
        cpu_task(N)
    return time.perf_counter() - inicio


def correr_threads(cantidad):
    inicio = time.perf_counter()
    hilos = [threading.Thread(target=cpu_task, args=(N,)) for _ in range(cantidad)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    return time.perf_counter() - inicio


def correr_procesos(cantidad):
    inicio = time.perf_counter()
    procesos = [multiprocessing.Process(target=cpu_task, args=(N,)) for _ in range(cantidad)]
    for p in procesos:
        p.start()
    for p in procesos:
        p.join()
    return time.perf_counter() - inicio


def main():
    print("=== Comparación con 2 llamadas a cpu_task ===")
    t_seq2 = correr_secuencial(2)
    t_2h = correr_threads(2)
    print(f"Secuencial (2x): {t_seq2:.2f}s")
    print(f"2 threads:       {t_2h:.2f}s")

    print("\n=== Comparación con 4 llamadas a cpu_task ===")
    t_seq4 = correr_secuencial(4)
    t_4h = correr_threads(4)
    t_4p = correr_procesos(4)
    print(f"Secuencial (4x): {t_seq4:.2f}s")
    print(f"4 threads:       {t_4h:.2f}s")
    print(f"4 procesos:      {t_4p:.2f}s  (bonus, multiprocessing)")

    print("\n--- Conclusión ---")
    print("Con threads, el tiempo se mantiene ≈ igual al secuencial (o peor):")
    print("el GIL impide que dos hilos ejecuten bytecode Python al mismo")
    print("tiempo, así que para CPU-bound threading no paraleliza, solo")
    print("intercala con overhead extra.")
    if t_4p > 0:
        print(f"\nSpeedup multiprocessing vs secuencial: {t_seq4 / t_4p:.2f}x")
        print("(en una máquina con varios cores físicos, debería acercarse a 4x)")


if __name__ == "__main__":
    main()
