#!/usr/bin/env python3
"""
analizadores/scheduling.py - Analizador de la vista "Scheduling".

Por pasada, para cada PID: nice, priority, policy, rt_priority, cpu
affinity, context switches (voluntarios/involuntarios), utime/stime,
SID y PGID -- todo via procfs.info_scheduling(). Sin estado "previo":
son valores del instante o contadores acumulados que se muestran tal
cual expone el kernel.
"""
import time

import procfs


def analizador_scheduling(pids_compartidos, snapshot, intervalo, evento_salida):
    """Mismo contrato que analizador_resumen."""
    try:
        while not evento_salida.is_set():
            pids = pids_compartidos.get("pids", [])
            ahora = time.time()
            resultados = []

            for pid in pids:
                try:
                    base = procfs.identificar_proceso(pid)
                    sched = procfs.info_scheduling(pid)
                except (FileNotFoundError, ProcessLookupError):
                    continue

                base.update(sched)
                resultados.append(base)

            snapshot["scheduling"] = {"datos": resultados, "timestamp": ahora}
            evento_salida.wait(intervalo.value)
    except KeyboardInterrupt:
        pass
