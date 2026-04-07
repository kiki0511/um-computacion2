#!/usr/bin/env python3
"""
Ejercicio 3.1 - Mini-grep: buscador de patrones en archivos o stdin.

Uso:
    python buscar.py "patron" archivo.txt
    python buscar.py "patron" *.txt -i -n
    python buscar.py "patron" *.log --count
    cat archivo.txt | python buscar.py "patron"
"""

import argparse
import sys
import re


def buscar_en_lineas(lineas, patron, ignorar_case, invertir, mostrar_numeros, nombre_archivo=None):
    """
    Itera sobre líneas y retorna las que coinciden (o no) con el patrón.
    Retorna lista de tuplas (num_linea, linea).
    """
    flags = re.IGNORECASE if ignorar_case else 0
    coincidencias = []

    for num, linea in enumerate(lineas, start=1):
        linea = linea.rstrip("\n")
        encontrado = bool(re.search(patron, linea, flags))

        if invertir:
            encontrado = not encontrado

        if encontrado:
            coincidencias.append((num, linea))

    return coincidencias


def formatear_resultado(num_linea, linea, nombre_archivo, multiples_archivos, mostrar_numeros):
    """Construye la línea de salida según las opciones activas."""
    partes = []

    if multiples_archivos and nombre_archivo:
        partes.append(nombre_archivo)

    if mostrar_numeros:
        partes.append(str(num_linea))

    if partes:
        return ":".join(partes) + ": " + linea
    return linea


def procesar_fuente(lineas, patron, args, nombre_archivo, multiples_archivos):
    """
    Procesa una fuente de líneas y muestra o cuenta los resultados.
    Retorna la cantidad de coincidencias.
    """
    try:
        coincidencias = buscar_en_lineas(
            lineas, patron,
            ignorar_case=args.ignore_case,
            invertir=args.invert,
            mostrar_numeros=args.line_number,
            nombre_archivo=nombre_archivo,
        )
    except re.error as e:
        print(f"Error: patrón de búsqueda inválido: {e}", file=sys.stderr)
        sys.exit(1)

    if args.count:
        # En modo --count no mostramos líneas, solo acumulamos
        return len(coincidencias)

    for num, linea in coincidencias:
        print(formatear_resultado(num, linea, nombre_archivo, multiples_archivos, args.line_number))

    return len(coincidencias)


def main():
    parser = argparse.ArgumentParser(
        description="Busca un patrón en archivos o stdin (mini versión de grep).",
        epilog="Si no se especifican archivos, lee de stdin.",
    )
    parser.add_argument(
        "patron",
        help="Patrón de búsqueda (soporta expresiones regulares)",
    )
    parser.add_argument(
        "archivos",
        nargs="*",
        metavar="archivo",
        help="Archivos donde buscar (opcional, default: stdin)",
    )
    parser.add_argument(
        "-i", "--ignore-case",
        action="store_true",
        help="Búsqueda insensible a mayúsculas/minúsculas",
    )
    parser.add_argument(
        "-n", "--line-number",
        action="store_true",
        help="Mostrar número de línea (activado automáticamente con múltiples archivos)",
    )
    parser.add_argument(
        "-c", "--count",
        action="store_true",
        help="Mostrar solo el conteo de coincidencias por archivo",
    )
    parser.add_argument(
        "-v", "--invert",
        action="store_true",
        help="Mostrar líneas que NO coinciden con el patrón",
    )

    args = parser.parse_args()

    # Con múltiples archivos, activar número de línea automáticamente
    multiples_archivos = len(args.archivos) > 1
    if multiples_archivos and not args.count:
        args.line_number = True

    total_coincidencias = 0

    if not args.archivos:
        # Leer desde stdin
        if sys.stdin.isatty():
            print("Error: no se especificaron archivos y no hay datos en stdin.", file=sys.stderr)
            parser.print_usage(sys.stderr)
            sys.exit(1)

        lineas = sys.stdin.readlines()
        total_coincidencias = procesar_fuente(lineas, args.patron, args, None, False)

        if args.count:
            print(f"Total: {total_coincidencias} coincidencias")
    else:
        resultados_por_archivo = {}

        for archivo in args.archivos:
            try:
                with open(archivo, "r", encoding="utf-8", errors="replace") as f:
                    lineas = f.readlines()
            except FileNotFoundError:
                print(f"Error: No se puede abrir '{archivo}'", file=sys.stderr)
                sys.exit(1)
            except PermissionError:
                print(f"Error: Sin permisos para leer '{archivo}'", file=sys.stderr)
                sys.exit(1)

            cantidad = procesar_fuente(lineas, args.patron, args, archivo, multiples_archivos)
            resultados_por_archivo[archivo] = cantidad
            total_coincidencias += cantidad

        if args.count:
            for archivo, cantidad in resultados_por_archivo.items():
                print(f"{archivo}: {cantidad} coincidencias")
            if multiples_archivos:
                print(f"Total: {total_coincidencias} coincidencias")

    return 0 if total_coincidencias > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
