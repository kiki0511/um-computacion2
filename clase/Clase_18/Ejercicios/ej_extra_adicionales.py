#!/usr/bin/env python3
"""
Ejercicios adicionales - Clase 18.

Modos:
  prioridades → scheduler donde las tareas de mayor prioridad se reanudan
                más seguido (heapq con "tiempo virtual", tipo stride scheduling)
  egoistas    → scheduler que mide cada reanudación y avisa si una tarea
                tardó más de un umbral sin ceder (como loop.set_debug(True))
  pipeline    → cadena de corrutinas-generador con send(): leer → filtrar → contar

Uso:
  python3 ej_extra_adicionales.py [prioridades|egoistas|pipeline|todo]
"""
import heapq
import sys
import time
from collections import deque


# ─────────────────────────────────────────────
# Scheduler con prioridades
# ─────────────────────────────────────────────

def trabajador(nombre, pasos):
    for i in range(1, pasos + 1):
        yield f'{nombre}{i}'


def scheduler_prioridades(tareas):
    """
    tareas: lista de (prioridad, generador). Cada vez que una tarea corre, su
    "pase" avanza 1/prioridad: las de prioridad alta avanzan poco y vuelven
    antes al frente del heap. Una deque no alcanza: hace falta un heap
    ordenado por pase.
    """
    heap = [(0.0, i, prio, g) for i, (prio, g) in enumerate(tareas)]
    heapq.heapify(heap)
    orden = []
    while heap:
        pase, i, prio, g = heapq.heappop(heap)
        try:
            orden.append(next(g))
        except StopIteration:
            continue
        heapq.heappush(heap, (pase + 1 / prio, i, prio, g))
    return orden


def prioridades():
    print('=== Scheduler con prioridades (A=3, B=1) ===')
    orden = scheduler_prioridades([(3, trabajador('A', 9)), (1, trabajador('B', 3))])
    print('  ' + ' '.join(orden))
    print('  → A corre 3 veces por cada vez que corre B.\n')


# ─────────────────────────────────────────────
# Detectar tareas egoístas
# ─────────────────────────────────────────────

def buena(nombre):
    for _ in range(3):
        time.sleep(0.01)
        yield


def mala(nombre):
    yield
    time.sleep(0.3)          # calcula mucho entre dos yield
    yield


def scheduler_vigilante(tareas, umbral=0.1):
    pendientes = deque(tareas)
    while pendientes:
        nombre, g = pendientes.popleft()
        t0 = time.perf_counter()
        try:
            next(g)
            terminada = False
        except StopIteration:
            terminada = True
        dur = time.perf_counter() - t0
        if dur > umbral:
            print(f'  ⚠ {nombre} tardó {dur * 1000:.0f} ms sin ceder (umbral {umbral * 1000:.0f} ms)')
        if not terminada:
            pendientes.append((nombre, g))


def egoistas():
    print('=== Detectar tareas egoístas ===')
    scheduler_vigilante([('buena', buena('buena')), ('mala', mala('mala'))])
    print('  → asyncio hace lo mismo con loop.set_debug(True) y slow_callback_duration.\n')


# ─────────────────────────────────────────────
# Pipeline de corrutinas-generador
# ─────────────────────────────────────────────

def arrancar(func):
    """Decorador: avanza la corrutina hasta el primer yield (el next() inicial)."""
    def envoltura(*a, **kw):
        g = func(*a, **kw)
        next(g)
        return g
    return envoltura


@arrancar
def contar():
    total = 0
    try:
        while True:
            linea = yield
            total += 1
            print(f'    [contar] #{total}: {linea}')
    except GeneratorExit:
        print(f'  [contar] total de líneas que pasaron el filtro: {total}')


@arrancar
def filtrar(palabra, destino):
    try:
        while True:
            linea = yield
            if palabra in linea:
                destino.send(linea)
    except GeneratorExit:
        destino.close()                  # propagar el cierre por la cadena


def leer(lineas, destino):
    """Productor: empuja datos con send(). No es corrutina: es la fuente."""
    for linea in lineas:
        destino.send(linea.rstrip('\n'))
    destino.close()


def pipeline():
    print('=== Pipeline leer → filtrar("ERROR") → contar ===')
    log = ['INFO arranca\n', 'ERROR disco lleno\n', 'INFO sigue\n',
           'ERROR timeout\n', 'WARN memoria\n']
    leer(log, filtrar('ERROR', contar()))
    print()


if __name__ == '__main__':
    modo = sys.argv[1] if len(sys.argv) > 1 else 'todo'
    modos = {'prioridades': [prioridades], 'egoistas': [egoistas], 'pipeline': [pipeline],
             'todo': [prioridades, egoistas, pipeline]}
    if modo not in modos:
        print(__doc__)
        sys.exit(1)
    for m in modos[modo]:
        m()
