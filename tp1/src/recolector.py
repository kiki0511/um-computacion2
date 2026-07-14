#!/usr/bin/env python3
"""
recolector.py - Lista los procesos vivos del sistema y los publica en una
estructura compartida para que los analizadores los lean.

Corre como un Process independiente y no analiza nada por sí mismo: solo
hace `procfs.listar_pids()` cada cierto intervalo y publica el resultado.
Cada analizador lee esa lista a su propio ritmo para saber qué PIDs
recorrer en su pasada -- el recolector no sabe ni le importa cuántos
analizadores la están leyendo.
"""
import time

import procfs


def recolector(pids_compartidos, intervalo, evento_salida):
    """
    Loop principal del recolector.

    pids_compartidos: multiprocessing.Manager().dict() compartido, con
        clave "pids" (lista de ints) y "timestamp" (float). Se usa un
        Manager.dict en vez de un dict común porque hay que compartirlo
        entre procesos con memoria separada -- un dict regular no
        atravesaría el fork/pickle de forma sincronizada; el Manager
        corre un proceso servidor aparte que serializa el acceso.
    intervalo: segundos entre listados (default sugerido por la consigna
        para Resumen: 2s -- acá se pasa como parámetro para poder
        ajustarlo más adelante).
    evento_salida: multiprocessing.Event() -- cuando el proceso principal
        lo activa (shutdown), el loop corta en la próxima vuelta en vez
        de bloquear con time.sleep().
    """
    try:
        while not evento_salida.is_set():
            pids_compartidos["pids"] = procfs.listar_pids()
            pids_compartidos["timestamp"] = time.time()
            evento_salida.wait(intervalo)
    except KeyboardInterrupt:
        # Ctrl+C le llega también a este proceso hijo (mismo grupo de
        # proceso que la terminal). Manejo provisorio: salir sin
        # traceback. En la Fase 3 esto se reemplaza por un handler de
        # SIGINT real vía self-pipe, coordinado con evento_salida.
        pass
