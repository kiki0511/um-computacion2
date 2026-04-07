#!/usr/bin/env python3
"""
Ejercicio 2.4 - Pipeline de funciones.

Compone múltiples funciones en secuencia: la salida de cada una
es la entrada de la siguiente.
"""

import functools
from typing import Callable, Any


def pipeline(*funciones: Callable) -> Callable:
    """
    Compone múltiples funciones en un pipeline izquierda a derecha.

    pipeline(f, g, h)(x) es equivalente a h(g(f(x)))

    Args:
        *funciones: funciones a componer en orden de aplicación

    Returns:
        Una función que aplica todas en secuencia.

    Raises:
        ValueError: si no se pasa ninguna función.

    Ejemplo:
        p = pipeline(doble, sumar_uno, cuadrado)
        p(3)  # ((3*2)+1)**2 = 49
    """
    if not funciones:
        raise ValueError("pipeline necesita al menos una función")

    def ejecutar(valor: Any) -> Any:
        return functools.reduce(lambda v, f: f(v), funciones, valor)

    return ejecutar


if __name__ == "__main__":
    def doble(x):     return x * 2
    def sumar_uno(x): return x + 1
    def cuadrado(x):  return x ** 2

    print("=== Pipeline básico ===")
    p = pipeline(doble, sumar_uno, cuadrado)
    print(f"p(3) = {p(3)}")    # ((3*2)+1)^2 = 49
    print(f"p(5) = {p(5)}")    # ((5*2)+1)^2 = 121

    print("\n=== Pipeline de una función ===")
    p2 = pipeline(doble)
    print(f"p2(10) = {p2(10)}")  # 20

    print("\n=== Pipeline con funciones de string ===")
    p3 = pipeline(str, len, doble)
    print(f"p3(12345) = {p3(12345)}")  # len("12345")=5, *2=10

    print("\n=== Procesamiento de texto ===")
    limpiar = pipeline(str.strip, str.lower, str.split)
    print(limpiar("  HELLO WORLD  "))  # ['hello', 'world']

    print("\n=== Cadena larga ===")
    procesar_numero = pipeline(
        lambda x: x * 3,
        lambda x: x - 1,
        str,
        lambda s: f"Resultado: {s}",
    )
    print(procesar_numero(7))  # Resultado: 20
