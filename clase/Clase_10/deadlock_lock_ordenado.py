#!/usr/bin/env python3
"""
Ejercicio 6 - Deadlock: detección y solución.

Un deadlock clásico ocurre cuando dos hilos toman dos locks en orden
INVERSO:

    Thread 1: lock_a -> (espera) -> lock_b
    Thread 2: lock_b -> (espera) -> lock_a

Si Thread 1 toma `lock_a` y Thread 2 toma `lock_b` casi al mismo tiempo,
Thread 1 queda esperando `lock_b` (que tiene Thread 2) y Thread 2 queda
esperando `lock_a` (que tiene Thread 1). Ninguno suelta lo que tiene:
deadlock, ambos quedan colgados para siempre.

`demostrar_deadlock()` reproduce esto. Para no colgar el script entero, se
usa `join(timeout=2)`: si después de 2s los hilos siguen vivos
(`is_alive()`), se reporta el deadlock y la función retorna (los hilos
colgados quedan como threads "huérfanos" daemon=False, pero como el
ejercicio solo corre una vez y el programa sigue, no es un problema para
esta demo).

`version_corregida()` aplica la solución estándar: TODOS los hilos toman
los locks en el MISMO orden (siempre `lock_a` antes que `lock_b`). Así nunca
puede darse el ciclo de espera circular, y termina sin problemas.
"""
import threading
import time


def demostrar_deadlock():
    lock_a = threading.Lock()
    lock_b = threading.Lock()

    def thread_1():
        with lock_a:
            print("Thread 1: tengo A")
            time.sleep(0.2)
            print("Thread 1: pidiendo B...")
            with lock_b:
                print("Thread 1: tengo A y B")

    def thread_2():
        with lock_b:
            print("Thread 2: tengo B")
            time.sleep(0.2)
            print("Thread 2: pidiendo A...")
            with lock_a:
                print("Thread 2: tengo B y A")

    t1 = threading.Thread(target=thread_1, daemon=True)
    t2 = threading.Thread(target=thread_2, daemon=True)

    t1.start()
    t2.start()

    t1.join(timeout=2)
    t2.join(timeout=2)

    if t1.is_alive() or t2.is_alive():
        print("\n¡DEADLOCK DETECTADO! (los hilos quedaron esperando para siempre)")
        return False
    print("\nTerminó sin deadlock (no debería pasar con este código...)")
    return True


def version_corregida():
    lock_a = threading.Lock()
    lock_b = threading.Lock()

    def thread_ordenado(nombre):
        with lock_a:  # Siempre A primero
            print(f"{nombre}: tengo A")
            time.sleep(0.05)
            with lock_b:  # Luego B
                print(f"{nombre}: tengo A y B")
                time.sleep(0.05)

    t1 = threading.Thread(target=thread_ordenado, args=("Thread 1",))
    t2 = threading.Thread(target=thread_ordenado, args=("Thread 2",))

    t1.start()
    t2.start()
    t1.join(timeout=2)
    t2.join(timeout=2)

    if t1.is_alive() or t2.is_alive():
        print("¡Deadlock! (no debería pasar con orden consistente)")
        return False
    print("¡Completado sin deadlock!")
    return True


def main():
    print("=== Versión con deadlock (locks en orden inverso) ===")
    demostrar_deadlock()

    print("\n=== Versión corregida (mismo orden en todos los hilos) ===")
    version_corregida()

    print("\nConclusión: la regla de oro es 'siempre adquirir múltiples locks")
    print("en el mismo orden en TODOS los hilos'. Otra opción, cuando se")
    print("puede, es usar un único lock que proteja ambos recursos.")


if __name__ == "__main__":
    main()
