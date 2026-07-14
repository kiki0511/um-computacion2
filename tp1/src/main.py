#!/usr/bin/env python3
"""
main.py - Punto de entrada del monitor.

Estado actual (Fase 2 del desarrollo -- vertical slice): arma el pipeline
mínimo end-to-end para validar que la arquitectura multiproceso con IPC
funciona antes de escalar a los 7 analizadores:

    recolector -> [pids_compartidos] -> analizador Resumen
                                              |
                                              v
                                     [snapshot] -> display (consola)

Todavía NO tiene: manejo de señales (Fase 3), TUI real con vistas
alternables (Fase 4), ni los otros 6 analizadores (Fase 5). El shutdown
acá es con Ctrl+C simple (SIGINT por defecto de Python), sin handler
propio todavía.
"""
import time
import multiprocessing as mp

from recolector import recolector
from analizadores.resumen import analizador_resumen


INTERVALO_RECOLECTOR = 2   # segundos
INTERVALO_RESUMEN = 2      # segundos (default de la vista Resumen)
INTERVALO_DISPLAY = 2      # cada cuánto refresca la consola


def mostrar(snapshot):
    """
    Display mínimo: imprime la tabla de Resumen en la consola.
    Placeholder de la Fase 2 -- en la Fase 4 esto se reemplaza por una
    TUI real (rich/curses) con las 7 vistas alternables.
    """
    entrada = snapshot.get("resumen")
    if entrada is None:
        print("(esperando la primera pasada del analizador...)")
        return

    antiguedad = time.time() - entrada["timestamp"]
    print("\033c", end="")  # limpia la terminal entre refrescos
    print(f"Monitor de Procesos -- vista Resumen  "
          f"(datos de hace {antiguedad:.1f}s, Ctrl+C para salir)\n")
    print(f"{'PID':>7} {'PPID':>7} {'USUARIO':<10} {'EST':<3} "
          f"{'CPU%':>6} {'THR':>4}  COMANDO")

    for p in sorted(entrada["datos"], key=lambda x: x["pid"]):
        comando = p["comando"]
        if len(comando) > 50:
            comando = comando[:47] + "..."
        print(f"{p['pid']:>7} {p['ppid']:>7} {p['usuario']:<10} "
              f"{p['estado']:<3} {p['cpu_pct']:>6.1f} "
              f"{p['num_threads']:>4}  {comando}")


def main():
    manager = mp.Manager()
    pids_compartidos = manager.dict()   # recolector -> analizadores
    snapshot = manager.dict()           # analizadores -> display
    evento_salida = mp.Event()          # shutdown cooperativo

    procesos = [
        mp.Process(
            target=recolector,
            args=(pids_compartidos, INTERVALO_RECOLECTOR, evento_salida),
            name="recolector",
        ),
        mp.Process(
            target=analizador_resumen,
            args=(pids_compartidos, snapshot, INTERVALO_RESUMEN, evento_salida),
            name="analizador-resumen",
        ),
    ]

    for p in procesos:
        p.start()

    try:
        while True:
            mostrar(snapshot)
            time.sleep(INTERVALO_DISPLAY)
    except KeyboardInterrupt:
        print("\nCtrl+C recibido, cerrando procesos hijos...")
    finally:
        evento_salida.set()
        for p in procesos:
            p.join(timeout=3)
            if p.is_alive():
                p.terminate()
                p.join()
        print("Listo, todos los procesos hijos terminaron.")


if __name__ == "__main__":
    main()
