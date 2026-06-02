#!/usr/bin/env python3
"""
Ejercicio adicional - Monitor de pipe.

Se interpone en un pipeline: deja pasar los datos de stdin a stdout sin
modificarlos, y al final reporta estadísticas (bytes y líneas) por stderr
(para no contaminar el flujo de datos que viaja por stdout).

Uso:
    cat archivo_grande | python3 monitor.py | wc -l
    cat archivo_grande | python3 monitor.py > copia.txt
"""
import sys


def main():
    total_bytes = 0
    total_lineas = 0

    # trabajar en binario para contar bytes de forma exacta
    entrada = sys.stdin.buffer
    salida = sys.stdout.buffer

    for linea in entrada:
        total_bytes += len(linea)
        total_lineas += 1
        salida.write(linea)
    salida.flush()

    print(f"[monitor] Procesados {total_bytes} bytes, {total_lineas} líneas",
          file=sys.stderr)


if __name__ == "__main__":
    main()
