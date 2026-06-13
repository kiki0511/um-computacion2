#!/usr/bin/env python3
"""
Ejercicio 1 - Primer hilo.

Lanza 3 hilos en paralelo. Cada uno imprime su nombre y un número del 1 al 5,
con una pausa de 0.2s entre cada número. El main espera a todos con join()
antes de imprimir "Listo".
"""
import threading
import time


def imprimir_numeros(nombre):
    for i in range(1, 6):
        print(f"[{nombre}] número: {i}")
        time.sleep(0.2)


def main():
    hilos = [
        threading.Thread(target=imprimir_numeros, args=(f"Hilo-{i}",))
        for i in range(1, 4)
    ]

    for h in hilos:
        h.start()

    for h in hilos:
        h.join()

    print("Listo")


if __name__ == "__main__":
    main()
