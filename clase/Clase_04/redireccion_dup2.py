#!/usr/bin/env python3
"""
Ejercicio 2.1 - Redirección manual de stdout con dup2.

Reproduce lo que hace el shell con `> archivo`, pero a mano:
  1. os.dup(1)  -> guardar una copia del stdout original
  2. os.dup2(archivo, 1) -> hacer que el fd 1 (stdout) apunte al archivo
  3. restaurar al final con dup2 del fd guardado

dup2(src, dst) hace que dst sea una copia de src (cerrando dst si estaba abierto).
"""
import os
import sys


def main():
    print("Este mensaje va a la terminal")

    # Guardar stdout original
    stdout_original = os.dup(1)

    # Abrir archivo destino
    archivo = os.open("/tmp/salida.txt",
                      os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o644)

    # Redirigir stdout al archivo
    os.dup2(archivo, 1)
    os.close(archivo)

    print("Este mensaje va al archivo")
    print("Y este también")
    sys.stdout.flush()  # importante: vaciar el buffer antes de restaurar

    # Restaurar stdout original
    os.dup2(stdout_original, 1)
    os.close(stdout_original)

    print("Volvimos a la terminal")
    print("Revisá el contenido de /tmp/salida.txt")


if __name__ == "__main__":
    main()
