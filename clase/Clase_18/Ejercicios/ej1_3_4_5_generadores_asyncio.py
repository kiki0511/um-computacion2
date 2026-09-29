#!/usr/bin/env python3
"""
Ejercicios 1, 3, 4 y 5: generadores que reciben, el puente a async/await,
asyncio de verdad y cuándo sirve.

Uso:
  python3 ej1_3_4_5_generadores_asyncio.py [1|3|4|5|todo]
"""
import asyncio
import sys
import time
import types
import warnings


# ─────────────────────────────────────────────
# Ejercicio 1: generadores que reciben
# ─────────────────────────────────────────────

def acumulador():
    total = 0
    while True:
        n = yield total
        total += n


def contador():
    n = 0
    while True:
        print(f'    voy por {n}')
        yield
        n += 1


def tarea_con_return():
    yield 'trabajando'
    return 'resultado final'


def ej1():
    print('=== 1.1 send() ===')
    a = acumulador()
    try:
        a.send(10)
    except TypeError as e:
        print(f'  send(10) sin next() previo → TypeError: {e}')
    print(f'  next(a) → {next(a)}   (corre hasta el primer yield y entrega total=0)')
    for n in (10, 5, 7):
        print(f'  a.send({n}) → {a.send(n)}')

    print('=== 1.2 el estado sobrevive ===')
    g1, g2 = contador(), contador()
    for g, nombre in ((g1, 'g1'), (g2, 'g2'), (g1, 'g1'), (g1, 'g1'), (g2, 'g2')):
        print(f'  next({nombre}):')
        next(g)
    print(f'  n de g1 = {g1.gi_frame.f_locals["n"]}, n de g2 = {g2.gi_frame.f_locals["n"]}'
          '  ← cada uno tiene su propio frame')

    print('=== 1.3 StopIteration lleva el resultado ===')
    tr = tarea_con_return()
    next(tr)
    try:
        next(tr)
    except StopIteration as e:
        print(f'  e.value = {e.value!r}')
    print()


# ─────────────────────────────────────────────
# Ejercicio 3: el puente
# ─────────────────────────────────────────────

async def f():
    return 99


@types.coroutine
def ceder():
    """Generador que se puede await-ear: el mismo protocolo por debajo."""
    valor = yield 'pausa'
    return valor


async def usa_ceder():
    r = await ceder()
    return f'recibí {r!r}'


def ej3():
    print('=== 3: corrutinas por dentro ===')
    c = f()
    print(f'  type(f()) = {type(c).__name__}, hasattr send: {hasattr(c, "send")}')
    try:
        c.send(None)
    except StopIteration as e:
        print(f'  c.send(None) → StopIteration con value={e.value}')

    c = usa_ceder()
    print(f'  primer send(None) sube hasta el scheduler: {c.send(None)!r}')
    try:
        c.send('hola')
    except StopIteration as e:
        print(f'  send("hola") la reanuda y termina: {e.value!r}')
    print()


# ─────────────────────────────────────────────
# Ejercicio 4: asyncio de verdad
# ─────────────────────────────────────────────

async def tarea(nombre, pasos):
    for i in range(1, pasos + 1):
        print(f'  [{nombre}] paso {i}/{pasos}')
        await asyncio.sleep(0)            # ceder, como el yield del scheduler
    print(f'  [{nombre}] terminada')
    return nombre


async def dormilona(nombre, seg):
    await asyncio.sleep(seg)
    print(f'    terminó {nombre} ({seg}s)')
    return nombre


async def saludar():
    print('  hola')


def ej4():
    print('=== 4.1 el scheduler en asyncio ===')

    async def main():
        await asyncio.gather(tarea('A', 3), tarea('B', 1), tarea('C', 2))
    asyncio.run(main())

    async def sin_await():
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            futuro = asyncio.gather(tarea('X', 1))
            print(f'  sin await, gather devuelve {type(futuro).__name__} y main sigue de largo;')
            print('  al terminar main, asyncio.run() CANCELA lo que quedó pendiente:')
            # marcar la excepción como "vista" para que no ensucie la salida
            futuro.add_done_callback(lambda fut: fut.cancelled() or fut.exception())
        return futuro
    asyncio.run(sin_await())

    asyncio.run(asyncio.sleep(0))
    asyncio.run(asyncio.sleep(0))
    print('  asyncio.run() dos veces seguidas: funciona (cada una crea y cierra su loop)')

    async def anidado():
        c = asyncio.sleep(0)
        try:
            asyncio.run(c)
        except RuntimeError as e:
            c.close()
            print(f'  asyncio.run() adentro de una corrutina: RuntimeError: {e}')
    asyncio.run(anidado())

    print('=== 4.2 crear no es ejecutar ===')
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always')
        saludar()                       # no imprime nada
        import gc
        gc.collect()
        for aviso in w:
            print(f'  saludar() solo → {aviso.category.__name__}: {aviso.message}')
    asyncio.run(saludar())

    print('=== 4.3 gather: orden de fin vs orden de resultados ===')

    async def main3():
        r = await asyncio.gather(dormilona('a', 0.3), dormilona('b', 0.1),
                                 dormilona('c', 0.2))
        print(f'    gather devuelve: {r}  ← en el orden en que se PASARON')
    asyncio.run(main3())

    async def main4():
        t0 = time.perf_counter()
        await asyncio.gather(*(asyncio.sleep(1) for _ in range(3)))
        t_gather = time.perf_counter() - t0
        t0 = time.perf_counter()
        for _ in range(3):
            await asyncio.sleep(1)
        print(f'  gather: {t_gather:.2f}s   for con await: {time.perf_counter() - t0:.2f}s')
    asyncio.run(main4())
    print()


# ─────────────────────────────────────────────
# Ejercicio 5: el bloqueo escondido
# ─────────────────────────────────────────────

def ej5():
    print('=== 5.1: "async" que no es async ===')

    async def bajar_bloqueante(i):
        time.sleep(0.5)                  # como urllib.request.urlopen: bloquea el hilo
        return i

    async def bajar_bien(i):
        await asyncio.sleep(0.5)         # como httpx.AsyncClient.get
        return i

    async def bajar_en_thread(i):
        # si la biblioteca es bloqueante y no hay alternativa: a un thread
        return await asyncio.to_thread(time.sleep, 0.5)

    for nombre, fn in (('bloqueante (urllib)', bajar_bloqueante),
                       ('asíncrona (httpx)', bajar_bien),
                       ('bloqueante en to_thread', bajar_en_thread)):
        async def main():
            await asyncio.gather(*(fn(i) for i in range(5)))
        t0 = time.perf_counter()
        asyncio.run(main())
        print(f'  5 "descargas" de 0.5s, {nombre:<24}: {time.perf_counter() - t0:.2f}s')
    print()


if __name__ == '__main__':
    modo = sys.argv[1] if len(sys.argv) > 1 else 'todo'
    ejs = {'1': [ej1], '3': [ej3], '4': [ej4], '5': [ej5], 'todo': [ej1, ej3, ej4, ej5]}
    if modo not in ejs:
        print(__doc__)
        sys.exit(1)
    for e in ejs[modo]:
        e()
