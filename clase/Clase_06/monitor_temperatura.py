#!/usr/bin/env python3
"""
Ejercicio adicional - Monitor de temperatura.

N procesos "sensores" escriben temperaturas (simuladas) en un Array
compartido de doubles. Un proceso "monitor" lee periódicamente y muestra
promedio, máximo y mínimo. Demuestra varios escritores + un lector sobre
memoria compartida.
"""
from multiprocessing import Process, Array, Value
import random
import time

NUM_SENSORES = 4
LECTURAS = 10


def sensor(temperaturas, idx, corriendo):
    """Cada sensor actualiza su posición del array con una temperatura."""
    base = 20 + idx * 2
    while corriendo.value:
        temperaturas[idx] = base + random.uniform(-3, 3)
        time.sleep(0.2)


def monitor(temperaturas, corriendo):
    for _ in range(LECTURAS):
        valores = [temperaturas[i] for i in range(NUM_SENSORES)]
        prom = sum(valores) / len(valores)
        print(f"[MONITOR] temps={[f'{v:.1f}' for v in valores]} "
              f"| prom={prom:.1f} max={max(valores):.1f} min={min(valores):.1f}")
        time.sleep(0.3)
    corriendo.value = 0  # avisar a los sensores que paren


def main():
    temperaturas = Array("d", [0.0] * NUM_SENSORES)
    corriendo = Value("i", 1)

    sensores = [
        Process(target=sensor, args=(temperaturas, i, corriendo))
        for i in range(NUM_SENSORES)
    ]
    mon = Process(target=monitor, args=(temperaturas, corriendo))

    for s in sensores:
        s.start()
    mon.start()

    mon.join()
    for s in sensores:
        s.join()

    print("Monitor finalizado.")


if __name__ == "__main__":
    main()
