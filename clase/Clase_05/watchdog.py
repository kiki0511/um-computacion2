#!/usr/bin/env python3
"""
Ejercicio adicional - Watchdog.

Monitorea un proceso hijo y lo reinicia si termina inesperadamente (código
distinto de 0). Si el hijo sale con código 0 (trabajo completado), no se
reinicia. SIGINT/SIGTERM detienen el watchdog y al hijo.

Uso:
    python3 watchdog.py
"""
import os
import signal
import time
import random

ejecutando = True


def detener(sig, frame):
    global ejecutando
    print("\n[WATCHDOG] Deteniendo...")
    ejecutando = False


def proceso_vigilado():
    """Hijo que trabaja un rato y a veces falla."""
    print(f"[VIGILADO {os.getpid()}] Iniciado")
    for i in range(random.randint(3, 8)):
        print(f"[VIGILADO {os.getpid()}] trabajando ({i})")
        time.sleep(1)
    if random.random() < 0.5:
        print(f"[VIGILADO {os.getpid()}] ¡Caída inesperada!")
        os._exit(1)
    print(f"[VIGILADO {os.getpid()}] terminó OK")
    os._exit(0)


def main():
    signal.signal(signal.SIGINT, detener)
    signal.signal(signal.SIGTERM, detener)

    reinicios = 0
    while ejecutando:
        pid = os.fork()
        if pid == 0:
            proceso_vigilado()  # no retorna (os._exit)

        # Padre: esperar a que termine
        _, status = os.waitpid(pid, 0)
        if not ejecutando:
            break

        codigo = os.WEXITSTATUS(status) if os.WIFEXITED(status) else -1
        if codigo == 0:
            print("[WATCHDOG] El proceso terminó correctamente. No reinicio.")
            break
        else:
            reinicios += 1
            print(f"[WATCHDOG] El proceso murió (código {codigo}). "
                  f"Reiniciando (#{reinicios})...")
            time.sleep(1)

    print(f"[WATCHDOG] Fin. Reinicios totales: {reinicios}")


if __name__ == "__main__":
    main()
