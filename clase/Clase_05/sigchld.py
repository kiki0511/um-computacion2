#!/usr/bin/env python3
"""
Ejercicio 3.2 - SIGCHLD para detectar hijos terminados.

Cuando un hijo termina, el kernel envía SIGCHLD al padre. En el manejador
hacemos os.waitpid(-1, WNOHANG) en un loop para recoger TODOS los hijos que
hayan terminado (varios pueden terminar casi a la vez y SIGCHLD no se
encola). Así el padre evita zombies sin bloquearse esperando.
"""
import os
import signal
import time

hijos_activos = set()
resultados = {}


def sigchld_handler(sig, frame):
    """Recoger hijos terminados sin bloquear (WNOHANG)."""
    while True:
        try:
            pid, status = os.waitpid(-1, os.WNOHANG)
            if pid == 0:
                break  # no quedan hijos terminados por recoger
            hijos_activos.discard(pid)
            codigo = os.WEXITSTATUS(status) if os.WIFEXITED(status) else -1
            resultados[pid] = codigo
            print(f"[SIGCHLD] Hijo {pid} terminó con código {codigo}")
        except ChildProcessError:
            break


def main():
    signal.signal(signal.SIGCHLD, sigchld_handler)

    print("Creando 5 hijos...")
    for i in range(5):
        pid = os.fork()
        if pid == 0:
            duracion = (i + 1) * 0.5
            time.sleep(duracion)
            os._exit(i)
        else:
            hijos_activos.add(pid)
            print(f"Creado hijo {pid}, durará {(i + 1) * 0.5}s")

    print("\n[PADRE] Trabajando mientras los hijos se ejecutan...")
    for tick in range(10):
        print(f"[PADRE] Tick {tick}, hijos activos: {len(hijos_activos)}")
        time.sleep(0.5)
        if not hijos_activos:
            break

    print(f"\n[PADRE] Todos terminaron. Resultados: {resultados}")


if __name__ == "__main__":
    main()
