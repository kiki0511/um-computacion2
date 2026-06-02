#!/usr/bin/env python3
"""
Ejercicio adicional - Señales como comandos.

Interpreta ráfagas de SIGUSR1 como comandos distintos según cuántas llegan
seguidas dentro de una ventana corta:
    1 x SIGUSR1 -> acción A (saludar)
    2 x SIGUSR1 -> acción B (mostrar hora)
    3 x SIGUSR1 -> acción C (shutdown)

Como SIGUSR1 no se encola (varias seguidas se "funden"), contamos los
disparos del handler y, tras un breve período sin nuevas señales (medido con
SIGALRM), decidimos qué comando ejecutar.

Uso:
    python3 senales_como_comandos.py     # terminal 1
    kill -USR1 <pid>                     # 1 vez = acción A
    kill -USR1 <pid>; kill -USR1 <pid>   # 2 rápidas = acción B
"""
import signal
import time
import os

VENTANA = 0.8  # segundos para agrupar ráfagas
pulsos = 0
ejecutando = True


def on_usr1(sig, frame):
    global pulsos
    pulsos += 1
    # (re)programar la evaluación de la ráfaga
    signal.setitimer(signal.ITIMER_REAL, VENTANA)


def on_alarm(sig, frame):
    global pulsos, ejecutando
    n = pulsos
    pulsos = 0
    if n == 1:
        print("[ACCIÓN A] ¡Hola!")
    elif n == 2:
        print(f"[ACCIÓN B] Hora actual: {time.ctime()}")
    elif n >= 3:
        print("[ACCIÓN C] Shutdown solicitado por 3 señales")
        ejecutando = False


def on_term(sig, frame):
    global ejecutando
    ejecutando = False


def main():
    signal.signal(signal.SIGUSR1, on_usr1)
    signal.signal(signal.SIGALRM, on_alarm)
    signal.signal(signal.SIGTERM, on_term)

    pid = os.getpid()
    print(f"PID {pid}. Enviá ráfagas de SIGUSR1:")
    print(f"  1x  kill -USR1 {pid}   -> acción A")
    print(f"  2x  kill -USR1 {pid}   -> acción B")
    print(f"  3x  kill -USR1 {pid}   -> acción C (shutdown)")

    while ejecutando:
        signal.pause()

    print("Terminado.")


if __name__ == "__main__":
    main()
