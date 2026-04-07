#!/usr/bin/env python3
"""
Ejercicio 2.2 - Buscador de archivos grandes.

Busca archivos que superen un tamaño mínimo dentro de un directorio,
de forma recursiva. Útil para encontrar qué ocupa espacio en disco.

Uso:
    python find_large.py /var/log --min-size 1M
    python find_large.py . --min-size 100K --type f
    python find_large.py /home --min-size 50M --top 10
"""

import argparse
import os
import sys
import re
from pathlib import Path


# ─── Parseo de tamaños ────────────────────────────────────────────────────────

UNIDADES = {"K": 1024, "M": 1024**2, "G": 1024**3, "B": 1}

def parsear_tamanio(valor_str):
    """
    Convierte un string de tamaño a bytes.
    Acepta: 1K, 100K, 1M, 2.5G, 500 (bytes por defecto)
    """
    valor_str = valor_str.strip().upper()
    match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([KMGB]?)", valor_str)
    if not match:
        raise argparse.ArgumentTypeError(
            f"Tamaño inválido: '{valor_str}'. Usá formato como 100K, 1M, 2G."
        )
    numero = float(match.group(1))
    sufijo = match.group(2) or "B"
    return int(numero * UNIDADES[sufijo])


def tamanio_legible(bytes_):
    """Convierte bytes a formato legible."""
    for unidad in ("bytes", "KB", "MB", "GB", "TB"):
        if bytes_ < 1024 or unidad == "TB":
            if unidad == "bytes":
                return f"{bytes_} bytes"
            return f"{bytes_:.1f} {unidad}"
        bytes_ /= 1024


# ─── Búsqueda ─────────────────────────────────────────────────────────────────

def buscar_archivos(directorio, min_bytes, tipo):
    """
    Recorre el directorio recursivamente y devuelve lista de (path, tamaño)
    que cumplen los filtros.
    """
    resultados = []

    try:
        for entrada in Path(directorio).rglob("*"):
            try:
                # Filtrar por tipo
                if tipo == "f" and not entrada.is_file():
                    continue
                if tipo == "d" and not entrada.is_dir():
                    continue

                # Evitar seguir symlinks para el tamaño
                info = entrada.lstat()
                tamanio = info.st_size

                if tamanio >= min_bytes:
                    resultados.append((entrada, tamanio))

            except (PermissionError, OSError):
                # Ignorar archivos/dirs sin permisos
                continue

    except FileNotFoundError:
        print(f"Error: El directorio '{directorio}' no existe.", file=sys.stderr)
        sys.exit(1)
    except PermissionError:
        print(f"Error: Sin permisos para acceder a '{directorio}'.", file=sys.stderr)
        sys.exit(1)

    return resultados


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Busca archivos que superen un tamaño mínimo en un directorio.",
        epilog="Ejemplos de tamaño: 500K, 10M, 1G",
    )
    parser.add_argument(
        "directorio",
        help="Directorio donde buscar",
    )
    parser.add_argument(
        "--min-size",
        type=parsear_tamanio,
        default=parsear_tamanio("1M"),
        metavar="TAMAÑO",
        help="Tamaño mínimo (ej: 100K, 1M, 2G). Default: 1M",
    )
    parser.add_argument(
        "--type",
        choices=["f", "d"],
        default=None,
        help="Tipo de entrada: f=archivo, d=directorio (default: ambos)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=None,
        metavar="N",
        help="Mostrar solo los N más grandes",
    )

    args = parser.parse_args()

    resultados = buscar_archivos(args.directorio, args.min_size, args.type)

    if not resultados:
        print(f"No se encontraron archivos de más de {tamanio_legible(args.min_size)}.")
        return 0

    # Ordenar por tamaño descendente
    resultados.sort(key=lambda x: x[1], reverse=True)

    if args.top:
        print(f"Los {args.top} archivos más grandes (mínimo {tamanio_legible(args.min_size)}):")
        resultados = resultados[:args.top]
        for i, (path, tam) in enumerate(resultados, 1):
            print(f"  {i:2}. {path} ({tamanio_legible(tam)})")
    else:
        for path, tam in resultados:
            print(f"{path} ({tamanio_legible(tam)})")

    total_bytes = sum(t for _, t in resultados)
    print(f"\nTotal: {len(resultados)} archivo(s), {tamanio_legible(total_bytes)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
