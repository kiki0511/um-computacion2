#!/usr/bin/env python3
"""
Ejercicio 3 (OBLIGATORIO): Sacar el trabajo del loop — partes A, B y C.
La parte D (la API) está en ej3d_api_hashear.py.

  A → el loop bloqueado: sin executor / ProcessPoolExecutor / to_thread,
      con duración y peor atraso del loop (preguntas 1-4)
  B → threads contra procesos: 4 tareas CPU, 1 tarea CPU, 4 tareas I/O
      (time.sleep) (preguntas 5-8)
  C → el costo de los procesos: lambda, argumento grande, pool por tarea
      contra pool reutilizado (preguntas 9-11)

Al final imprime una tabla en markdown lista para pegar en respuestas.md.

IMPORTANTE (macOS): ProcessPoolExecutor usa 'spawn' y re-importa este
archivo en cada proceso hijo. Por eso las funciones que van al pool están
a nivel de módulo y todo arranca desde el if __name__ == '__main__'.

Uso:
  python3 ej3_executor.py                  # A, B y C (~1 minuto)
  python3 ej3_executor.py A                # una sola parte (A, B o C)
  python3 ej3_executor.py --vueltas 1000000   # cálculo más corto
"""
import asyncio
import hashlib
import multiprocessing
import os
import pickle
import sys
import time
from concurrent.futures import ProcessPoolExecutor

VUELTAS = 3_000_000          # ~5 s de CPU (igual que executor.py)
LATIDO = 0.05                # el medidor debería despertarse cada 50 ms
tabla = []                   # filas para el resumen final


# ─────────────────────────────────────────────
# Funciones que van al executor (nivel de módulo: se pueden picklear)
# ─────────────────────────────────────────────

def hashear(vueltas):
    """CPU-bound puro: SHA-256 iterado. Con 32 bytes de entrada, hashlib
    NO suelta el GIL (solo lo suelta con más de ~2 KB).

    Las vueltas se pasan SIEMPRE como argumento: con 'spawn' (macOS) el hijo
    re-importa el módulo y no ve los cambios que main le hizo a VUELTAS."""
    h = b'x'
    for _ in range(vueltas):
        h = hashlib.sha256(h).digest()
    return h.hex()[:8]


def dormir(segundos):
    """I/O-bound simulado: time.sleep SÍ suelta el GIL."""
    time.sleep(segundos)
    return segundos


def sumar(numeros):
    return sum(numeros)


def cuadrado(x):
    return x * x


# ─────────────────────────────────────────────
# Parte A: el loop bloqueado
# ─────────────────────────────────────────────

async def medidor(muestras, parar):
    """Duerme LATIDO y anota cuánto se pasó. Si el loop está bloqueado,
    el sleep vence pero nadie lo despierta hasta que el loop se libera."""
    while not parar.is_set():
        t0 = time.perf_counter()
        await asyncio.sleep(LATIDO)
        muestras.append((time.perf_counter() - t0 - LATIDO) * 1000)


async def medir(trabajo):
    muestras = []
    parar = asyncio.Event()
    m = asyncio.create_task(medidor(muestras, parar))
    await asyncio.sleep(0.2)
    t0 = time.perf_counter()
    await trabajo()
    dur = time.perf_counter() - t0
    parar.set()
    await asyncio.sleep(LATIDO * 2)
    m.cancel()
    await asyncio.gather(m, return_exceptions=True)
    return dur, max(muestras, default=0.0)


async def parte_a():
    print(f'=== Parte A: el loop bloqueado ({VUELTAS:,} vueltas de SHA-256) ===\n')
    loop = asyncio.get_running_loop()

    async def sin_executor():
        hashear(VUELTAS)                              # corre EN el loop

    with ProcessPoolExecutor(max_workers=2) as pool:
        async def con_procesos():
            await loop.run_in_executor(pool, hashear, VUELTAS)  # otro proceso

        async def con_threads():
            await asyncio.to_thread(hashear, VUELTAS)           # otro thread

        for nombre, trabajo in (('sin executor', sin_executor),
                                ('ProcessPoolExecutor', con_procesos),
                                ('asyncio.to_thread', con_threads)):
            dur, atraso = await medir(trabajo)
            print(f'  {nombre:<22} {dur:6.2f} s  | peor atraso del loop: {atraso:8.1f} ms')
            tabla.append(('A', nombre, f'{dur:.2f} s', f'{atraso:.1f} ms'))
    print('\n  Sin executor el atraso ≈ toda la duración: durante ese lapso el')
    print('  servidor no acepta conexiones, no responde, no dispara timeouts.\n')


# ─────────────────────────────────────────────
# Parte B: threads contra procesos
# ─────────────────────────────────────────────

async def comparar(n, funcion, *args):
    loop = asyncio.get_running_loop()

    t0 = time.perf_counter()
    await asyncio.gather(*(asyncio.to_thread(funcion, *args) for _ in range(n)))
    con_threads = time.perf_counter() - t0

    with ProcessPoolExecutor(max_workers=n) as pool:
        # Calentar el pool: que el arranque de los procesos no entre en la medición
        await asyncio.gather(*(loop.run_in_executor(pool, cuadrado, 1) for _ in range(n)))
        t0 = time.perf_counter()
        await asyncio.gather(*(loop.run_in_executor(pool, funcion, *args)
                               for _ in range(n)))
        con_procesos = time.perf_counter() - t0
    return con_threads, con_procesos


async def parte_b():
    print(f'=== Parte B: threads contra procesos ({os.cpu_count()} núcleos, '
          f'start method: {multiprocessing.get_start_method()}) ===\n')
    casos = [
        ('4 tareas CPU (hashear)', 4, hashear, VUELTAS),
        ('1 tarea CPU (hashear)', 1, hashear, VUELTAS),
        ('4 tareas I/O (time.sleep 2 s)', 4, dormir, 2),
    ]
    print(f'  {"caso":<32} {"threads":>9} {"procesos":>9}  relación')
    for nombre, n, funcion, *args in casos:
        th, pr = await comparar(n, funcion, *args)
        print(f'  {nombre:<32} {th:8.2f}s {pr:8.2f}s  {th / pr:5.2f}x')
        tabla.append(('B', nombre, f'{th:.2f} s', f'{pr:.2f} s'))
    print('\n  CPU: los threads se turnan el GIL -> 4 tareas ≈ 4 veces una.')
    print('  I/O: time.sleep suelta el GIL -> los threads ya son paralelos.\n')


# ─────────────────────────────────────────────
# Parte C: el costo de los procesos
# ─────────────────────────────────────────────

async def parte_c():
    print('=== Parte C: el costo de los procesos ===\n')
    loop = asyncio.get_running_loop()

    with ProcessPoolExecutor(max_workers=2) as pool:
        # Pregunta 9: una lambda
        error = 'ninguno'
        try:
            await loop.run_in_executor(pool, lambda: 2 + 2)
        except Exception as e:
            error = type(e).__name__
            print(f'  lambda al executor -> {error}: {e}')
        try:
            pickle.dumps(lambda: 2 + 2)
        except Exception as e:
            print(f'  (es el pickle: {type(e).__name__}: {e})')
        tabla.append(('C', 'lambda al executor', error, ''))

        # Pregunta 10: argumento grande contra un número
        await loop.run_in_executor(pool, cuadrado, 1)            # calentar
        grande = list(range(1_000_000))
        t0 = time.perf_counter()
        for _ in range(5):
            await loop.run_in_executor(pool, cuadrado, 7)
        chico = (time.perf_counter() - t0) / 5
        t0 = time.perf_counter()
        for _ in range(5):
            await loop.run_in_executor(pool, sumar, grande)
        lista = (time.perf_counter() - t0) / 5
        t0 = time.perf_counter()
        for _ in range(5):
            sum(grande)
        local = (time.perf_counter() - t0) / 5
        tam = len(pickle.dumps(grande)) / 1e6
        print(f'\n  un número al pool:          {chico * 1000:7.2f} ms por llamada')
        print(f'  lista de 1M números al pool: {lista * 1000:7.2f} ms por llamada '
              f'({tam:.1f} MB pickleados)')
        print(f'  sum() de esa lista en local: {local * 1000:7.2f} ms  <- el viaje '
              f'cuesta más que el cálculo')
        tabla.append(('C', 'arg chico / 1M números / local',
                      f'{chico * 1000:.2f} ms / {lista * 1000:.1f} ms',
                      f'{local * 1000:.1f} ms'))

    # Pregunta 11: pool por tarea contra pool reutilizado
    n = 10
    t0 = time.perf_counter()
    for _ in range(n):
        with ProcessPoolExecutor(max_workers=1) as p:
            await loop.run_in_executor(p, cuadrado, 3)
    por_tarea = (time.perf_counter() - t0) / n
    with ProcessPoolExecutor(max_workers=1) as p:
        await loop.run_in_executor(p, cuadrado, 3)              # crear el proceso
        t0 = time.perf_counter()
        for _ in range(n):
            await loop.run_in_executor(p, cuadrado, 3)
        reutilizado = (time.perf_counter() - t0) / n
    print(f'\n  pool nuevo por tarea:  {por_tarea * 1000:7.2f} ms por tarea')
    print(f'  pool reutilizado:      {reutilizado * 1000:7.2f} ms por tarea  '
          f'({por_tarea / reutilizado:.0f}x más barato)\n')
    tabla.append(('C', 'pool por tarea / reutilizado',
                  f'{por_tarea * 1000:.1f} ms', f'{reutilizado * 1000:.2f} ms'))


def imprimir_tabla():
    print('=== Para pegar en respuestas.md ===\n')
    print('| Parte | Caso | Valor 1 | Valor 2 |')
    print('|-------|------|---------|---------|')
    for fila in tabla:
        print('| ' + ' | '.join(fila) + ' |')
    print('\n(A: duración | peor atraso.  B: threads | procesos.  '
          'C: según la fila)')


async def main(partes):
    if 'A' in partes:
        await parte_a()
    if 'B' in partes:
        await parte_b()
    if 'C' in partes:
        await parte_c()
    imprimir_tabla()


if __name__ == '__main__':
    args = sys.argv[1:]
    if '--vueltas' in args:
        VUELTAS = int(args[args.index('--vueltas') + 1])
    partes = [a for a in args if a in ('A', 'B', 'C')] or ['A', 'B', 'C']
    asyncio.run(main(partes))
