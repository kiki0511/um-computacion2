#!/usr/bin/env python3
"""
Ejercicio 1.2 - Decorador de logging.

Registra cada llamada a una función: argumentos, valor de retorno y timestamp.
"""

import functools
from datetime import datetime


def log_llamada(func):
    """
    Decorador que imprime información sobre cada llamada a la función:
    - Timestamp
    - Nombre de la función
    - Argumentos posicionales y keyword
    - Valor de retorno

    Preserva el nombre y docstring original con @wraps.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Formatear argumentos
        args_str = ", ".join(repr(a) for a in args)
        kwargs_str = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
        todos_args = ", ".join(filter(None, [args_str, kwargs_str]))

        print(f"[{timestamp}] Llamando a {func.__name__}({todos_args})")

        resultado = func(*args, **kwargs)

        print(f"[{timestamp}] {func.__name__} retornó {resultado!r}")
        return resultado

    return wrapper


if __name__ == "__main__":
    @log_llamada
    def sumar(a, b):
        """Suma dos números."""
        return a + b

    @log_llamada
    def saludar(nombre, entusiasta=False):
        """Genera un saludo."""
        sufijo = "!" if entusiasta else "."
        return f"Hola, {nombre}{sufijo}"

    print("=== sumar ===")
    resultado = sumar(3, 5)

    print("\n=== saludar con kwargs ===")
    saludar("Ana", entusiasta=True)

    print("\n=== Verificar que @wraps preserva el nombre ===")
    print(f"Nombre: {sumar.__name__}")
    print(f"Docstring: {sumar.__doc__}")
