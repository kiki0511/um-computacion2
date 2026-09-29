#!/usr/bin/env python3
"""
Ejercicio 2 (OBLIGATORIO): Construir el scheduler.

Event loop cooperativo desde cero, con generadores.

Partes:
  A → intercalado round-robin con deque + contador de reanudaciones
      (+ tarea sin ningún yield)
  B → tarea egoísta con time.sleep(3): congela a todas
  C → dormir(segundos) que CEDE informando cuándo quiere volver;
      scheduler con cola de prioridad por tiempo (heapq)
  D → yield from dormir(...) vs dormir(...) a secas

Uso:
  python3 ej2_scheduler.py [a|b|c|d|todo]
"""
import heapq
import sys
import time
from collections import deque

T0 = time.monotonic()


def t():
    return f'{time.monotonic() - T0:5.2f}s'


# ─────────────────────────────────────────────
# Parte A: intercalado
# ─────────────────────────────────────────────

def tarea(nombre, pasos):
    for i in range(1, pasos + 1):
        print(f'  [{nombre}] paso {i}/{pasos}')
        yield                             # cedo el control al scheduler
    print(f'  [{nombre}] terminada')


def scheduler(tareas):
    """Round-robin: saca una, la reanuda hasta su próximo yield, y si no
    terminó la vuelve a poner al final de la cola."""
    pendientes = deque(tareas)
    reanudaciones = 0
    while pendientes:
        actual = pendientes.popleft()
        try:
            reanudaciones += 1
            next(actual)
        except StopIteration:
            continue                      # terminó: no vuelve a la cola
        pendientes.append(actual)
    return reanudaciones


def sin_yield(nombre):
    """No es un generador: llamarla ejecuta todo y devuelve None."""
    print(f'  [{nombre}] hago todo de una vez')


def parte_a():
    global T0
    T0 = time.monotonic()
    print('=== Parte A: tres tareas de 3, 1 y 2 pasos ===')
    n = scheduler([tarea('A', 3), tarea('B', 1), tarea('C', 2)])
    print(f'  → next() llamado {n} veces (6 pasos + 3 StopIteration)\n')

    print('=== Parte A.3: una "tarea" sin ningún yield ===')
    try:
        scheduler([tarea('A', 1), sin_yield('X')])
    except TypeError as e:
        print(f'  TypeError: {e}')
    print('  → sin yield la función NO es un generador: se ejecutó entera al')
    print('    llamarla (antes de entrar al scheduler) y devolvió None.\n')


# ─────────────────────────────────────────────
# Parte B: la cooperación es obligatoria
# ─────────────────────────────────────────────

def tarea_con_hora(nombre, pasos):
    for i in range(1, pasos + 1):
        print(f'  {t()} [{nombre}] paso {i}/{pasos}')
        yield


def tarea_egoista(nombre):
    print(f'  {t()} [{nombre}] me pongo a calcular')
    time.sleep(3)                         # no cede el control
    print(f'  {t()} [{nombre}] listo')
    yield


def parte_b():
    global T0
    T0 = time.monotonic()
    print('=== Parte B: una tarea egoísta en el medio ===')
    scheduler([tarea_con_hora('A', 3), tarea_egoista('EGO'), tarea_con_hora('C', 3)])
    print('  → Durante los 3 s nadie más avanzó: el scheduler no puede sacarle el')
    print('    control a una tarea, solo lo recupera cuando ella hace yield.\n')


# ─────────────────────────────────────────────
# Parte C: agregar tiempo
# ─────────────────────────────────────────────

def dormir(segundos):
    """No duerme: cede el control diciendo CUÁNDO quiere volver."""
    yield time.monotonic() + segundos


def tarea_lenta(nombre, veces, espera=0.15):
    for i in range(1, veces + 1):
        print(f'  {t()} [{nombre}] {i}/{veces}')
        yield from dormir(espera)         # los yield de dormir suben al scheduler
    print(f'  {t()} [{nombre}] terminada')


def scheduler_con_tiempo(tareas):
    """
    Cola de prioridad ordenada por "cuándo despertar". Si la próxima tarea
    todavía no debe despertar, el scheduler (y SOLO él) duerme hasta ese
    momento: una sola espera real que cubre las esperas de todas.
    """
    cola = []                             # (despertar, contador, generador)
    orden = 0                             # desempate estable para heapq
    for g in tareas:
        heapq.heappush(cola, (0.0, orden, g))
        orden += 1
    reanudaciones = 0
    while cola:
        despertar, _, g = heapq.heappop(cola)
        falta = despertar - time.monotonic()
        if falta > 0:
            time.sleep(falta)             # nadie tiene nada que hacer: esperar
        try:
            reanudaciones += 1
            cuando = next(g)
        except StopIteration:
            continue
        heapq.heappush(cola, (cuando or 0.0, orden, g))
        orden += 1
    return reanudaciones


def parte_c():
    global T0
    print('=== Parte C: tres tareas que esperan 0.15 s por paso ===')
    for corrida in range(1, 4):
        T0 = time.monotonic()
        silencio = corrida > 1
        if silencio:
            import io, contextlib
            with contextlib.redirect_stdout(io.StringIO()):
                scheduler_con_tiempo([tarea_lenta('A', 3), tarea_lenta('B', 2),
                                      tarea_lenta('C', 4)])
        else:
            scheduler_con_tiempo([tarea_lenta('A', 3), tarea_lenta('B', 2),
                                  tarea_lenta('C', 4)])
        total = time.monotonic() - T0
        print(f'  corrida {corrida}: total {total:.2f}s  '
              f'(suma de las esperas: {(3 + 2 + 4) * 0.15:.2f}s)')
    print('  → Las esperas se solapan: el total es la tarea más larga (4 × 0.15 = 0.60s).\n')


# ─────────────────────────────────────────────
# Parte D: yield from
# ─────────────────────────────────────────────

def tarea_sin_yield_from(nombre, veces, espera=0.15):
    for i in range(1, veces + 1):
        print(f'  {t()} [{nombre}] {i}/{veces}')
        dormir(espera)                    # crea el generador y lo tira: no cede nada
    print(f'  {t()} [{nombre}] terminada')
    yield                                 # para que siga siendo un generador


def parte_d():
    global T0
    T0 = time.monotonic()
    print('=== Parte D: dormir(espera) SIN yield from ===')
    scheduler_con_tiempo([tarea_sin_yield_from('A', 3), tarea_sin_yield_from('B', 2)])
    print('  → No falla ruidosamente: dormir(espera) solo CREA un generador que')
    print('    nunca se itera, así que su yield jamás llega al scheduler. Las tareas')
    print('    no esperan ni se intercalan (A corre entera, después B), en 0.00s.')
    print(f'    dormir(1) devuelve un {type(dormir(1)).__name__}, que se descarta sin ejecutarse.\n')


if __name__ == '__main__':
    modo = sys.argv[1] if len(sys.argv) > 1 else 'todo'
    partes = {'a': [parte_a], 'b': [parte_b], 'c': [parte_c], 'd': [parte_d],
              'todo': [parte_a, parte_b, parte_c, parte_d]}
    if modo not in partes:
        print(__doc__)
        sys.exit(1)
    for f in partes[modo]:
        f()
