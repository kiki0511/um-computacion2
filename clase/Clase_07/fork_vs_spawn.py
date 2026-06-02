#!/usr/bin/env python3
"""
Ejercicio 5 - fork vs spawn.

Compara el costo de crear 100 procesos con cada método de arranque:

  - fork  : el hijo es una copia del padre (rápido; solo Unix). Hereda todo
            el estado de memoria por copy-on-write.
  - spawn : arranca un intérprete nuevo y re-importa el módulo (más lento,
            pero portable y más limpio; es el default en macOS y Windows).

Se usa multiprocessing.get_context(metodo) para no fijar el método global,
de modo que se puedan medir ambos en la misma corrida.

Nota: 'fork' no está disponible en Windows; el script lo omite si falta.
"""
import multiprocessing
import time


def tarea_trivial():
    # trabajo mínimo: lo que se mide es el costo de CREAR el proceso
    pass


def medir(metodo, n=100):
    ctx = multiprocessing.get_context(metodo)
    inicio = time.time()
    procesos = []
    for _ in range(n):
        p = ctx.Process(target=tarea_trivial)
        p.start()
        procesos.append(p)
    for p in procesos:
        p.join()
    return time.time() - inicio


def main():
    n = 100
    disponibles = multiprocessing.get_all_start_methods()
    print(f"Métodos disponibles en esta plataforma: {disponibles}")
    print(f"Creando y esperando {n} procesos con cada método...\n")

    for metodo in ("fork", "spawn"):
        if metodo not in disponibles:
            print(f"{metodo:6}: no disponible en esta plataforma")
            continue
        t = medir(metodo, n)
        print(f"{metodo:6}: {t:.3f}s  ({t / n * 1000:.2f} ms por proceso)")

    print("\nObservación: fork suele ser bastante más rápido que spawn, "
          "porque spawn reinicia el intérprete y re-importa el módulo.")


if __name__ == "__main__":
    main()
