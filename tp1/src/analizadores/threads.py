#!/usr/bin/env python3
"""
analizadores/threads.py - Analizador de la vista "Threads".

A diferencia de los demás analizadores (una fila por proceso), acá cada
fila es UN THREAD -- se recorren todos los PIDs y, para cada uno, todos
sus TIDs (/proc/<pid>/task/). El resultado es una tabla plana de threads
de todo el sistema.

Detalle de diseño: cada fila usa el campo "pid" = tid del thread (no el
pid del proceso dueño). Es así a propósito, para poder reusar tal cual
la lógica genérica de selección/pin/orden de display.py (que identifica
cada fila por su "pid"), sin duplicar esa lógica para un caso especial
de threads. El pid del proceso dueño se guarda aparte, en "pid_proceso".
"""
import time

import procfs


def analizador_threads(pids_compartidos, snapshot, intervalo, evento_salida):
    """
    Mismo contrato que analizador_resumen, con la salvedad de que el
    CPU% por thread SÍ necesita estado "previo" entre pasadas (como en
    Resumen), pero indexado por (pid, tid) en vez de por pid solo -- dos
    threads de procesos distintos pueden tener el mismo tid... en
    realidad no, los tid son únicos a nivel sistema igual que los pid,
    pero se indexa por la tupla de todas formas para que quede explícito
    a qué proceso pertenece cada entrada de estado.
    """
    previo = {}

    try:
        while not evento_salida.is_set():
            pids = pids_compartidos.get("pids", [])
            ahora = time.time()
            resultados = []
            claves_vigentes = set()

            for pid in pids:
                try:
                    tids = procfs.listar_threads(pid)
                except (FileNotFoundError, ProcessLookupError):
                    continue

                for tid in tids:
                    clave = (pid, tid)
                    try:
                        stat = procfs.leer_stat(pid, tid)
                        nombre = procfs.leer_comm(pid, tid)
                        status = procfs.leer_status(pid, tid)
                    except (FileNotFoundError, ProcessLookupError):
                        # El thread terminó entre listar_threads() y leerlo.
                        continue

                    claves_vigentes.add(clave)
                    utime, stime = stat["utime"], stat["stime"]
                    anterior = previo.get(clave)
                    if anterior is not None:
                        u0, s0, t0 = anterior
                        cpu_pct = procfs.calcular_cpu_pct(utime, stime, u0, s0, ahora - t0)
                    else:
                        cpu_pct = 0.0
                    previo[clave] = (utime, stime, ahora)

                    resultados.append({
                        "pid": tid,                 # ver docstring: tid en el campo "pid" a propósito
                        "tid": tid,
                        "pid_proceso": pid,
                        "nombre": nombre,
                        "estado": stat["state"],
                        "estado_desc": procfs.estado_legible(stat["state"]),
                        "cpu_pct": cpu_pct,
                        "ctxt_switches_voluntarios": int(status.get("voluntary_ctxt_switches", "0")),
                        "ctxt_switches_involuntarios": int(status.get("nonvoluntary_ctxt_switches", "0")),
                    })

            # Purgar threads que ya no existen, mismo motivo que en resumen.py.
            for clave_vieja in list(previo.keys()):
                if clave_vieja not in claves_vigentes:
                    del previo[clave_vieja]

            snapshot["threads"] = {"datos": resultados, "timestamp": ahora}
            evento_salida.wait(intervalo.value)
    except KeyboardInterrupt:
        pass
