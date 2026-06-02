#!/usr/bin/env python3
"""
Ejercicio 2.2 - Demostración de stdout vs stderr.

stdout (fd 1) y stderr (fd 2) son canales distintos. Por eso se pueden
redirigir por separado:

    python3 separar_salidas.py > solo_stdout.txt     # captura solo fd 1
    python3 separar_salidas.py 2> solo_stderr.txt    # captura solo fd 2
    python3 separar_salidas.py > out.txt 2> err.txt  # cada uno a su archivo
    python3 separar_salidas.py > todo.txt 2>&1        # ambos al mismo archivo
"""
import sys
import os


def main():
    # stdout
    print("Mensaje normal a stdout")
    sys.stdout.write("Otro mensaje a stdout\n")
    os.write(1, b"Y otro mas directo al fd 1\n")

    # stderr
    print("Mensaje de error a stderr", file=sys.stderr)
    sys.stderr.write("Otro error a stderr\n")
    os.write(2, b"Error directo al fd 2\n")


if __name__ == "__main__":
    main()
