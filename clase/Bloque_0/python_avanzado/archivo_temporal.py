#!/usr/bin/env python3
"""
Ejercicio 1.1 - Context manager para archivos temporales.

Crea un archivo temporal que se borra automáticamente al salir del bloque
with, incluso si ocurre una excepción adentro.
"""

import os
from contextlib import contextmanager


@contextmanager
def archivo_temporal(nombre: str):
    """
    Context manager que crea un archivo temporal y lo borra al salir.

    Args:
        nombre: nombre del archivo a crear

    Yields:
        El objeto archivo abierto en modo lectura/escritura.

    El archivo se borra siempre al salir del bloque with,
    incluso si ocurrió una excepción.
    """
    f = open(nombre, "w+", encoding="utf-8")
    try:
        yield f
    finally:
        f.close()
        if os.path.exists(nombre):
            os.remove(nombre)


if __name__ == "__main__":
    print("=== Uso básico ===")
    with archivo_temporal("test.txt") as f:
        f.write("Datos de prueba\n")
        f.write("Más datos\n")
        f.seek(0)
        print(f.read())

    assert not os.path.exists("test.txt"), "El archivo debería haberse borrado"
    print("✓ El archivo fue borrado correctamente\n")

    print("=== Borra incluso con excepción ===")
    try:
        with archivo_temporal("error.txt") as f:
            f.write("algo\n")
            raise ValueError("Error simulado")
    except ValueError:
        pass

    assert not os.path.exists("error.txt"), "Debería haberse borrado igual"
    print("✓ El archivo fue borrado a pesar de la excepción")
