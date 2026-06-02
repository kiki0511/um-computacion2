#!/usr/bin/env python3
"""
Ejercicio 1.2 - Explorar file descriptors del proceso actual.

Cada proceso tiene una tabla de file descriptors. En Linux se puede inspeccionar
mirando /proc/<PID>/fd, donde cada fd es un symlink a lo que apunta.
Por defecto: 0=stdin, 1=stdout, 2=stderr. Al abrir archivos, el SO asigna el
fd libre más bajo (normalmente 3, 4, ...).
"""
import os


def listar_fds():
    fd_dir = f"/proc/{os.getpid()}/fd"
    print(f"File descriptors de PID {os.getpid()}:")
    for fd in sorted(os.listdir(fd_dir), key=int):
        try:
            target = os.readlink(f"{fd_dir}/{fd}")
            print(f"  fd {fd} -> {target}")
        except OSError as e:
            print(f"  fd {fd} -> (error: {e})")


def main():
    print("=== Estado inicial ===")
    listar_fds()

    print("\n=== Después de abrir un archivo ===")
    f = open("/tmp/test_fd.txt", "w")
    print(f"Archivo abierto con fd {f.fileno()}")
    listar_fds()

    print("\n=== Después de abrir otro ===")
    f2 = open("/etc/passwd", "r")
    print(f"Segundo archivo con fd {f2.fileno()}")
    listar_fds()

    print("\n=== Después de cerrar el primero ===")
    f.close()
    listar_fds()

    print("\n=== Después de cerrar todo ===")
    f2.close()
    listar_fds()


if __name__ == "__main__":
    main()
