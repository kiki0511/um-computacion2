#!/usr/bin/env python3
"""
Ejercicio 3 - Memoria compartida con Value y Array.

Varios procesos incrementan un Value compartido usando get_lock() para evitar
la race condition (a diferencia de la Clase 6, acá SÍ sincronizamos). Otro
grupo llena segmentos disjuntos de un Array.

Preguntas:
  - ¿Si quitás `with contador.get_lock():`? Vuelve la race condition: el
    contador final será menor a 40000 (incrementos perdidos).
  - ¿Hace falta lock para el Array? No, porque cada worker escribe en un
    rango DISJUNTO (no hay dos procesos tocando la misma posición).
"""
from multiprocessing import Process, Value, Array


def incrementar(contador, n_veces, wid):
    for _ in range(n_veces):
        with contador.get_lock():   # sección crítica protegida
            contador.value += 1
    print(f"Worker {wid} terminó sus {n_veces} incrementos")


def llenar_array(arr, valor_inicial, wid):
    seg = len(arr) // 4
    inicio = wid * seg
    fin = inicio + seg
    for i in range(inicio, fin):
        arr[i] = valor_inicial + i


def main():
    # Value con lock
    contador = Value("i", 0)
    procs = [Process(target=incrementar, args=(contador, 10000, i))
             for i in range(4)]
    for p in procs:
        p.start()
    for p in procs:
        p.join()

    print(f"\nContador final: {contador.value}")
    assert contador.value == 40000, "¡Race condition! Falta el lock"

    # Array particionado (sin lock: segmentos disjuntos)
    arr = Array("i", 100)
    procs = [Process(target=llenar_array, args=(arr, 1000, i))
             for i in range(4)]
    for p in procs:
        p.start()
    for p in procs:
        p.join()

    print(f"Array (primeros 10): {list(arr)[:10]}")
    print(f"Array (últimos 10):  {list(arr)[-10:]}")


if __name__ == "__main__":
    main()
