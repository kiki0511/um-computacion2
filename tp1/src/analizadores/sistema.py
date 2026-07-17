#!/usr/bin/env python3
"""
analizadores/sistema.py - Analizador de la vista "Sistema global".

A diferencia de los otros 6 analizadores, éste NO produce una fila por
proceso -- produce UN SOLO objeto agregado (CPU global, load average,
memoria del sistema, conteos de procesos, uptime). Por eso
snapshot["sistema"]["datos"] es un dict, no una lista, y display.py lo
trata como caso especial (ver _renderizar_sistema en display.py).

El top 3 por CPU% y por RSS se pide "derivado del snapshot" -- este
analizador LEE (no escribe) snapshot["resumen"] y snapshot["memoria"],
que ya fueron calculados por esos otros dos analizadores. Es la única
vista que lee datos de otra vista en vez de solo /proc directo; sigue
siendo seguro porque cada analizador tiene su propio "casillero" en el
Manager.dict y acá solo se lee, nunca se escribe ahí.
"""
import time

import procfs


def _top_por_campo(filas, campo, n=3):
    """Los n valores más altos de `campo` entre las filas, como
    (pid, usuario, comando, valor) para no acoplar display.py al resto
    de los campos de cada vista."""
    ordenadas = sorted(filas, key=lambda f: f.get(campo, 0), reverse=True)
    return [
        {"pid": f["pid"], "usuario": f.get("usuario", "?"),
         "comando": f.get("comando", "?"), "valor": f.get(campo, 0)}
        for f in ordenadas[:n]
    ]


def analizador_sistema(snapshot, intervalo, evento_salida):
    """
    No recibe pids_compartidos -- a diferencia de los otros 6, este
    analizador no itera procesos individuales; contar_procesos() hace su
    propio procfs.listar_pids() internamente, y el resto de los datos
    (meminfo, loadavg, uptime, /proc/stat) son del sistema, no de un PID.

    Mantiene estado "previo" de la línea `cpu` de /proc/stat entre
    pasadas -- igual que el CPU% por proceso en Resumen, el CPU% global
    también es un delta entre dos lecturas, no un valor instantáneo.
    """
    stat_anterior = procfs.leer_stat_sistema()

    try:
        while not evento_salida.is_set():
            ahora = time.time()

            meminfo = procfs.leer_meminfo()
            loadavg = procfs.leer_loadavg()
            uptime = procfs.leer_uptime()
            stat_actual = procfs.leer_stat_sistema()
            cpu_pct = procfs.calcular_cpu_pct_sistema(stat_actual["cpu"], stat_anterior["cpu"])
            stat_anterior = stat_actual
            conteos = procfs.contar_procesos()

            entrada_resumen = snapshot.get("resumen")
            entrada_memoria = snapshot.get("memoria")
            top_cpu = _top_por_campo(entrada_resumen["datos"], "cpu_pct") if entrada_resumen else []
            top_mem = _top_por_campo(entrada_memoria["datos"], "VmRSS") if entrada_memoria else []

            datos = {
                "cpu_pct": cpu_pct,
                "loadavg": loadavg,
                "meminfo": meminfo,
                "uptime_seg": uptime["uptime_seg"],
                "btime": stat_actual["btime"],
                "conteos_procesos": conteos,
                "top_cpu": top_cpu,
                "top_mem": top_mem,
            }
            snapshot["sistema"] = {"datos": datos, "timestamp": ahora}
            evento_salida.wait(intervalo.value)
    except KeyboardInterrupt:
        pass
