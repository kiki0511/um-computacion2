#!/usr/bin/env python3
"""
Ejercicio 3.1 - Memoización manual sin lru_cache.

Implementa un decorador @memoize que cachea resultados de funciones
según sus argumentos, con estadísticas de uso y limpieza de cache.
"""

import functools
from typing import Any, Dict, Tuple


def memoize(func):
    """
    Decorador que cachea los resultados de una función por argumentos.

    La función decorada gana tres atributos extra:
        .cache       → dict con los resultados cacheados
        .cache_info() → namedtuple con hits, misses, size
        .clear_cache() → limpia el cache y resetea estadísticas

    Solo funciona con argumentos hasheables (no listas ni dicts).

    Ejemplo:
        @memoize
        def fibonacci(n):
            if n < 2: return n
            return fibonacci(n-1) + fibonacci(n-2)
    """
    cache: Dict[Tuple, Any] = {}
    hits = 0
    misses = 0

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        nonlocal hits, misses

        # La clave del cache incluye args y kwargs (ordenados para consistencia)
        clave = args + tuple(sorted(kwargs.items()))

        if clave in cache:
            hits += 1
            return cache[clave]

        misses += 1
        resultado = func(*args, **kwargs)
        cache[clave] = resultado
        return resultado

    def cache_info():
        """Devuelve estadísticas del cache."""
        class CacheInfo:
            def __init__(self, h, m, s):
                self.hits = h
                self.misses = m
                self.size = s
            def __repr__(self):
                return (f"CacheInfo(hits={self.hits}, "
                        f"misses={self.misses}, size={self.size})")

        return CacheInfo(hits, misses, len(cache))

    def clear_cache():
        """Limpia el cache y resetea los contadores."""
        nonlocal hits, misses
        cache.clear()
        hits = 0
        misses = 0

    wrapper.cache = cache
    wrapper.cache_info = cache_info
    wrapper.clear_cache = clear_cache

    return wrapper


if __name__ == "__main__":
    print("=== Fibonacci con memoize ===")

    @memoize
    def fibonacci(n):
        """Fibonacci recursivo (sin memoize sería exponencial)."""
        if n < 2:
            return n
        return fibonacci(n - 1) + fibonacci(n - 2)

    print(f"fibonacci(10) = {fibonacci(10)}")
    print(f"fibonacci(30) = {fibonacci(30)}")
    print(f"fibonacci(50) = {fibonacci(50)}")

    print(f"\nEstadísticas: {fibonacci.cache_info()}")
    print(f"Tamaño del cache: {len(fibonacci.cache)} entradas")

    print("\n=== Limpiar cache ===")
    fibonacci.clear_cache()
    print(f"Después de limpiar: {fibonacci.cache_info()}")
    fibonacci(10)
    print(f"Después de recalcular fibonacci(10): {fibonacci.cache_info()}")

    print("\n=== Con kwargs ===")

    @memoize
    def potencia(base, exponente=2):
        print(f"  (calculando {base}^{exponente})")
        return base ** exponente

    potencia(3, exponente=4)
    potencia(3, exponente=4)  # Debería usar el cache
    potencia(3)               # Base=3, exp=2 — diferente clave
    print(potencia.cache_info())
