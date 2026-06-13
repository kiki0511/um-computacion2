#!/usr/bin/env python3
"""
Ejercicio 6 - Hilos daemon.

Un hilo "daemon" es un hilo en segundo plano que NO impide que el programa
termine: cuando el hilo principal (main) termina, todos los hilos daemon
mueren automáticamente, sin esperar a que terminen su trabajo.

Este script corre la versión CON daemon=True (termina solo, ideal para que
el ejercicio se pueda correr sin intervención). Más abajo está comentada la
versión SIN daemon para que la pruebes manualmente.
"""
import threading
import time


def loop_infinito(label):
    while True:
        print(f"[{label}] trabajando...")
        time.sleep(1)


def main():
    print("=== Versión con daemon=True ===")
    h = threading.Thread(target=loop_infinito, args=("daemon",), daemon=True)
    h.start()

    time.sleep(3)
    print("[Main] terminó: el hilo daemon muere automáticamente con el proceso")

    # --- Versión SIN daemon (descomentar para probar) ---
    #
    # Si lanzás el mismo hilo sin daemon=True, Python espera a que TODOS los
    # hilos no-daemon terminen antes de salir del proceso. Como
    # `loop_infinito` nunca termina, el programa queda colgado para siempre
    # y hay que matarlo con Ctrl+C.
    #
    # print("\n=== Versión sin daemon ===")
    # h2 = threading.Thread(target=loop_infinito, args=("no-daemon",))
    # h2.start()
    # time.sleep(3)
    # print("[Main] 'terminó', pero el proceso sigue vivo por el hilo no-daemon")
    # h2.join()  # nunca retorna -> hay que Ctrl+C


if __name__ == "__main__":
    main()
