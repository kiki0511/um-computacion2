#!/usr/bin/env python3
"""
Ejercicio 2.2 - Decorador de reintentos (OBLIGATORIO).

Reintenta una función que falla hasta un número máximo de veces,
esperando entre intentos. Muy útil para operaciones de red o APIs.
"""

import functools
import time
import random
from typing import Tuple, Type


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    """
    Decorador que reintenta la función si lanza una excepción.

    Args:
        max_attempts: número máximo de intentos (default: 3)
        delay: segundos a esperar entre intentos (default: 1)
        exceptions: tupla de tipos de excepción a capturar (default: Exception)
                    Solo reintenta si la excepción es de estos tipos.

    Raises:
        La última excepción capturada si todos los intentos fallan.

    Ejemplo:
        @retry(max_attempts=3, delay=0.5, exceptions=(ConnectionError,))
        def conectar():
            ...
    """
    def decorador(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            ultimo_error = None

            for intento in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    ultimo_error = e
                    if intento < max_attempts:
                        print(
                            f"Intento {intento}/{max_attempts} falló: {e}. "
                            f"Esperando {delay}s..."
                        )
                        time.sleep(delay)
                    else:
                        print(f"Intento {intento}/{max_attempts} falló: {e}.")

            raise ultimo_error

        return wrapper
    return decorador


if __name__ == "__main__":
    print("=== Caso que falla siempre ===")

    @retry(max_attempts=3, delay=0.1)
    def siempre_falla():
        raise ConnectionError("Servidor no disponible")

    try:
        siempre_falla()
    except ConnectionError as e:
        print(f"Excepción final capturada: {e}\n")

    print("=== Caso que falla a veces ===")
    intentos = {"n": 0}

    @retry(max_attempts=5, delay=0.05)
    def falla_las_primeras_dos():
        intentos["n"] += 1
        if intentos["n"] < 3:
            raise ConnectionError("Fallo temporal")
        return f"Éxito en el intento {intentos['n']}"

    resultado = falla_las_primeras_dos()
    print(f"Resultado: {resultado}\n")

    print("=== Solo captura excepciones especificadas ===")

    @retry(max_attempts=3, delay=0.05, exceptions=(ConnectionError,))
    def lanza_valor_error():
        raise ValueError("Este error NO debería reintentarse")

    try:
        lanza_valor_error()
    except ValueError as e:
        print(f"ValueError no reintentado, capturado inmediatamente: {e}")
