#!/usr/bin/env python3
"""
Ejercicio adicional - Procesador de archivos en paralelo.

Dada una carpeta, procesa todos sus archivos en paralelo con Pool: para cada
archivo calcula líneas, palabras, bytes y el hash SHA-256. Es el patrón típico
"un archivo por tarea".

Uso:
    python3 procesador_archivos.py [carpeta]
    (si no se pasa carpeta, genera archivos de ejemplo en /tmp y los procesa)
"""
from multiprocessing import Pool, cpu_count
import hashlib
import os
import sys


def procesar_archivo(ruta):
    lineas = palabras = 0
    h = hashlib.sha256()
    bytes_totales = 0
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(65536), b""):
            h.update(bloque)
            bytes_totales += len(bloque)
            lineas += bloque.count(b"\n")
            palabras += len(bloque.split())
    return {
        "archivo": os.path.basename(ruta),
        "lineas": lineas,
        "palabras": palabras,
        "bytes": bytes_totales,
        "sha256": h.hexdigest()[:16],  # recortado para mostrar
    }


def generar_ejemplos():
    carpeta = "/tmp/archivos_demo"
    os.makedirs(carpeta, exist_ok=True)
    for i in range(6):
        with open(os.path.join(carpeta, f"archivo_{i}.txt"), "w") as f:
            for j in range((i + 1) * 100):
                f.write(f"linea {j} del archivo {i} con varias palabras\n")
    return carpeta


def main():
    if len(sys.argv) == 2:
        carpeta = sys.argv[1]
    else:
        print("(sin carpeta) generando archivos de ejemplo...")
        carpeta = generar_ejemplos()

    if not os.path.isdir(carpeta):
        print(f"Error: {carpeta} no es una carpeta", file=sys.stderr)
        sys.exit(1)

    rutas = [os.path.join(carpeta, n) for n in sorted(os.listdir(carpeta))
             if os.path.isfile(os.path.join(carpeta, n))]
    if not rutas:
        print("No hay archivos para procesar")
        return

    with Pool(cpu_count()) as pool:
        resultados = pool.map(procesar_archivo, rutas)

    print(f"\nProcesados {len(resultados)} archivos de {carpeta}:")
    print(f"{'archivo':20s} {'líneas':>8s} {'palabras':>9s} "
          f"{'bytes':>9s}  sha256")
    for r in resultados:
        print(f"{r['archivo']:20s} {r['lineas']:8d} {r['palabras']:9d} "
              f"{r['bytes']:9d}  {r['sha256']}...")


if __name__ == "__main__":
    main()
