#!/usr/bin/env python3
"""
Ejercicio 5 (OBLIGATORIO) - Value y Array compartidos.

multiprocessing.Value y multiprocessing.Array crean objetos en memoria
compartida entre procesos. A diferencia de las variables normales (que NO se
comparten tras un fork), estos sí permiten que varios procesos lean y
escriban el mismo dato.

Tres partes:
  5.1  Value compartido -> demostrar RACE CONDITION (incrementos perdidos)
  5.2  Array compartido -> dividir un cálculo entre procesos y verificar
  Tarea Array('d') con sin() + acumulador Value('d') (ver race condition)

La race condition de 5.1 ocurre porque `contador.value += 1` no es atómico:
es leer, sumar, escribir. Si dos procesos lo hacen a la vez, uno pisa al otro.
"""
from multiprocessing import Process, Value, Array
import math


# ----------------------------------------------------------------------
# 5.1 - Value y race condition
# ----------------------------------------------------------------------
def incrementar(contador, n, nombre):
    print(f"[{nombre}] Iniciando {n} incrementos...")
    for _ in range(n):
        contador.value += 1   # NO atómico -> race condition
    print(f"[{nombre}] Terminado")


def demo_race_condition():
    print("=== 5.1: Value compartido (race condition) ===")
    contador = Value("i", 0)
    N = 100_000
    procesos = []
    for i in range(4):
        p = Process(target=incrementar, args=(contador, N, f"P{i}"))
        p.start()
        procesos.append(p)
    for p in procesos:
        p.join()

    esperado = 4 * N
    print(f"\nEsperado: {esperado}")
    print(f"Obtenido: {contador.value}")
    print(f"Diferencia: {esperado - contador.value} (incrementos perdidos)")


# ----------------------------------------------------------------------
# 5.2 - Array compartido para cálculo paralelo
# ----------------------------------------------------------------------
def calcular_cuadrados(resultado, inicio, fin):
    for i in range(inicio, fin):
        resultado[i] = i * i


def demo_array_paralelo():
    print("\n=== 5.2: Array compartido (cálculo paralelo) ===")
    TAMANO = 1000
    resultado = Array("i", TAMANO)
    NUM_PROCESOS = 4
    chunk = TAMANO // NUM_PROCESOS

    procesos = []
    for i in range(NUM_PROCESOS):
        ini = i * chunk
        fin = (i + 1) * chunk if i < NUM_PROCESOS - 1 else TAMANO
        p = Process(target=calcular_cuadrados, args=(resultado, ini, fin))
        p.start()
        procesos.append(p)
    for p in procesos:
        p.join()

    print(f"resultado[10]  = {resultado[10]}   (esperado 100)")
    print(f"resultado[99]  = {resultado[99]}   (esperado 9801)")
    print(f"resultado[999] = {resultado[999]} (esperado 998001)")
    errores = sum(1 for i in range(TAMANO) if resultado[i] != i * i)
    print(f"Errores: {errores}")


# ----------------------------------------------------------------------
# Tarea - Array('d') con sin() + acumulador Value('d')
# ----------------------------------------------------------------------
def calcular_sin(resultado, acumulador, inicio, fin):
    suma_local = 0.0
    for i in range(inicio, fin):
        v = math.sin(i * 0.01)
        resultado[i] = v
        suma_local += v
    # acumular en el Value compartido (NO atómico -> posible race condition)
    acumulador.value += suma_local


def demo_tarea_sin():
    print("\n=== Tarea: Array('d') con sin() + acumulador Value('d') ===")
    TAMANO = 100
    resultado = Array("d", TAMANO)
    acumulador = Value("d", 0.0)
    NUM_PROCESOS = 4
    chunk = TAMANO // NUM_PROCESOS

    procesos = []
    for i in range(NUM_PROCESOS):
        ini = i * chunk
        fin = (i + 1) * chunk if i < NUM_PROCESOS - 1 else TAMANO
        p = Process(target=calcular_sin,
                    args=(resultado, acumulador, ini, fin))
        p.start()
        procesos.append(p)
    for p in procesos:
        p.join()

    print("Primeros 20 resultados:")
    for i in range(20):
        print(f"  sin({i * 0.01:.2f}) = {resultado[i]:.5f}")

    suma_secuencial = sum(math.sin(i * 0.01) for i in range(TAMANO))
    print(f"\nSuma acumulada (Value):   {acumulador.value:.6f}")
    print(f"Suma secuencial (control): {suma_secuencial:.6f}")
    print("Si difieren, hubo race condition en el acumulador "
          "(solo 4 sumas, suele coincidir, pero no está garantizado).")


def main():
    demo_race_condition()
    demo_array_paralelo()
    demo_tarea_sin()


if __name__ == "__main__":
    main()
