#!/usr/bin/env python3
"""
analizadores/resumen.py - Analizador de la vista "Resumen".

Proceso independiente que, en cada pasada:
  1. Lee la lista de PIDs publicada por el recolector.
  2. Para cada PID, arma su info_resumen() y calcula el CPU% comparando
     contra la lectura anterior de ESE MISMO pid (guardada en un dict
     local a este proceso -- no hace falta compartirla, ningún otro
     proceso necesita el estado "anterior" de este analizador).
  3. Escribe el resultado en el snapshot global compartido.
"""
import time

import procfs


def analizador_resumen(pids_compartidos, snapshot, intervalo, evento_salida):
    """
    Loop principal del analizador de Resumen.

    pids_compartidos: Manager().dict() con clave "pids" (lista de PIDs),
        escrito por el recolector.
    snapshot: Manager().dict() global. Este analizador solo escribe su
        propia clave, snapshot["resumen"], y nunca toca las demás --
        así los 7 analizadores pueden correr en paralelo sin pisarse
        (cada uno tiene su "casillero" propio en el mismo dict).
    intervalo: multiprocessing.Value("d", segundos). Es un Value y no un
        float común porque el proceso principal necesita poder cambiarlo
        en caliente -- por SIGHUP (recarga de config.json) o, en la
        Fase 4, con las teclas +/- de la TUI. Se lee intervalo.value en
        cada vuelta del loop, así el cambio se aplica sin reiniciar el
        proceso.
    evento_salida: multiprocessing.Event() para shutdown limpio.
    """
    # Estado privado de este proceso: última lectura de utime/stime/tiempo
    # por PID, para poder calcular el delta de jiffies en la próxima
    # pasada. No se comparte con nadie -- vive y muere con este proceso.
    previo = {}

    try:
        while not evento_salida.is_set():
            pids = pids_compartidos.get("pids", [])
            ahora = time.time()
            resultados = []

            for pid in pids:
                try:
                    info = procfs.info_resumen(pid)
                except (FileNotFoundError, ProcessLookupError):
                    # El proceso murió entre que el recolector lo listó y
                    # que nosotros lo leímos -- normal con /proc, se ignora.
                    continue

                utime, stime = info["utime"], info["stime"]
                anterior = previo.get(pid)
                if anterior is not None:
                    u0, s0, t0 = anterior
                    info["cpu_pct"] = procfs.calcular_cpu_pct(utime, stime, u0, s0, ahora - t0)
                else:
                    # Primera vez que vemos este PID: no hay "anterior"
                    # para comparar, así que no podemos dar un % todavía.
                    info["cpu_pct"] = 0.0

                previo[pid] = (utime, stime, ahora)
                resultados.append(info)

            # Purgar del estado privado los PIDs que ya no están vivos,
            # para que no crezca indefinidamente si el sistema crea y
            # mata muchos procesos (ej: si corrés esto por horas).
            vigentes = set(pids)
            for pid_viejo in list(previo.keys()):
                if pid_viejo not in vigentes:
                    del previo[pid_viejo]

            snapshot["resumen"] = {"datos": resultados, "timestamp": ahora}
            evento_salida.wait(intervalo.value)
    except KeyboardInterrupt:
        # Mismo motivo que en recolector.py: Ctrl+C le llega directo a
        # este proceso hijo también. Manejo provisorio hasta la Fase 3.
        pass
