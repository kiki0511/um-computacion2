#!/usr/bin/env python3
"""
Ejercicio adicional - Estimación de π con Monte Carlo (paralelo).

Se generan puntos aleatorios en el cuadrado [0,1]x[0,1] y se cuenta cuántos
caen dentro del círculo unitario (x²+y² <= 1). La proporción tiende a π/4,
así que π ≈ 4 * dentro / total. El trabajo se reparte con Pool.
"""
from multiprocessing import Pool, cpu_count
import random
import time

TOTAL_PUNTOS = 4_000_000


def contar_dentro(n):
    """Cuenta cuántos de n puntos aleatorios caen dentro del círculo."""
    dentro = 0
    for _ in range(n):
        x, y = random.random(), random.random()
        if x * x + y * y <= 1.0:
            dentro += 1
    return dentro


def main():
    workers = cpu_count()
    por_worker = TOTAL_PUNTOS // workers
    cargas = [por_worker] * workers

    inicio = time.time()
    with Pool(workers) as pool:
        parciales = pool.map(contar_dentro, cargas)
    duracion = time.time() - inicio

    dentro = sum(parciales)
    total = por_worker * workers
    pi = 4 * dentro / total

    print(f"Puntos: {total:,} | Workers: {workers}")
    print(f"π estimado: {pi:.6f}")
    print(f"π real:     3.141593")
    print(f"Error:      {abs(pi - 3.141592653589793):.6f}")
    print(f"Tiempo:     {duracion:.2f}s")


if __name__ == "__main__":
    main()
