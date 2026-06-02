#!/usr/bin/env python3
"""
Ejercicio adicional 6.3 - Mini pstree.

Versión simplificada de pstree: arma el árbol de procesos a partir de la
relación PID -> PPid (que se lee de /proc/<PID>/status) y lo imprime con
indentación.

Uso:
    python3 mi_pstree.py          # desde PID 1
    python3 mi_pstree.py <PID>    # desde un PID dado como raíz
"""
import os
import sys


def leer_procesos():
    """Devuelve dos dicts: nombre[pid] y lista de hijos[ppid]."""
    nombre = {}
    hijos = {}

    for entrada in os.listdir("/proc"):
        if not entrada.isdigit():
            continue
        pid = int(entrada)
        try:
            with open(f"/proc/{pid}/status") as f:
                campos = {}
                for linea in f:
                    clave, _, valor = linea.partition(":")
                    if clave in ("Name", "PPid"):
                        campos[clave] = valor.strip()
                    if "Name" in campos and "PPid" in campos:
                        break
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue

        nombre[pid] = campos.get("Name", "?")
        ppid = int(campos.get("PPid", 0))
        hijos.setdefault(ppid, []).append(pid)

    return nombre, hijos


def imprimir_arbol(pid, nombre, hijos, nivel=0):
    etiqueta = nombre.get(pid, "?")
    print(f"{'  ' * nivel}{etiqueta}({pid})")
    for hijo in sorted(hijos.get(pid, [])):
        imprimir_arbol(hijo, nombre, hijos, nivel + 1)


def main():
    raiz = 1
    if len(sys.argv) == 2:
        if not sys.argv[1].isdigit():
            print(f"Uso: {sys.argv[0]} [PID]", file=sys.stderr)
            sys.exit(1)
        raiz = int(sys.argv[1])

    nombre, hijos = leer_procesos()
    if raiz not in nombre:
        print(f"Error: no existe el proceso {raiz}", file=sys.stderr)
        sys.exit(1)

    imprimir_arbol(raiz, nombre, hijos)


if __name__ == "__main__":
    main()
