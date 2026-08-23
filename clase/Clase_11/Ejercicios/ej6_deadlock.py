#!/usr/bin/env python3
"""
Ejercicio 6: Demostración de deadlock y su prevención.

Versión A: dos threads adquieren locks en orden opuesto → deadlock potencial.
Versión B: orden consistente (siempre lock_a antes que lock_b) → sin deadlock.
"""
import threading
import time


def demostrar_deadlock():
    """
    Thread 1 toma A luego pide B.
    Thread 2 toma B luego pide A.
    Si ambos toman su primero antes que el otro libere el suyo: deadlock.
    """
    lock_a = threading.Lock()
    lock_b = threading.Lock()

    def thread_1():
        with lock_a:
            print("Thread 1: tiene A, esperando B...")
            time.sleep(0.1)
            with lock_b:
                print("Thread 1: tiene A y B")

    def thread_2():
        with lock_b:
            print("Thread 2: tiene B, esperando A...")
            time.sleep(0.1)
            with lock_a:
                print("Thread 2: tiene B y A")

    t1 = threading.Thread(target=thread_1)
    t2 = threading.Thread(target=thread_2)

    t1.start()
    t2.start()

    t1.join(timeout=2)
    t2.join(timeout=2)

    if t1.is_alive() or t2.is_alive():
        print("¡DEADLOCK DETECTADO! Los threads quedaron bloqueados.")
        return False
    print("Completado sin deadlock (tuviste suerte con el timing).")
    return True


def version_corregida():
    """
    Ambos threads adquieren los locks siempre en el mismo orden (A → B).
    La espera circular es imposible: nunca habrá deadlock.
    """
    lock_a = threading.Lock()
    lock_b = threading.Lock()

    def thread_ordenado(nombre):
        with lock_a:           # Siempre A primero
            print(f"{nombre}: tiene A")
            with lock_b:       # Luego B
                print(f"{nombre}: tiene A y B")
                time.sleep(0.1)

    t1 = threading.Thread(target=thread_ordenado, args=("Thread 1",))
    t2 = threading.Thread(target=thread_ordenado, args=("Thread 2",))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    print("¡Completado sin deadlock!")


if __name__ == "__main__":
    print("=== Versión con deadlock potencial ===")
    demostrar_deadlock()

    print("\n=== Versión corregida (jerarquía de locks) ===")
    version_corregida()
