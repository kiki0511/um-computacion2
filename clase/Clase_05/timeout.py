#!/usr/bin/env python3
"""
Ejercicio 4.1 - Timeout usando SIGALRM.

signal.alarm(n) programa que el kernel envíe SIGALRM dentro de n segundos.
El manejador lanza una excepción Timeout que interrumpe la función lenta.
Se implementa como decorador reutilizable.

Limitación: SIGALRM solo funciona en el hilo principal y en Unix.
"""
import signal


class Timeout(Exception):
    pass


def timeout_handler(sig, frame):
    raise Timeout("Operación excedió el tiempo límite")


def con_timeout(segundos):
    """Decorador que aborta la función si tarda más de `segundos`."""
    def decorador(func):
        def wrapper(*args, **kwargs):
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(segundos)
            try:
                return func(*args, **kwargs)
            finally:
                signal.alarm(0)  # cancelar la alarma
                signal.signal(signal.SIGALRM, old_handler)  # restaurar
        return wrapper
    return decorador


@con_timeout(3)
def operacion_lenta():
    import time
    print("Iniciando operación...")
    time.sleep(5)
    return "Completado"


@con_timeout(3)
def operacion_rapida():
    import time
    print("Iniciando operación...")
    time.sleep(1)
    return "Completado"


def main():
    print("=== Operación rápida ===")
    try:
        print(f"Resultado: {operacion_rapida()}")
    except Timeout as e:
        print(f"Timeout: {e}")

    print("\n=== Operación lenta ===")
    try:
        print(f"Resultado: {operacion_lenta()}")
    except Timeout as e:
        print(f"Timeout: {e}")


if __name__ == "__main__":
    main()
