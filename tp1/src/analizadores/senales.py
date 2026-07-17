#!/usr/bin/env python3
"""
analizadores/senales.py - Analizador de la vista "Señales".

Por pasada, para cada PID: las 5 máscaras de señales (SigBlk/SigIgn/
SigCgt/SigPnd/ShdPnd) ya decodificadas a nombres legibles por
procfs.info_senales(). Sin estado "previo": son máscaras del instante,
no contadores.

Nota de nombre de archivo: este módulo se llama igual que
src/senales.py (el del self-pipe de manejo de señales del PROCESO
MONITOR), pero son cosas completamente distintas -- éste es el
analizador de la vista Señales de cada proceso MONITOREADO. No hay
conflicto de import porque uno vive en analizadores/ y el otro en la
raíz de src/.
"""
import time

import procfs


def analizador_senales(pids_compartidos, snapshot, intervalo, evento_salida):
    """Mismo contrato que analizador_resumen."""
    try:
        while not evento_salida.is_set():
            pids = pids_compartidos.get("pids", [])
            ahora = time.time()
            resultados = []

            for pid in pids:
                try:
                    base = procfs.identificar_proceso(pid)
                    senales = procfs.info_senales(pid)
                except (FileNotFoundError, ProcessLookupError, PermissionError):
                    continue

                base.update(senales)
                resultados.append(base)

            snapshot["senales"] = {"datos": resultados, "timestamp": ahora}
            evento_salida.wait(intervalo.value)
    except KeyboardInterrupt:
        pass
