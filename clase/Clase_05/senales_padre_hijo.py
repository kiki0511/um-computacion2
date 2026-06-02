#!/usr/bin/env python3
"""
Ejercicio 3.1 - Comunicación padre->hijo con señales.

El hijo registra manejadores para SIGUSR1 y SIGUSR2 y espera con
signal.pause() (se bloquea hasta que llega cualquier señal). El padre usa
os.kill(pid, señal) para "comandar" al hijo:
  - SIGUSR1 -> incrementar un contador
  - SIGUSR2 -> mostrar el valor actual
  - SIGTERM -> terminar
"""
import os
import signal
import time


def main():
    pid = os.fork()

    if pid == 0:
        # === HIJO ===
        contador = 0

        def incrementar(sig, frame):
            nonlocal_holder["c"] += 1
            print(f"[HIJO] Contador incrementado: {nonlocal_holder['c']}")

        def mostrar(sig, frame):
            print(f"[HIJO] Valor actual: {nonlocal_holder['c']}")

        # truco: usar un dict mutable para el estado del handler
        nonlocal_holder = {"c": contador}

        signal.signal(signal.SIGUSR1, incrementar)
        signal.signal(signal.SIGUSR2, mostrar)

        print(f"[HIJO] PID={os.getpid()}, esperando señales...")
        while True:
            signal.pause()  # dormir hasta recibir una señal

    else:
        # === PADRE ===
        time.sleep(0.5)  # dar tiempo a que el hijo registre los handlers

        print("[PADRE] Enviando SIGUSR1 (incrementar) x3")
        for _ in range(3):
            os.kill(pid, signal.SIGUSR1)
            time.sleep(0.3)

        print("[PADRE] Enviando SIGUSR2 (mostrar)")
        os.kill(pid, signal.SIGUSR2)
        time.sleep(0.3)

        print("[PADRE] Enviando SIGUSR1 x2")
        for _ in range(2):
            os.kill(pid, signal.SIGUSR1)
            time.sleep(0.3)

        print("[PADRE] Enviando SIGUSR2 (mostrar)")
        os.kill(pid, signal.SIGUSR2)
        time.sleep(0.3)

        print("[PADRE] Terminando hijo")
        os.kill(pid, signal.SIGTERM)
        os.wait()


if __name__ == "__main__":
    main()
