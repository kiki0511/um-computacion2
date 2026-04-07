#!/usr/bin/env python3
"""
Ejercicio 1.3 - Generador de Fibonacci.

Implementa la secuencia de Fibonacci como generador infinito (o con límite).
Un generador produce valores uno a la vez con yield, sin cargar todo en memoria.
"""

from typing import Optional


def fibonacci(limite: Optional[int] = None):
    """
    Generador de la secuencia de Fibonacci.

    Args:
        limite: si se especifica, solo genera números <= limite.
                Si es None, genera infinitamente.

    Yields:
        Números de Fibonacci en orden: 0, 1, 1, 2, 3, 5, 8, 13, ...

    Ejemplo:
        >>> list(fibonacci(limite=10))
        [0, 1, 1, 2, 3, 5, 8]
    """
    a, b = 0, 1
    while True:
        if limite is not None and a > limite:
            return
        yield a
        a, b = b, a + b


if __name__ == "__main__":
    print("=== Primeros 10 términos (generador infinito) ===")
    fib = fibonacci()
    for _ in range(10):
        print(next(fib), end=" ")
    print()

    print("\n=== Podemos seguir desde donde quedamos ===")
    print(next(fib))  # 55
    print(next(fib))  # 89

    print("\n=== Con límite de 100 ===")
    print(list(fibonacci(limite=100)))

    print("\n=== Ventaja del generador vs lista ===")
    # Esto funciona en memoria constante, sin importar cuántos elementos pedimos
    fib2 = fibonacci()
    n = 1000
    for _ in range(n - 1):
        next(fib2)
    print(f"El término {n} de Fibonacci: {next(fib2)}")
