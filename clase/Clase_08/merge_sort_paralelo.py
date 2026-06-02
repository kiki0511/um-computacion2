#!/usr/bin/env python3
"""
Ejercicio adicional - Merge sort paralelo.

Divide la lista en N partes, ordena cada parte en un proceso (Pool) y luego
hace el merge final secuencial. Compara contra el sort secuencial.

¿A partir de qué tamaño conviene paralelizar? Solo con listas grandes: para
listas chicas, el costo de crear procesos y serializar los datos (pickle al
enviarlos a los workers) supera la ganancia. Acá se ve que el sort nativo de
Python (Timsort, en C) es dificilísimo de superar; el ejercicio es didáctico.
"""
from multiprocessing import Pool, cpu_count
import random
import time


def merge(a, b):
    """Combina dos listas ordenadas en una sola ordenada."""
    resultado = []
    i = j = 0
    while i < len(a) and j < len(b):
        if a[i] <= b[j]:
            resultado.append(a[i]); i += 1
        else:
            resultado.append(b[j]); j += 1
    resultado.extend(a[i:])
    resultado.extend(b[j:])
    return resultado


def merge_sort_paralelo(datos, workers):
    # partir en `workers` trozos
    n = len(datos)
    tam = n // workers
    trozos = [datos[i * tam: (i + 1) * tam] for i in range(workers - 1)]
    trozos.append(datos[(workers - 1) * tam:])  # el último lleva el resto

    # ordenar cada trozo en paralelo
    with Pool(workers) as pool:
        ordenados = pool.map(sorted, trozos)

    # merge final (secuencial)
    resultado = ordenados[0]
    for parte in ordenados[1:]:
        resultado = merge(resultado, parte)
    return resultado


def main():
    N = 2_000_000
    datos = [random.randint(0, 10_000_000) for _ in range(N)]
    workers = cpu_count()

    # secuencial
    inicio = time.time()
    esperado = sorted(datos)
    t_seq = time.time() - inicio

    # paralelo
    inicio = time.time()
    resultado = merge_sort_paralelo(datos, workers)
    t_par = time.time() - inicio

    print(f"N={N:,}  workers={workers}")
    print(f"sorted() secuencial: {t_seq:.2f}s")
    print(f"merge_sort paralelo: {t_par:.2f}s")
    print(f"¿Resultado correcto? {resultado == esperado}")
    print("\nNota: el sorted() nativo (C) es muy difícil de superar; "
          "el merge paralelo es principalmente didáctico.")


if __name__ == "__main__":
    main()
