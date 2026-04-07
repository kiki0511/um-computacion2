#!/usr/bin/env python3
"""
Ejercicio 3.1 - Comparador de directorios.

Compara dos directorios y muestra qué archivos fueron agregados, eliminados
o modificados. Similar a 'diff -r' pero con salida más clara.

Uso:
    python diffdir.py proyecto_v1 proyecto_v2
    python diffdir.py dir1 dir2 --recursive
    python diffdir.py dir1 dir2 --checksum
"""

import argparse
import hashlib
import os
import sys
from datetime import datetime
from pathlib import Path


# ─── Utilidades ──────────────────────────────────────────────────────────────

def formatear_fecha(timestamp):
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")


def calcular_hash(ruta, chunk=65536):
    """Calcula el hash SHA256 de un archivo en chunks (eficiente para archivos grandes)."""
    h = hashlib.sha256()
    try:
        with open(ruta, "rb") as f:
            while True:
                bloque = f.read(chunk)
                if not bloque:
                    break
                h.update(bloque)
        return h.hexdigest()
    except (PermissionError, OSError):
        return None


def listar_archivos(directorio, recursivo):
    """
    Devuelve un dict {ruta_relativa: Path} con todos los archivos del directorio.
    """
    base = Path(directorio)
    archivos = {}

    try:
        patron = "**/*" if recursivo else "*"
        for entrada in base.glob(patron):
            if entrada.is_file():
                clave = str(entrada.relative_to(base))
                archivos[clave] = entrada
    except PermissionError as e:
        print(f"Error de permisos al leer '{directorio}': {e}", file=sys.stderr)

    return archivos


# ─── Comparación ─────────────────────────────────────────────────────────────

def comparar_directorios(dir1, dir2, recursivo, usar_checksum):
    archivos1 = listar_archivos(dir1, recursivo)
    archivos2 = listar_archivos(dir2, recursivo)

    claves1 = set(archivos1.keys())
    claves2 = set(archivos2.keys())

    solo_en_1 = sorted(claves1 - claves2)
    solo_en_2 = sorted(claves2 - claves1)
    en_ambos  = sorted(claves1 & claves2)

    modificados_tam   = []
    modificados_fecha = []
    modificados_hash  = []
    identicos         = []

    for nombre in en_ambos:
        p1 = archivos1[nombre]
        p2 = archivos2[nombre]

        try:
            s1 = p1.stat()
            s2 = p2.stat()
        except OSError:
            continue

        diferente_tam   = s1.st_size  != s2.st_size
        diferente_fecha = abs(s1.st_mtime - s2.st_mtime) > 1  # tolerancia 1 seg

        if diferente_tam:
            modificados_tam.append((nombre, s1.st_size, s2.st_size))
        elif diferente_fecha:
            modificados_fecha.append((nombre, s1.st_mtime, s2.st_mtime))
        elif usar_checksum:
            h1 = calcular_hash(p1)
            h2 = calcular_hash(p2)
            if h1 and h2 and h1 != h2:
                modificados_hash.append(nombre)
            else:
                identicos.append(nombre)
        else:
            identicos.append(nombre)

    return {
        "solo_en_1":        solo_en_1,
        "solo_en_2":        solo_en_2,
        "mod_tamanio":      modificados_tam,
        "mod_fecha":        modificados_fecha,
        "mod_hash":         modificados_hash,
        "identicos":        identicos,
    }


# ─── Presentación ─────────────────────────────────────────────────────────────

def mostrar_resultado(resultado, dir1, dir2):
    hay_diferencias = any([
        resultado["solo_en_1"],
        resultado["solo_en_2"],
        resultado["mod_tamanio"],
        resultado["mod_fecha"],
        resultado["mod_hash"],
    ])

    if resultado["solo_en_1"]:
        print(f"\nSolo en {dir1}:")
        for f in resultado["solo_en_1"]:
            print(f"  {f}")

    if resultado["solo_en_2"]:
        print(f"\nSolo en {dir2}:")
        for f in resultado["solo_en_2"]:
            print(f"  {f}")

    if resultado["mod_tamanio"]:
        print("\nModificados (tamaño diferente):")
        for nombre, t1, t2 in resultado["mod_tamanio"]:
            print(f"  {nombre} ({t1} -> {t2} bytes)")

    if resultado["mod_fecha"]:
        print("\nModificados (fecha diferente):")
        for nombre, f1, f2 in resultado["mod_fecha"]:
            print(f"  {nombre} ({formatear_fecha(f1)} -> {formatear_fecha(f2)})")

    if resultado["mod_hash"]:
        print("\nModificados (contenido diferente, mismo tamaño y fecha):")
        for nombre in resultado["mod_hash"]:
            print(f"  {nombre}")

    n_id = len(resultado["identicos"])
    if n_id:
        print(f"\nIdénticos: {n_id} archivo{'s' if n_id != 1 else ''}")

    if not hay_diferencias:
        print("\nLos directorios son idénticos.")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Compara dos directorios y muestra qué cambió entre ellos.",
    )
    parser.add_argument("dir1", help="Primer directorio")
    parser.add_argument("dir2", help="Segundo directorio")
    parser.add_argument(
        "--recursive", "-r",
        action="store_true",
        help="Incluir subdirectorios en la comparación",
    )
    parser.add_argument(
        "--checksum",
        action="store_true",
        help="Comparar contenido con hash SHA256 (más lento pero exacto)",
    )

    args = parser.parse_args()

    for d in [args.dir1, args.dir2]:
        if not Path(d).exists():
            print(f"Error: '{d}' no existe.", file=sys.stderr)
            sys.exit(1)
        if not Path(d).is_dir():
            print(f"Error: '{d}' no es un directorio.", file=sys.stderr)
            sys.exit(1)

    print(f"Comparando '{args.dir1}' con '{args.dir2}'...")
    if args.checksum:
        print("(Modo checksum activado — esto puede tardar para archivos grandes)")

    resultado = comparar_directorios(args.dir1, args.dir2, args.recursive, args.checksum)
    mostrar_resultado(resultado, args.dir1, args.dir2)

    return 0


if __name__ == "__main__":
    sys.exit(main())
