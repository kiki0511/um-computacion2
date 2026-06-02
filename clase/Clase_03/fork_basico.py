#!/usr/bin/env python3
"""
Ejercicio 2.1 - Mi primer fork.

Demuestra cómo os.fork() duplica el proceso: a partir de la llamada,
el código se ejecuta DOS veces (una en el padre, otra en el hijo).

Observaciones al correrlo varias veces:
- El orden de los mensajes del padre y del hijo NO es determinista:
  depende de a quién planifique el scheduler primero.
- El último print aparece dos veces porque tanto el padre como el hijo
  ejecutan esa línea (ambos continúan después del fork).
"""
import os


def main():
    print(f"Proceso original: PID={os.getpid()}")

    pid = os.fork()

    if pid == 0:
        # Este bloque solo lo ejecuta el HIJO (fork devuelve 0 en el hijo)
        print(f"Soy el HIJO: PID={os.getpid()}, PPID={os.getppid()}")
    else:
        # Este bloque solo lo ejecuta el PADRE (fork devuelve el PID del hijo)
        print(f"Soy el PADRE: PID={os.getpid()}, hijo={pid}")

    # Esta línea la ejecutan AMBOS procesos -> aparece dos veces
    print(f"Este mensaje lo imprime PID={os.getpid()}")


if __name__ == "__main__":
    main()
