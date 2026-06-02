#!/usr/bin/env python3
"""
Ejercicio 1 - Métodos de Pool.

Explora los métodos de Pool y cuándo conviene cada uno:
  map / map_async  -> todos los resultados, en orden de entrada
  imap             -> iterador lazy, mantiene el orden
  imap_unordered   -> iterador lazy, orden de finalización (suele ser + rápido)
  starmap          -> función con múltiples argumentos
  apply_async      -> control fino sobre una tarea individual (Future)

Reflexión:
  - imap_unordered puede ser más rápido porque entrega cada resultado apenas
    está listo, sin esperar a los anteriores (no respeta orden).
  - apply_async conviene para tareas sueltas/heterogéneas o cuando querés
    seguir trabajando mientras se calcula (devuelve un Future).
  - Si la duración fuera constante, imap e imap_unordered se verían casi
    iguales (todas terminan en orden parejo).
"""
from multiprocessing import Pool
import time
import random


def cuadrado(x):
    time.sleep(random.uniform(0.1, 1.0))  # duración variable
    return x ** 2


def suma(a, b):
    return a + b


def main():
    with Pool(4) as pool:
        print("== map ==")
        print(pool.map(cuadrado, range(8)))

        print("\n== map_async ==")
        async_result = pool.map_async(cuadrado, range(8))
        print(f"¿listo inmediatamente? {async_result.ready()}")
        print(f"resultados: {async_result.get()}")

        print("\n== imap (mantiene orden) ==")
        for r in pool.imap(cuadrado, range(8)):
            print(f"  llegó: {r}")

        print("\n== imap_unordered (orden de finalización) ==")
        for r in pool.imap_unordered(cuadrado, range(8)):
            print(f"  llegó: {r}")

        print("\n== starmap ==")
        print(pool.starmap(suma, [(1, 2), (3, 4), (5, 6)]))

        print("\n== apply_async ==")
        resultado = pool.apply_async(cuadrado, (10,))
        print(f"¿listo? {resultado.ready()}")
        print(f"resultado: {resultado.get()}")


if __name__ == "__main__":
    main()
