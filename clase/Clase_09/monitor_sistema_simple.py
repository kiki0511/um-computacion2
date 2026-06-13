#!/usr/bin/env python3
"""
Adicional - Monitor de sistema simple.

3 threads daemon imprimen métricas simuladas (CPU, memoria, disco) cada
cierto intervalo, cada uno a su propio ritmo. El programa principal duerme
10 segundos y termina; al ser daemons, los 3 hilos mueren con él sin que
haga falta señalizarles nada (mismo concepto que `hilos_daemon.py`, aplicado
a algo más realista).
"""
import random
import threading
import time

DURACION_TOTAL = 10  # segundos que vive el programa


def metric_cpu():
    while True:
        print(f"[CPU]    uso: {random.uniform(5, 95):5.1f}%")
        time.sleep(1)


def metric_memoria():
    while True:
        print(f"[MEM]    uso: {random.uniform(20, 80):5.1f}%")
        time.sleep(2)


def metric_disco():
    while True:
        print(f"[DISCO]  I/O: {random.uniform(0, 50):5.1f} MB/s")
        time.sleep(3)


def main():
    hilos = [
        threading.Thread(target=metric_cpu, daemon=True),
        threading.Thread(target=metric_memoria, daemon=True),
        threading.Thread(target=metric_disco, daemon=True),
    ]
    for h in hilos:
        h.start()

    print(f"Monitor corriendo por {DURACION_TOTAL}s...\n")
    time.sleep(DURACION_TOTAL)
    print("\nMain terminó: los 3 hilos daemon mueren con el proceso")


if __name__ == "__main__":
    main()
