#!/usr/bin/env python3
"""
main.py - Punto de entrada del monitor.

Estado actual (Fase 4 del desarrollo): sobre el pipeline con señales de
la Fase 3, se reemplaza el display de consola simple por una TUI real
con curses (display.py), con las 7 vistas navegables (solo Resumen tiene
un analizador real detrás -- Fase 5 conecta el resto).

    señales (self-pipe) ─┐
                          ├─→ loop principal (curses.wrapper) ─→ pantalla
    teclado (curses) ─────┘

Todavía NO tiene los otros 6 analizadores (Fase 5) ni empaquetado Docker
(Fase 6). SIGWINCH queda pendiente (opcional según la consigna).
"""
import curses
import json
import select
import signal
import time
import multiprocessing as mp

from recolector import recolector
from analizadores.resumen import analizador_resumen
from senales import ManejadorSenales
import display


RUTA_CONFIG = "config.json"  # relativo al cwd -- se corre desde tp1/
INTERVALO_RECOLECTOR = 2     # el recolector no es una "vista", no está en config.json

DEFAULTS_CONFIG = {
    "intervalos": {v["clave"]: v["intervalo_min"] * 2 for v in display.VISTAS},
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


def dump_snapshot(snapshot):
    """SIGUSR1: vuelca el snapshot actual a dump_<timestamp>.json."""
    datos = dict(snapshot)
    nombre = f"dump_{int(time.time())}.json"
    with open(nombre, "w") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)
    return nombre


def bucle_ui(stdscr, snapshot, intervalos, modo_verbose, evento_salida, manejador, config_ref):
    """
    Loop principal de la TUI, ejecutado dentro de curses.wrapper().

    config_ref es una lista de 1 elemento (config_ref[0] = config actual)
    en vez de una variable común, porque SIGHUP necesita reasignarla
    desde este mismo loop y Python no deja reasignar una variable de un
    scope exterior sin "nonlocal" -- una lista mutable es más simple acá
    que declarar nonlocal.
    """
    curses.curs_set(0)      # sin cursor parpadeante fuera de pedir_texto()
    stdscr.timeout(150)     # ms -- también marca el ritmo del loop

    estado = display.EstadoUI()

    while True:
        filas_crudas = display.obtener_filas(snapshot, estado.vista_activa)
        filas = display.filtrar_y_ordenar(filas_crudas, estado) if filas_crudas is not None else []
        display.sincronizar_seleccion_pineada(estado, filas)

        tecla = stdscr.getch()
        if tecla != -1:
            resultado = display.procesar_tecla(estado, tecla, intervalos, filas)
            if resultado == "salir":
                evento_salida.set()
            elif resultado == "pedir_comando":
                estado.filtro_comando = display.pedir_texto(stdscr, "Filtrar por comando: ")
            elif resultado == "pedir_usuario":
                estado.filtro_usuario = display.pedir_texto(stdscr, "Filtrar por usuario: ")

        # Señales del sistema operativo (no bloqueante -- el timeout de
        # getch() ya le da ritmo al loop, acá solo miramos si hay algo).
        listos, _, _ = select.select([manejador.fd_lectura()], [], [], 0)
        if listos:
            for signum in manejador.leer_pendientes():
                if signum in (signal.SIGINT, signal.SIGTERM):
                    evento_salida.set()
                elif signum == signal.SIGHUP:
                    config_ref[0] = cargar_config()
                    for clave, value in intervalos.items():
                        value.value = config_ref[0]["intervalos"].get(clave, value.value)
                elif signum == signal.SIGUSR1:
                    dump_snapshot(snapshot)
                elif signum == signal.SIGUSR2:
                    modo_verbose.value = not modo_verbose.value

        if evento_salida.is_set():
            break

        display.renderizar(stdscr, estado, snapshot, filas, intervalos, bool(modo_verbose.value))


def main():
    config = cargar_config()

    manager = mp.Manager()
    pids_compartidos = manager.dict()   # recolector -> analizadores
    snapshot = manager.dict()           # analizadores -> display
    evento_salida = mp.Event()          # shutdown cooperativo

    # Un Value por vista (las 7), no solo para "resumen": SIGHUP y las
    # teclas +/- de cualquier vista necesitan algo para modificar incluso
    # antes de que la Fase 5 conecte los analizadores que faltan.
    intervalos = {
        v["clave"]: mp.Value("d", config["intervalos"].get(v["clave"], v["intervalo_min"] * 2))
        for v in display.VISTAS
    }
    modo_verbose = mp.Value("b", config.get("verbose", False))

    procesos = [
        mp.Process(
            target=recolector,
            args=(pids_compartidos, INTERVALO_RECOLECTOR, evento_salida),
            name="recolector",
        ),
        mp.Process(
            target=analizador_resumen,
            args=(pids_compartidos, snapshot, intervalos["resumen"], evento_salida),
            name="analizador-resumen",
        ),
    ]
    for p in procesos:
        p.start()

    manejador = ManejadorSenales()
    manejador.registrar(signal.SIGINT, signal.SIGTERM, signal.SIGHUP,
                         signal.SIGUSR1, signal.SIGUSR2)

    try:
        curses.wrapper(bucle_ui, snapshot, intervalos, modo_verbose,
                        evento_salida, manejador, [config])
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
