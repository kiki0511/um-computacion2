#!/usr/bin/env python3
"""
analizadores/fds.py - Analizador de la vista "File Descriptors".

Por pasada, para cada PID: la lista completa de FDs abiertos (fd,
destino, tipo inferido) y un resumen con el conteo por tipo. La lista
completa siempre se guarda en el snapshot -- es display.py quien decide
cuánto mostrar según el modo verbose (SIGUSR2), no este analizador. Así
el dato crudo queda completo y disponible también para el dump de
SIGUSR1.
"""
import time

import procfs


def analizador_fds(pids_compartidos, snapshot, intervalo, evento_salida):
    """Mismo contrato que analizador_resumen. Sin estado "previo": la
    lista de FDs abiertos es un dato instantáneo, no un contador."""
    try:
        while not evento_salida.is_set():
            pids = pids_compartidos.get("pids", [])
            ahora = time.time()
            resultados = []

            for pid in pids:
                try:
                    base = procfs.identificar_proceso(pid)
                    fds = procfs.listar_fds(pid)
                except (FileNotFoundError, ProcessLookupError, PermissionError):
                    continue

                conteo_por_tipo = {}
                for fd in fds:
                    conteo_por_tipo[fd["tipo"]] = conteo_por_tipo.get(fd["tipo"], 0) + 1

                base["fds"] = fds
                base["total_fds"] = len(fds)
                base["conteo_por_tipo"] = conteo_por_tipo
                resultados.append(base)

            snapshot["fds"] = {"datos": resultados, "timestamp": ahora}
            evento_salida.wait(intervalo.value)
    except KeyboardInterrupt:
        pass
