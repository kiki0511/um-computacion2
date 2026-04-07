#!/usr/bin/env python3
"""
Ejercicio 3.2 - Analizador de uso de disco.

Muestra cuánto espacio ocupa cada archivo/carpeta dentro de un directorio,
similar al comando 'du' pero con más opciones de presentación.

Uso:
    python diskusage.py /home/user --depth 1
    python diskusage.py . --top 5
    python diskusage.py . --depth 2 --exclude "node_modules,*.log"
"""

import argparse
import fnmatch
import sys
from pathlib import Path


# ─── Utilidades ──────────────────────────────────────────────────────────────

def tamanio_legible(bytes_):
    """Convierte bytes a formato legible con unidad apropiada."""
    for unidad in ("B", "KB", "MB", "GB", "TB"):
        if bytes_ < 1024 or unidad == "TB":
            if unidad == "B":
                return f"{bytes_} B"
            return f"{bytes_:.1f} {unidad}"
        bytes_ /= 1024


def esta_excluido(nombre, patrones):
    """Devuelve True si el nombre coincide con algún patrón de exclusión."""
    return any(fnmatch.fnmatch(nombre, p) for p in patrones)


# ─── Cálculo de tamaños ───────────────────────────────────────────────────────

def tamanio_total(path, patrones_excluir):
    """
    Calcula recursivamente el tamaño total de un directorio en bytes.
    No sigue symlinks para evitar ciclos.
    """
    total = 0
    try:
        if path.is_symlink():
            return path.lstat().st_size
        if path.is_file():
            return path.stat().st_size
        if path.is_dir():
            for hijo in path.iterdir():
                if esta_excluido(hijo.name, patrones_excluir):
                    continue
                total += tamanio_total(hijo, patrones_excluir)
    except (PermissionError, OSError):
        pass
    return total


def recolectar_entradas(directorio, depth, patrones_excluir, nivel=0):
    """
    Recorre el directorio hasta la profundidad indicada y devuelve
    lista de (path, tamaño_total).
    """
    resultados = []
    base = Path(directorio)

    try:
        entradas = sorted(base.iterdir(), key=lambda p: p.name.lower())
    except (PermissionError, OSError):
        return resultados

    for entrada in entradas:
        if esta_excluido(entrada.name, patrones_excluir):
            continue

        tam = tamanio_total(entrada, patrones_excluir)
        resultados.append((entrada, tam))

        # Entrar en subdirectorios si no alcanzamos la profundidad límite
        if entrada.is_dir() and not entrada.is_symlink():
            if depth is None or nivel + 1 < depth:
                resultados.extend(
                    recolectar_entradas(entrada, depth, patrones_excluir, nivel + 1)
                )

    return resultados


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Analiza el uso de disco de un directorio.",
        epilog="Similar a 'du' pero con salida más amigable.",
    )
    parser.add_argument(
        "directorio",
        help="Directorio a analizar",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=1,
        metavar="N",
        help="Profundidad de análisis (default: 1 = solo primer nivel)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=None,
        metavar="N",
        help="Mostrar solo los N elementos más grandes",
    )
    parser.add_argument(
        "--exclude",
        type=str,
        default="",
        metavar="PATRONES",
        help="Patrones a excluir separados por coma (ej: node_modules,*.log)",
    )

    args = parser.parse_args()

    base = Path(args.directorio)
    if not base.exists():
        print(f"Error: '{args.directorio}' no existe.", file=sys.stderr)
        sys.exit(1)
    if not base.is_dir():
        print(f"Error: '{args.directorio}' no es un directorio.", file=sys.stderr)
        sys.exit(1)

    patrones = [p.strip() for p in args.exclude.split(",") if p.strip()]

    if args.top:
        # Modo --top: recolectar todo y mostrar los N más grandes
        print(f"Calculando uso de disco en '{args.directorio}'...\n")
        entradas = recolectar_entradas(args.directorio, depth=None, patrones_excluir=patrones)
        entradas.sort(key=lambda x: x[1], reverse=True)
        top = entradas[:args.top]

        print(f"Los {args.top} elementos más grandes:")
        for i, (path, tam) in enumerate(top, 1):
            print(f"  {i:2}. {path} ({tamanio_legible(tam)})")
    else:
        # Modo normal: mostrar por profundidad
        entradas = recolectar_entradas(args.directorio, depth=args.depth, patrones_excluir=patrones)
        entradas.sort(key=lambda x: x[1], reverse=True)

        ancho = max((len(tamanio_legible(t)) for _, t in entradas), default=6)

        for path, tam in entradas:
            tam_str = tamanio_legible(tam).rjust(ancho)
            print(f"{tam_str}    {path}")

        # Total del directorio raíz
        total = tamanio_total(base, patrones)
        linea = "─" * 40
        print(linea)
        total_str = tamanio_legible(total).rjust(ancho)
        print(f"{total_str}    {base} (total)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
