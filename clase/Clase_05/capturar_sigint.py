#!/usr/bin/env python3
"""
Ejercicio 2.1 - Capturar SIGINT (Ctrl+C).

Por defecto Ctrl+C envía SIGINT y Python lo traduce a KeyboardInterrupt,
terminando el programa. Acá registramos un manejador propio con
signal.signal() que intercepta la señal: el programa solo termina luego
de 3 pulsaciones.
"""
import signal
import time

contador_ctrl_c = 0


def manejador_sigint(sig, frame):
    global contador_ctrl_c
    contador_ctrl_c += 1
    print(f"\n¡Ctrl+C detectado! (vez #{contador_ctrl_c})")

    if contador_ctrl_c >= 3:
        print("OK, OK, me voy...")
        raise SystemExit(0)
    else:
        print(f"Presioná {3 - contador_ctrl_c} veces más para salir")


def main():
    signal.signal(signal.SIGINT, manejador_sigint)

    print("Presioná Ctrl+C (3 veces para salir)")
    print("Observá cómo el programa no termina la primera vez")

    while True:
        print(".", end="", flush=True)
        time.sleep(0.5)


if __name__ == "__main__":
    main()
