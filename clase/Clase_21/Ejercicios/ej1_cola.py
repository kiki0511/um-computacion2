#!/usr/bin/env python3
"""
Ejercicio 1: La cola (asyncio.Queue).

Cubre las 16 preguntas del ejercicio, cada sección se puede correr sola:
  1.1 reparto     → 3 contra 6 workers, cómo se reparte el trabajo
  1.2 task_done   → qué pasa sin task_done() y por qué va en un finally
  1.3 presion     → backpressure con maxsize; memoria con cola infinita; 503
  1.4 apagado     → cancelar contra centinela; un centinela por worker
  1.5 prioridad   → PriorityQueue, el TypeError con empates y la inanición

Uso:
  python3 ej1_cola.py              # todas las secciones
  python3 ej1_cola.py reparto      # solo una (reparto, task_done, presion,
                                   #            apagado, prioridad)
"""
import asyncio
import itertools
import sys
import time
import tracemalloc

DEMORA = 0.05
CENTINELA = object()


# ─────────────────────────────────────────────
# Piezas comunes
# ─────────────────────────────────────────────

async def procesar(tarea):
    """Trabajo simulado: I/O que tarda DEMORA segundos."""
    await asyncio.sleep(DEMORA)
    return f'{tarea} ok'


async def worker(cola, wid, hechas):
    """Worker de la clase: bucle infinito con task_done() en el finally."""
    while True:
        tarea = await cola.get()
        try:
            await procesar(tarea)
            hechas.append((wid, tarea))
        finally:
            cola.task_done()


async def detener(workers):
    """Cancela y espera a los workers (para no dejar tareas sueltas)."""
    for w in workers:
        w.cancel()
    await asyncio.gather(*workers, return_exceptions=True)


# ─────────────────────────────────────────────
# 1.1 El reparto
# ─────────────────────────────────────────────

async def correr_reparto(n_tareas, n_workers):
    cola = asyncio.Queue(maxsize=5)
    hechas = []
    workers = [asyncio.create_task(worker(cola, i, hechas))
               for i in range(n_workers)]
    t0 = time.perf_counter()
    for i in range(n_tareas):
        await cola.put(f'tarea-{i}')
    await cola.join()
    dur = time.perf_counter() - t0
    await detener(workers)

    reparto = {}
    for wid, _ in hechas:
        reparto[wid] = reparto.get(wid, 0) + 1
    return dur, dict(sorted(reparto.items()))


async def seccion_reparto():
    print('=== 1.1 El reparto ===\n')
    n = 12
    print(f'  {n} tareas de {DEMORA}s. Secuencial serían {n * DEMORA:.2f}s')
    print(f'  {"workers":>8}  {"tiempo":>7}  {"ideal":>6}  reparto')
    for w in (3, 6):
        dur, rep = await correr_reparto(n, w)
        ideal = -(-n // w) * DEMORA            # rondas (redondeo arriba) × demora
        print(f'  {w:>8}  {dur:6.3f}s  {ideal:5.2f}s  {rep}')

    # Con tareas de duración DISTINTA el reparto deja de ser parejo:
    # el worker que termina primero vuelve antes a la cola y se lleva más.
    print('\n  Con duraciones distintas (0.01 s a 0.12 s):')
    cola = asyncio.Queue()
    hechas = []

    async def worker_variable(wid):
        while True:
            d = await cola.get()
            try:
                await asyncio.sleep(d)
                hechas.append(wid)
            finally:
                cola.task_done()

    ws = [asyncio.create_task(worker_variable(i)) for i in range(3)]
    for d in [0.12, 0.01, 0.01, 0.01, 0.12, 0.01, 0.01, 0.01, 0.12, 0.01, 0.01, 0.01]:
        cola.put_nowait(d)
    await cola.join()
    await detener(ws)
    print(f'  reparto: { {w: hechas.count(w) for w in range(3)} }  <- ya no es 4/4/4')
    print()


# ─────────────────────────────────────────────
# 1.2 task_done
# ─────────────────────────────────────────────

async def seccion_task_done():
    print('=== 1.2 task_done ===\n')

    # Pregunta 4: worker SIN task_done()
    async def worker_sin_task_done(cola):
        while True:
            tarea = await cola.get()
            await procesar(tarea)
            # falta cola.task_done()

    cola = asyncio.Queue()
    ws = [asyncio.create_task(worker_sin_task_done(cola)) for _ in range(3)]
    for i in range(12):
        cola.put_nowait(i)
    try:
        await asyncio.wait_for(cola.join(), timeout=1.0)
        print('  join() volvió (no debería)')
    except TimeoutError:
        # _unfinished_tasks es interno: lo leemos solo para ver el mecanismo
        print('  Sin task_done(): join() sigue esperando después de 1 s')
        print(f'  qsize() = {cola.qsize()} (la cola está VACÍA) pero el contador '
              f'interno de pendientes = {cola._unfinished_tasks}')
    await detener(ws)

    # Pregunta 6: task_done() DESPUÉS de procesar en vez de en el finally
    async def procesar_que_falla(tarea):
        await asyncio.sleep(DEMORA)
        if tarea == 3:
            raise ValueError('falló la tarea 3')

    async def worker_task_done_sin_finally(cola):
        while True:
            tarea = await cola.get()
            try:
                await procesar_que_falla(tarea)
                cola.task_done()            # si procesar falla, NO se ejecuta
            except ValueError:
                pass                        # el worker sobrevive, pero...

    cola = asyncio.Queue()
    ws = [asyncio.create_task(worker_task_done_sin_finally(cola)) for _ in range(3)]
    for i in range(6):
        cola.put_nowait(i)
    try:
        await asyncio.wait_for(cola.join(), timeout=1.0)
        print('  join() volvió')
    except TimeoutError:
        print('\n  task_done() fuera del finally y una tarea que falla:')
        print(f'  join() se cuelga igual, contador interno = {cola._unfinished_tasks} '
              f'(la tarea que falló nunca se dio por hecha)')
    await detener(ws)
    print()


# ─────────────────────────────────────────────
# 1.3 Backpressure
# ─────────────────────────────────────────────

async def seccion_presion():
    print('=== 1.3 Backpressure ===\n')

    # Pregunta 7 y 8: cuánto tarda el productor según maxsize
    for limite in (2, 100):
        cola = asyncio.Queue(maxsize=limite)
        esperas = []

        async def consumidor_lento():
            while True:
                await cola.get()
                await asyncio.sleep(0.05)
                cola.task_done()

        c = asyncio.create_task(consumidor_lento())
        t0 = time.perf_counter()
        for i in range(10):
            t_put = time.perf_counter()
            await cola.put(i)                 # acá se frena si está llena
            esperas.append(time.perf_counter() - t_put)
        productor = time.perf_counter() - t0
        await cola.join()
        await detener([c])
        bloqueados = sum(1 for e in esperas if e > 0.01)
        print(f'  maxsize={limite:<4} productor: {productor:.2f}s  '
              f'| put() que tuvieron que esperar: {bloqueados}/10')

    # Pregunta 9: memoria con cola infinita y 10.000 pedidos
    print('\n  10.000 pedidos de golpe (cada uno con 1 KB de datos):')
    for limite in (0, 100):                   # 0 = sin límite
        tracemalloc.start()
        cola = asyncio.Queue(maxsize=limite)
        rechazadas = 0
        for i in range(10_000):
            # str(i) al final fuerza un string NUEVO por pedido (si no, Python
            # reutiliza la misma constante 'xxx...' y la medición miente)
            pedido = {'id': i, 'tipo': 'descargar', 'datos': 'x' * 1024 + str(i)}
            try:
                cola.put_nowait(pedido)
            except asyncio.QueueFull:
                rechazadas += 1               # en la API: responder 503
        actual, _ = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        nombre = 'infinita' if limite == 0 else f'maxsize={limite}'
        print(f'  cola {nombre:<12} en cola: {cola.qsize():>6}  '
              f'rechazadas: {rechazadas:>6}  memoria: {actual / 1e6:6.2f} MB')
    print('  -> crece lineal: con 1 millón de pedidos serían ~1.3 GB y el proceso muere por OOM.')
    print('  -> En la API: put_nowait() + except QueueFull -> HTTP 503 (o 429).')
    print()


# ─────────────────────────────────────────────
# 1.4 Apagado
# ─────────────────────────────────────────────

async def seccion_apagado():
    print('=== 1.4 Apagado ===\n')
    lenta = 0.3

    # Pregunta 11 y 12: cancelar a mitad de procesamiento
    async def worker_verboso(cola, wid, hechas, perdidas):
        while True:
            item = await cola.get()
            if item is CENTINELA:
                cola.task_done()
                return
            try:
                await asyncio.sleep(lenta)
                hechas.append(item)
            except asyncio.CancelledError:
                perdidas.append(item)          # la cancelación la cortó a la mitad
                raise
            finally:
                cola.task_done()

    for modo in ('cancelar', 'centinela'):
        cola = asyncio.Queue()
        hechas, perdidas = [], []
        ws = [asyncio.create_task(worker_verboso(cola, i, hechas, perdidas))
              for i in range(3)]
        for i in range(6):
            cola.put_nowait(f't{i}')
        await asyncio.sleep(0.45)              # a mitad de la segunda ronda
        t0 = time.perf_counter()
        if modo == 'cancelar':
            await detener(ws)
        else:
            for _ in ws:
                cola.put_nowait(CENTINELA)
            await asyncio.gather(*ws)
        dur = time.perf_counter() - t0
        print(f'  {modo:<10} terminó en {dur:.2f}s  hechas: {len(hechas)}  '
              f'cortadas a la mitad: {perdidas or "ninguna"}')

    # Pregunta 13: un solo centinela para 3 workers
    cola = asyncio.Queue()
    hechas, perdidas = [], []
    ws = [asyncio.create_task(worker_verboso(cola, i, hechas, perdidas))
          for i in range(3)]
    cola.put_nowait(CENTINELA)                  # uno solo
    hecho, pendiente = await asyncio.wait(ws, timeout=0.5)
    print(f'\n  Un solo centinela para 3 workers: salieron {len(hecho)}, '
          f'siguen esperando en get(): {len(pendiente)}')
    await detener(list(pendiente))
    print()


# ─────────────────────────────────────────────
# 1.5 Prioridades
# ─────────────────────────────────────────────

async def seccion_prioridad():
    print('=== 1.5 Prioridades ===\n')

    # Pregunta 14: PriorityQueue con tuplas (prioridad, tarea). Menor sale primero.
    cola = asyncio.PriorityQueue()
    for prio, nombre in [(3, 'normal'), (1, 'urgente'), (5, 'cuando puedas')]:
        cola.put_nowait((prio, {'nombre': nombre}))
    orden = [cola.get_nowait()[1]['nombre'] for _ in range(3)]
    print(f'  orden de salida: {orden}')

    # Pregunta 15: dos tareas con la misma prioridad
    cola = asyncio.PriorityQueue()
    cola.put_nowait((2, {'nombre': 'a'}))
    try:
        cola.put_nowait((2, {'nombre': 'b'}))
    except TypeError as e:
        print(f'\n  Empate de prioridad con dicts -> TypeError: {e}')

    # Arreglo: un contador como desempate (además mantiene FIFO entre iguales)
    contador = itertools.count()
    cola = asyncio.PriorityQueue()
    for nombre in ('a', 'b', 'c'):
        cola.put_nowait((2, next(contador), {'nombre': nombre}))
    orden = [cola.get_nowait()[2]['nombre'] for _ in range(3)]
    print(f'  Con (prioridad, contador, tarea): {orden}  <- sin error y en orden FIFO')

    # Pregunta 16: inanición. Llega una tarea urgente cada 0.04 s y el worker
    # tarda 0.05 s: siempre hay una urgente esperando, la baja nunca sale.
    cola = asyncio.PriorityQueue()
    contador = itertools.count()
    atendidas = []

    async def productor_urgente(parar):
        while not parar.is_set():
            cola.put_nowait((1, next(contador), 'urgente'))
            await asyncio.sleep(0.04)

    async def worker_prio():
        while True:
            _, _, t = await cola.get()
            await asyncio.sleep(0.05)
            atendidas.append(t)
            cola.task_done()

    cola.put_nowait((5, next(contador), 'baja'))
    parar = asyncio.Event()
    p = asyncio.create_task(productor_urgente(parar))
    w = asyncio.create_task(worker_prio())
    await asyncio.sleep(1.5)
    parar.set()
    await detener([p, w])
    print(f'\n  1.5 s con urgentes llegando sin parar: atendidas {len(atendidas)}, '
          f'¿la de baja prioridad salió? {"sí" if "baja" in atendidas else "NO"}')
    print('  -> Inanición (clase 11). La solución con envejecimiento está en '
          'ej_extra_adicionales.py')
    print()


SECCIONES = {
    'reparto': seccion_reparto,
    'task_done': seccion_task_done,
    'presion': seccion_presion,
    'apagado': seccion_apagado,
    'prioridad': seccion_prioridad,
}


async def main(elegidas):
    for nombre in elegidas:
        await SECCIONES[nombre]()


if __name__ == '__main__':
    pedidas = [a for a in sys.argv[1:] if a in SECCIONES] or list(SECCIONES)
    asyncio.run(main(pedidas))
