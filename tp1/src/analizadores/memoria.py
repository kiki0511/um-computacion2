#!/usr/bin/env python3
"""
analizadores/memoria.py - Analizador de la vista "Memoria".

Por pasada, para cada PID: los contadores VmSize/VmRSS/.../VmSwap de
status (instantáneos, no hacen falta dos lecturas), los page faults
minor/major de stat (acumulados desde que arrancó el proceso -- se
muestran tal cual los expone el kernel, sin convertir a tasa por
segundo, ya que la consigna no lo pide), y los segmentos de memoria
agrupados por categoría desde /proc/<pid>/maps.
"""
import time

import procfs


def analizador_memoria(pids_compartidos, snapshot, intervalo, evento_salida):
    """
    pids_compartidos / snapshot / intervalo / evento_salida: mismo
    contrato que analizador_resumen (ver analizadores/resumen.py). Este
    analizador no necesita estado "previo" entre pasadas -- a diferencia
    de CPU%, todos sus datos son valores instantáneos o acumulados que
    ya vienen calculados por el kernel.
    """
    try:
        while not evento_salida.is_set():
            pids = pids_compartidos.get("pids", [])
            ahora = time.time()
            resultados = []

            for pid in pids:
                try:
                    base = procfs.identificar_proceso(pid)
                    vm = procfs.info_memoria_status(pid)
                    stat = procfs.leer_stat(pid)
                    segmentos = procfs.agrupar_memoria(pid)
                except (FileNotFoundError, ProcessLookupError):
                    continue

                base.update(vm)
                base["minflt"] = stat["minflt"]
                base["majflt"] = stat["majflt"]
                base["segmentos"] = segmentos
                resultados.append(base)

            snapshot["memoria"] = {"datos": resultados, "timestamp": ahora}
            evento_salida.wait(intervalo.value)
    except KeyboardInterrupt:
        pass
