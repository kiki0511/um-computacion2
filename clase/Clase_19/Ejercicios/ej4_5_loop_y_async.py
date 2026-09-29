#!/usr/bin/env python3
"""
Ejercicios 4 y 5: dónde está el event loop, y async bien y mal.

Modos:
  workers → levanta `uvicorn ej3_api:app --workers 3`, pide /quien-soy varias
            veces, y muestra que el estado en memoria NO se comparte
  medir   → medir.py con un cuarto grupo: cálculo pesado (hash iterado)
            escrito de tres formas (async def, def, async + ProcessPool)

Uso:
  python3 ej4_5_loop_y_async.py workers
  python3 ej4_5_loop_y_async.py medir
"""
import asyncio
import hashlib
import multiprocessing
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor

PUERTO_WORKERS = 8003
PUERTO_MEDIR = 8004
PEDIDOS = 3
DEMORA = 1.0
ITER = 1_500_000                   # ~0.5 s de CPU


# ─────────────────────────────────────────────
# Ejercicio 4: varios workers
# ─────────────────────────────────────────────

def workers():
    import httpx
    aqui = os.path.dirname(os.path.abspath(__file__))
    srv = subprocess.Popen(
        [sys.executable, '-m', 'uvicorn', 'ej3_api:app', '--workers', '3',
         '--port', str(PUERTO_WORKERS), '--log-level', 'error'], cwd=aqui)
    base = f'http://127.0.0.1:{PUERTO_WORKERS}'
    try:
        for _ in range(50):
            try:
                httpx.get(base + '/')
                break
            except httpx.ConnectError:
                time.sleep(0.2)
        time.sleep(1.0)                      # que arranquen los 3 workers
        pids = set()
        for _ in range(30):
            # conexión nueva cada vez: el SO reparte las conexiones entre workers
            pids.add(httpx.get(base + '/quien-soy', headers={'Connection': 'close'}).json()['pid'])
        print(f'PIDs distintos en 30 pedidos a /quien-soy: {sorted(pids)}')

        r = httpx.post(base + '/tareas', json={'tipo': 'esperar'})
        tid = r.json()['id']
        print(f'Creé la tarea {tid} (la atendió un worker). La pido 15 veces:')
        codigos = [httpx.get(f'{base}/tareas/{tid}', headers={'Connection': 'close'}).status_code
                   for _ in range(15)]
        print(f'  {codigos}')
        print('  → los 404 son de workers que tienen SU propio dict `tareas`, vacío.')
    finally:
        srv.terminate()
        srv.wait()


# ─────────────────────────────────────────────
# Ejercicio 5: medir, con un cuarto caso CPU
# ─────────────────────────────────────────────

def hash_iterado(n=ITER):
    h = b'x'
    for _ in range(n):
        h = hashlib.sha256(h).digest()
    return h.hex()[:8]


def crear_app():
    from contextlib import asynccontextmanager
    from fastapi import FastAPI

    # spawn: los workers no heredan el socket de escucha de uvicorn
    pool = ProcessPoolExecutor(max_workers=PEDIDOS,
                               mp_context=multiprocessing.get_context('spawn'))

    @asynccontextmanager
    async def ciclo_de_vida(_app):
        yield                                  # la app corre acá
        pool.shutdown(cancel_futures=True)     # si no, quedan workers huérfanos

    app = FastAPI(lifespan=ciclo_de_vida)

    @app.get('/async-bien')
    async def async_bien():
        await asyncio.sleep(DEMORA)
        return {'ok': True}

    @app.get('/async-mal')
    async def async_mal():
        time.sleep(DEMORA)
        return {'ok': True}

    @app.get('/sync')
    def sincronico():
        time.sleep(DEMORA)
        return {'ok': True}

    @app.get('/cpu-async')
    async def cpu_async():
        return {'h': hash_iterado()}           # bloquea el loop

    @app.get('/cpu-sync')
    def cpu_sync():
        return {'h': hash_iterado()}           # threadpool, pero el GIL serializa

    @app.get('/cpu-procesos')
    async def cpu_procesos():
        loop = asyncio.get_running_loop()
        return {'h': await loop.run_in_executor(pool, hash_iterado)}

    return app


def levantar():
    import uvicorn
    uvicorn.run(crear_app(), host='127.0.0.1', port=PUERTO_MEDIR, log_level='error')


async def medir_ruta(ruta):
    import httpx
    async with httpx.AsyncClient(timeout=60) as c:
        t0 = time.perf_counter()
        await asyncio.gather(*(c.get(f'http://127.0.0.1:{PUERTO_MEDIR}/{ruta}')
                               for _ in range(PEDIDOS)))
        return time.perf_counter() - t0


def medir():
    import httpx
    p = multiprocessing.Process(target=levantar)     # no daemon: crea hijos (pool)
    p.start()
    for _ in range(50):
        try:
            httpx.get(f'http://127.0.0.1:{PUERTO_MEDIR}/sync', timeout=5)
            break
        except httpx.ConnectError:
            time.sleep(0.2)
    t0 = time.perf_counter()
    hash_iterado()
    un_hash = time.perf_counter() - t0
    print(f'{PEDIDOS} pedidos concurrentes. Espera = {DEMORA}s; un hash = {un_hash:.2f}s\n')
    for ruta in ('async-bien', 'async-mal', 'sync', 'cpu-async', 'cpu-sync', 'cpu-procesos'):
        asyncio.run(medir_ruta(ruta))              # calentar (pool de procesos, etc.)
        print(f'  /{ruta:<13} {asyncio.run(medir_ruta(ruta)):5.2f}s')
    p.terminate()
    p.join()


if __name__ == '__main__':
    modo = sys.argv[1] if len(sys.argv) > 1 else ''
    if modo == 'workers':
        workers()
    elif modo == 'medir':
        medir()
    else:
        print(__doc__)
        sys.exit(1)
