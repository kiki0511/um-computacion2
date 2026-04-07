#!/usr/bin/env python3
"""Ejercicio 2.2 - Listador de archivos mejorado (inspirado en ls)."""

import argparse
import os
import sys
from pathlib import Path


def listar_directorio(directorio, mostrar_ocultos, extension):
    try:
        entradas = sorted(Path(directorio).iterdir(), key=lambda p: p.name.lower())
    except FileNotFoundError:
        print(f"Error: El directorio '{directorio}' no existe.")
        sys.exit(1)
    except PermissionError:
        print(f"Error: Sin permisos para leer '{directorio}'.")
        sys.exit(1)

    for entrada in entradas:
        nombre = entrada.name

        # Filtrar archivos ocultos si no se pidió --all
        if not mostrar_ocultos and nombre.startswith("."):
            continue

        # Filtrar por extensión si se especificó
        if extension and entrada.suffix != extension:
            continue

        # Agregar "/" al final si es directorio
        if entrada.is_dir():
            print(f"{nombre}/")
        else:
            print(nombre)


def main():
    parser = argparse.ArgumentParser(
        description="Lista archivos de un directorio con filtros opcionales."
    )
    parser.add_argument(
        "directorio",
        nargs="?",
        default=".",
        help="Directorio a listar (por defecto: directorio actual)",
    )
    parser.add_argument(
        "-a", "--all",
        action="store_true",
        dest="mostrar_ocultos",
        help="Incluir archivos ocultos (los que empiezan con punto)",
    )
    parser.add_argument(
        "--extension",
        metavar="EXT",
        help="Filtrar archivos por extensión (ej: .py, .txt)",
    )

    args = parser.parse_args()
    listar_directorio(args.directorio, args.mostrar_ocultos, args.extension)
    return 0


if __name__ == "__main__":
    exit(main())
