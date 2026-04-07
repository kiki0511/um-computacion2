#!/usr/bin/env python3
"""
Ejercicio 2.3 - Generador de chunks (lotes).

Divide cualquier iterable en grupos de tamaño fijo.
El último grupo puede ser más pequeño si no hay suficientes elementos.
Es lazy: no carga todo en memoria.
"""

from typing import Iterable, TypeVar, Generator, List

T = TypeVar("T")


def chunked(iterable: Iterable[T], size: int) -> Generator[List[T], None, None]:
    """
    Divide un iterable en chunks de tamaño `size`.

    Args:
        iterable: cualquier objeto iterable (lista, generador, archivo, etc.)
        size: tamaño de cada chunk

    Yields:
        Listas con hasta `size` elementos. El último puede ser más pequeño.

    Raises:
        ValueError: si size es menor o igual a 0.

    Ejemplo:
        >>> list(chunked(range(7), 3))
        [[0, 1, 2], [3, 4, 5], [6]]
    """
    if size <= 0:
        raise ValueError(f"El tamaño del chunk debe ser > 0, recibido: {size}")

    chunk = []
    for elemento in iterable:
        chunk.append(elemento)
        if len(chunk) == size:
            yield chunk
            chunk = []

    # Entregar el último chunk si quedó algo
    if chunk:
        yield chunk


if __name__ == "__main__":
    print("=== Lista de números ===")
    print(list(chunked(range(10), 3)))

    print("\n=== String (iterable de caracteres) ===")
    print(list(chunked("abcdefgh", 3)))

    print("\n=== Iterable exactamente divisible ===")
    print(list(chunked(range(9), 3)))

    print("\n=== Chunk más grande que el iterable ===")
    print(list(chunked(range(3), 10)))

    print("\n=== Iterable vacío ===")
    print(list(chunked([], 5)))

    print("\n=== Uso con archivo (simulado) ===")
    import io
    contenido = "\n".join(f"línea {i}" for i in range(1, 8))
    archivo_simulado = io.StringIO(contenido)

    for batch in chunked(archivo_simulado, 3):
        print(f"  Batch de {len(batch)} líneas: {[l.strip() for l in batch]}")
