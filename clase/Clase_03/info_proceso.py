#!/usr/bin/env python3
"""
Ejercicio adicional 6.2 - Información de un proceso desde /proc.

Uso:
    python3 info_proceso.py <PID>

Lee de /proc/<PID>/:
  - cmdline : línea de comando completa
  - status  : nombre, estado, memoria, etc.
  - fd/     : file descriptors abiertos
"""
import os
import sys


def leer_cmdline(pid):
    ruta = f"/proc/{pid}/cmdline"
    with open(ruta, "rb") as f:
        # los argumentos vienen separados por bytes nulos
        datos = f.read().replace(b"\x00", b" ").strip()
    return datos.decode(errors="replace") or "(sin cmdline)"


def leer_status(pid, campos=("Name", "State", "VmRSS", "Threads", "PPid")):
    ruta = f"/proc/{pid}/status"
    info = {}
    with open(ruta) as f:
        for linea in f:
            clave, _, valor = linea.partition(":")
            if clave in campos:
                info[clave] = valor.strip()
    return info


def listar_fds(pid):
    ruta = f"/proc/{pid}/fd"
    fds = []
    for fd in sorted(os.listdir(ruta), key=lambda x: int(x)):
        try:
            destino = os.readlink(os.path.join(ruta, fd))
        except OSError:
            destino = "?"
        fds.append((fd, destino))
    return fds


def main():
    if len(sys.argv) != 2:
        print(f"Uso: {sys.argv[0]} <PID>", file=sys.stderr)
        sys.exit(1)

    pid = sys.argv[1]
    if not pid.isdigit() or not os.path.isdir(f"/proc/{pid}"):
        print(f"Error: no existe el proceso {pid}", file=sys.stderr)
        sys.exit(1)

    try:
        print(f"=== Proceso {pid} ===")
        print(f"cmdline: {leer_cmdline(pid)}\n")

        print("status:")
        for clave, valor in leer_status(pid).items():
            print(f"  {clave}: {valor}")

        print("\nfile descriptors:")
        for fd, destino in listar_fds(pid):
            print(f"  {fd} -> {destino}")
    except PermissionError:
        print("Error: permisos insuficientes para leer este proceso "
              "(probá con sudo o con un proceso propio)", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: el proceso terminó mientras lo inspeccionábamos",
              file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
