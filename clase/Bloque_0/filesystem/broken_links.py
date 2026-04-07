#!/usr/bin/env python3
"""
Ejercicio 2.3 - Detector de enlaces simbólicos rotos.

Busca symlinks cuyo destino no existe. Opcionalmente los elimina.

Uso:
    python broken_links.py /home/user
    python broken_links.py /home/user --delete
    python broken_links.py /etc --quiet
"""

import argparse
import os
import sys
from pathlib import Path


def buscar_enlaces_rotos(directorio):
    """
    Recorre el directorio recursivamente y devuelve lista de symlinks rotos.
    Un symlink está roto si is_link() es True pero exists() es False
    (el destino no existe).
    """
    rotos = []

    try:
        for entrada in Path(directorio).rglob("*"):
            try:
                # is_symlink() usa lstat, no sigue el enlace
                # exists() sigue el enlace — si devuelve False, está roto
                if entrada.is_symlink() and not entrada.exists():
                    try:
                        destino = os.readlink(entrada)
                    except OSError:
                        destino = "(ilegible)"
                    rotos.append((entrada, destino))
            except (PermissionError, OSError):
                continue

    except FileNotFoundError:
        print(f"Error: El directorio '{directorio}' no existe.", file=sys.stderr)
        sys.exit(1)
    except PermissionError:
        print(f"Error: Sin permisos para acceder a '{directorio}'.", file=sys.stderr)
        sys.exit(1)

    return rotos


def main():
    parser = argparse.ArgumentParser(
        description="Detecta (y opcionalmente elimina) enlaces simbólicos rotos.",
    )
    parser.add_argument(
        "directorio",
        help="Directorio donde buscar",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Ofrecer eliminar cada enlace roto (pide confirmación)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Solo mostrar el conteo total",
    )

    args = parser.parse_args()

    if not args.quiet:
        print(f"Buscando enlaces simbólicos rotos en {args.directorio}...\n")

    rotos = buscar_enlaces_rotos(args.directorio)

    if args.quiet:
        print(len(rotos))
        return 0

    if not rotos:
        print("No se encontraron enlaces rotos.")
        return 0

    print("Enlaces rotos encontrados:")
    for enlace, destino in rotos:
        print(f"  {enlace} -> {destino} (no existe)")

    print(f"\nTotal: {len(rotos)} enlace(s) roto(s)")

    if args.delete:
        print()
        eliminados = 0
        for enlace, destino in rotos:
            try:
                respuesta = input(f"¿Eliminar '{enlace}'? [s/N] ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\nOperación cancelada.")
                break

            if respuesta == "s":
                try:
                    enlace.unlink()
                    print(f"  Eliminado: {enlace}")
                    eliminados += 1
                except PermissionError:
                    print(f"  Error: sin permisos para eliminar '{enlace}'")
                except OSError as e:
                    print(f"  Error al eliminar '{enlace}': {e}")

        print(f"\n{eliminados} enlace(s) eliminado(s).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
