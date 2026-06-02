#!/usr/bin/env python3
"""
Ejercicio 1 - Tu primer Process (vs os.fork()).

Reescribe el patrón fork+exec+wait de la Clase 3 usando
multiprocessing.Process.

¿Qué nos ahorramos respecto de os.fork()?
  - No hay rama "if pid == 0" (el código del hijo es una función target).
  - No llamamos os._exit() a mano ni os.wait().
  - join() reemplaza a wait(); p.exitcode da el código de salida.
  - Es portable (Linux/macOS/Windows), fork() no lo es.
"""
import multiprocessing
import os
import time


def tarea(nombre):
    print(f"[{nombre}] PID={os.getpid()}, parent={os.getppid()}")
    time.sleep(1)
    print(f"[{nombre}] termino")


def main():
    p = multiprocessing.Process(target=tarea, args=("Worker",))
    p.start()
    p.join()
    print(f"[Main] PID={os.getpid()}, hijo terminó con exitcode={p.exitcode}")


if __name__ == "__main__":
    main()
