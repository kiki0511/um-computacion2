#!/usr/bin/env python3
"""
Ejercicio 5 (OBLIGATORIO) - Procesador de imágenes paralelo.

Aplica un filtro blur 3x3 (CPU-intensive) a varias "imágenes" (matrices de
enteros) usando Pool.map, y compara el tiempo secuencial vs paralelo.

Verificación:
  - Crea múltiples imágenes (matrices) aleatorias
  - Aplica el filtro a cada imagen
  - Usa Pool.map para el procesamiento paralelo
  - Muestra tiempo secuencial vs paralelo
  - Calcula speedup
  - Usa el guard if __name__ == "__main__"
"""
from multiprocessing import Pool
import time
import random


def crear_imagen(size):
    return [[random.randint(0, 255) for _ in range(size)]
            for _ in range(size)]


def aplicar_filtro(imagen, pasadas=8):
    """Filtro blur 3x3 aplicado varias veces (CPU-intensive)."""
    size = len(imagen)
    for _ in range(pasadas):
        resultado = [[0] * size for _ in range(size)]
        for i in range(1, size - 1):
            for j in range(1, size - 1):
                suma = 0
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        suma += imagen[i + di][j + dj]
                resultado[i][j] = suma // 9
        imagen = resultado
    return imagen


def procesar_imagen(args):
    idx, imagen = args
    inicio = time.time()
    resultado = aplicar_filtro(imagen)
    duracion = time.time() - inicio
    checksum = sum(sum(fila) for fila in resultado)
    return idx, duracion, checksum


def main():
    NUM_IMAGENES = 8
    SIZE = 100

    print(f"Creando {NUM_IMAGENES} imágenes de {SIZE}x{SIZE}...")
    imagenes = [(i, crear_imagen(SIZE)) for i in range(NUM_IMAGENES)]

    # Secuencial
    print("\nProcesamiento secuencial:")
    inicio = time.time()
    for img in imagenes:
        procesar_imagen(img)
    t_seq = time.time() - inicio
    print(f"Tiempo: {t_seq:.2f}s")

    # Paralelo
    print("\nProcesamiento paralelo (4 workers):")
    inicio = time.time()
    with Pool(4) as pool:
        resultados = pool.map(procesar_imagen, imagenes)
    t_par = time.time() - inicio

    for idx, duracion, checksum in resultados:
        print(f"  Imagen {idx}: {duracion:.3f}s (checksum={checksum})")

    print(f"Tiempo total: {t_par:.2f}s")
    print(f"Speedup: {t_seq / t_par:.2f}x")


if __name__ == "__main__":
    main()
