#!/usr/bin/env python3
"""
Ejercicio 2.3 - Múltiples hijos.

El padre crea 3 hijos con duraciones distintas y espera a todos.

Observación clave: los hijos NO terminan en el orden en que fueron
creados, sino en el orden en que completan su trabajo (el de 1s termina
antes que el de 2s aunque se haya creado después).
"""
import os
import time


def trabajo_hijo(numero, duracion):
    """Trabajo que hace cada hijo: dormir y salir con un código propio."""
    print(f"Hijo {numero} (PID {os.getpid()}): iniciando, durará {duracion}s")
    time.sleep(duracion)
    print(f"Hijo {numero}: terminando")
    os._exit(numero)  # código de salida = número de hijo


def main():
    hijos_config = [2, 1, 3]  # duraciones en segundos
    hijos_pids = []

    for i, duracion in enumerate(hijos_config):
        pid = os.fork()
        if pid == 0:
            trabajo_hijo(i, duracion)
            # No se vuelve de aquí gracias a os._exit
        else:
            hijos_pids.append(pid)
            print(f"Padre: creado hijo {i} con PID {pid}")

    print(f"\nPadre: esperando a {len(hijos_pids)} hijos...")
    while hijos_pids:
        pid, status = os.wait()
        codigo = os.WEXITSTATUS(status)
        hijos_pids.remove(pid)
        print(f"Padre: hijo PID {pid} terminó con código {codigo}")

    print("Padre: todos los hijos terminaron")


if __name__ == "__main__":
    main()
