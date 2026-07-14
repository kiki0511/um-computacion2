#!/usr/bin/env python3
"""
main.py - Punto de entrada del monitor.

Estado actual (Fase 3 del desarrollo): sobre el pipeline de la Fase 2
(recolector -> analizador Resumen -> snapshot -> display consola) se
agrega manejo de señales real, con el patrón self-pipe de senales.py:

    SIGINT / SIGTERM -> shutdown limpio (termina los procesos hijos)
    SIGHUP            -> recarga config.json (intervalos por vista)
    SIGUSR1           -> vuelca el snapshot actual a dump_<timestamp>.json
    SIGUSR2           -> toggle de modo verbose

Todavía NO tiene: TUI real con vistas alternables (Fase 4), ni los otros
6 analizadores (Fase 5). SIGWINCH queda pendiente (es opcional según la
consigna).
"""
import json
import os
import select
import signal
import time
import multiprocessing as mp

from recolector import recolector
from analizadores.resumen import analizador_resumen
from senales import ManejadorSenales


RUTA_CONFIG = "config.json"  # relativo al cwd -- se corre desde tp1/
INTERVALO_RECOLECTOR = 2     # el recolector no es una "vista", no está en config.json
INTERVALO_DISPLAY = 2        # cada cuánto refresca la consola (independiente de las vistas)

DEFAULTS_CONFIG = {
    "intervalos": {"resumen": 2},
    "filtros_default": {"usuario": None, "comando": None, "orden": "cpu"},
    "verbose": False,
}


def cargar_config():
    """
    Lee config.json. Si no existe o está corrupto, cae a defaults
    razonables en vez de tirar abajo el monitor -- una config.json mal
    escrita a mano (típico al testear SIGHUP) no debería matar el proceso.
    """
    try:
        with open(RUTA_CONFIG) as f:
            config = json.load(f)
        combinada = dict(DEFAULTS_CONFIG)
        combinada.update(config)
        return combinada
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[config] no se pudo leer {RUTA_CONFIG} ({e}), uso defaults")
        return dict(DEFAULTS_CONFIG)


def mostrar(snapshot, verbose):
    """
    Display mínimo: imprime la tabla de Resumen en la consola.
    Placeholder de la Fase 2/3 -- en la Fase 4 esto se reemplaza por una
    TUI real (rich/curses) con las 7 vistas alternables.

    En modo verbose (toggle con SIGUSR2) se agregan columnas extra
    (UID/GID crudos y utime/stime en jiffies) -- un adelanto de lo que
    la Fase 5 va a usar para mostrar más detalle por proceso.
    """
    entrada = snapshot.get("resumen")
    if entrada is None:
        print("(esperando la primera pasada del analizador...)")
        return

    antiguedad = time.time() - entrada["timestamp"]
    print("\033c", end="")  # limpia la terminal entre refrescos
    print(f"Monitor de Procesos -- vista Resumen  "
          f"(datos de hace {antiguedad:.1f}s, verbose={verbose}, "
          f"PID monitor={os.getpid()})\n")

    if verbose:
        print(f"{'PID':>7} {'PPID':>7} {'USUARIO':<10} {'EST':<3} "
              f"{'CPU%':>6} {'THR':>4} {'UID':>5} {'GID':>5} "
              f"{'UTIME':>7} {'STIME':>7}  COMANDO")
    else:
        print(f"{'PID':>7} {'PPID':>7} {'USUARIO':<10} {'EST':<3} "
              f"{'CPU%':>6} {'THR':>4}  COMANDO")

    for p in sorted(entrada["datos"], key=lambda x: x["pid"]):
        comando = p["comando"]
        if len(comando) > 50:
            comando = comando[:47] + "..."

        if verbose:
            print(f"{p['pid']:>7} {p['ppid']:>7} {p['usuario']:<10} "
                  f"{p['estado']:<3} {p['cpu_pct']:>6.1f} {p['num_threads']:>4} "
                  f"{p['uid']:>5} {p['gid']:>5} {p['utime']:>7} {p['stime']:>7}  {comando}")
        else:
            print(f"{p['pid']:>7} {p['ppid']:>7} {p['usuario']:<10} "
                  f"{p['estado']:<3} {p['cpu_pct']:>6.1f} "
                  f"{p['num_threads']:>4}  {comando}")


def dump_snapshot(snapshot):
    """
    SIGUSR1: vuelca el contenido actual del snapshot a un JSON con
    timestamp en el nombre. dict(snapshot) copia los datos del
    Manager.dict a un dict común -- necesario porque el proxy del
    Manager no es serializable directo con json.dump.
    """
    datos = dict(snapshot)
    nombre = f"dump_{int(time.time())}.json"
    with open(nombre, "w") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)
    print(f"\n[SIGUSR1] snapshot volcado a {nombre}")


def main():
    config = cargar_config()

    manager = mp.Manager()
    pids_compartidos = manager.dict()   # recolector -> analizadores
    snapshot = manager.dict()           # analizadores -> display
    evento_salida = mp.Event()          # shutdown cooperativo

    # Value, no float común: SIGHUP (y en la Fase 4 las teclas +/-) lo
    # modifican desde el proceso principal, y el analizador -- que corre
    # en OTRO proceso -- necesita ver ese cambio sin reiniciarse.
    intervalo_resumen = mp.Value("d", config["intervalos"].get("resumen", 2))
    modo_verbose = mp.Value("b", config.get("verbose", False))

    procesos = [
        mp.Process(
            target=recolector,
            args=(pids_compartidos, INTERVALO_RECOLECTOR, evento_salida),
            name="recolector",
        ),
        mp.Process(
            target=analizador_resumen,
            args=(pids_compartidos, snapshot, intervalo_resumen, evento_salida),
            name="analizador-resumen",
        ),
    ]
    for p in procesos:
        p.start()

    manejador = ManejadorSenales()
    manejador.registrar(signal.SIGINT, signal.SIGTERM, signal.SIGHUP,
                         signal.SIGUSR1, signal.SIGUSR2)

    print(f"Monitor corriendo (PID {os.getpid()}). "
          "SIGINT/SIGTERM salir, SIGHUP recargar config, "
          "SIGUSR1 dump, SIGUSR2 toggle verbose.")

    try:
        while True:
            listos, _, _ = select.select([manejador.fd_lectura()], [], [],
                                          INTERVALO_DISPLAY)

            if listos:
                for signum in manejador.leer_pendientes():
                    if signum in (signal.SIGINT, signal.SIGTERM):
                        print(f"\n[{signal.Signals(signum).name}] cerrando...")
                        evento_salida.set()
                    elif signum == signal.SIGHUP:
                        config = cargar_config()
                        intervalo_resumen.value = config["intervalos"].get("resumen", 2)
                        print(f"\n[SIGHUP] config recargada -- "
                              f"intervalo resumen = {intervalo_resumen.value}s")
                    elif signum == signal.SIGUSR1:
                        dump_snapshot(snapshot)
                    elif signum == signal.SIGUSR2:
                        modo_verbose.value = not modo_verbose.value
                        print(f"\n[SIGUSR2] modo verbose = {bool(modo_verbose.value)}")

            if evento_salida.is_set():
                break

            mostrar(snapshot, bool(modo_verbose.value))
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
