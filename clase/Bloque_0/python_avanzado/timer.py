#!/usr/bin/env python3
"""
Ejercicio 2.1 - Timer con context manager (OBLIGATORIO).

Mide el tiempo de ejecución de un bloque de código.
Implementado de dos formas: como clase y con @contextmanager.
"""

import time
from contextlib import contextmanager
from typing import Optional


# ─── Implementación como clase ────────────────────────────────────────────────

class Timer:
    """
    Context manager que mide el tiempo de ejecución de un bloque with.

    Uso:
        with Timer("Mi operación"):
            ...
        # [Timer] Mi operación: 0.123s

        with Timer() as t:
            ...
        print(t.elapsed)

    Atributos:
        elapsed: tiempo transcurrido en segundos (actualizado en tiempo real)
    """

    def __init__(self, nombre: Optional[str] = None):
        """
        Args:
            nombre: etiqueta para identificar el timer. Si se da, imprime
                    el resultado al salir del bloque.
        """
        self.nombre = nombre
        self._inicio: Optional[float] = None

    @property
    def elapsed(self) -> float:
        """Tiempo transcurrido desde que empezó el timer, en segundos."""
        if self._inicio is None:
            return 0.0
        return time.perf_counter() - self._inicio

    def __enter__(self) -> "Timer":
        self._inicio = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        # Calculamos el tiempo final
        duracion = self.elapsed

        if self.nombre:
            print(f"[Timer] {self.nombre}: {duracion:.3f}s")

        # Retornar False: no suprimimos excepciones
        return False


# ─── Implementación con @contextmanager ──────────────────────────────────────

@contextmanager
def timer_func(nombre: Optional[str] = None):
    """
    Versión funcional del Timer usando @contextmanager.

    Uso:
        with timer_func("operación") as t:
            ...
    """
    inicio = time.perf_counter()

    class Estado:
        """Objeto simple para exponer elapsed durante el bloque."""
        @property
        def elapsed(self):
            return time.perf_counter() - inicio

    estado = Estado()
    try:
        yield estado
    finally:
        duracion = time.perf_counter() - inicio
        if nombre:
            print(f"[Timer] {nombre}: {duracion:.3f}s")


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Timer con nombre (imprime automáticamente) ===")
    with Timer("Comprensión de lista"):
        datos = [x**2 for x in range(1_000_000)]

    print("\n=== Timer sin nombre (acceso manual a elapsed) ===")
    with Timer() as t:
        time.sleep(0.3)
    print(f"El bloque tardó {t.elapsed:.3f} segundos")

    print("\n=== Elapsed durante el bloque ===")
    with Timer("Dos pasos") as t:
        time.sleep(0.1)
        print(f"  Después del paso 1: {t.elapsed:.3f}s")
        time.sleep(0.2)
        print(f"  Después del paso 2: {t.elapsed:.3f}s")

    print("\n=== Versión funcional con @contextmanager ===")
    with timer_func("Versión funcional") as t:
        time.sleep(0.1)
        print(f"  elapsed durante bloque: {t.elapsed:.3f}s")

    print("\n=== Timer sobrevive a excepciones ===")
    try:
        with Timer("Con error"):
            time.sleep(0.1)
            raise ValueError("Error de prueba")
    except ValueError:
        print("  (excepción capturada afuera)")
