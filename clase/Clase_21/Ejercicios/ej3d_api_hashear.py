#!/usr/bin/env python3
"""
Ejercicio 3, Parte D (OBLIGATORIO): la medición 2 del TP2 en una API real.

Parte de api.py de la clase 19 (GET /tareas con datos en memoria) y agrega:
  POST /hashear          → async def que calcula ADENTRO del loop (lo bloquea)
  POST /hashear-executor → run_in_executor con un ProcessPoolExecutor creado
                           una sola vez en el lifespan
  POST /hashear-sync     → def común (FastAPI lo manda a su threadpool).
                           No lo pide el ejercicio: está para comparar

Uso:
  pip install fastapi uvicorn httpx

  # Modo automático: levanta el servidor, mide y muestra la tabla
  python3 ej3d_api_hashear.py --medir

  # Modo manual (lo que pide el enunciado, con dos terminales):
  python3 ej3d_api_hashear.py
  # terminal 2:
  curl -X POST 'localhost:8000/hashear?vueltas=3000000' &
  sleep 0.5; curl -o /dev/null -s -w 'GET /tareas: %{time_total}s\\n' localhost:8000/tareas
"""
import asyncio
import hashlib
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

PUERTO = 8021                 # --medir lo reemplaza por uno libre
VUELTAS = 3_000_000


def hashear(vueltas):
    """CPU-bound puro. Nivel de módulo: tiene que poder viajar al proceso hijo."""
    h = b'x'
    for _ in range(vueltas):
        h = hashlib.sha256(h).digest()
    return h.hex()[:16]


@asynccontextmanager
async def ciclo(app):
    # El pool se crea UNA vez al arrancar (crear procesos es caro, ver parte C)
    app.state.pool = ProcessPoolExecutor(max_workers=2)
    yield
    app.state.pool.shutdown(wait=True, cancel_futures=True)


app = FastAPI(title='Medición 2 del TP2', lifespan=ciclo)

# Algunas tareas de mentira para que GET /tareas devuelva algo
tareas = {i: {'id': i, 'tipo': 'esperar', 'estado': 'pendiente'} for i in range(1, 6)}


@app.get('/tareas')
async def listar():
    return list(tareas.values())


@app.post('/hashear')
async def hashear_bloqueante(vueltas: int = VUELTAS):
    """MAL: async def que calcula sin await. Mientras corre, el loop no
    atiende a NADIE más (ni el GET de otra terminal)."""
    t0 = time.perf_counter()
    resultado = hashear(vueltas)
    return {'modo': 'sin executor', 'hash': resultado,
            'segundos': round(time.perf_counter() - t0, 2)}


@app.post('/hashear-executor')
async def hashear_executor(request: Request, vueltas: int = VUELTAS):
    """BIEN: el cálculo va a otro proceso; el loop solo espera el Future."""
    loop = asyncio.get_running_loop()
    t0 = time.perf_counter()
    resultado = await loop.run_in_executor(request.app.state.pool, hashear, vueltas)
    return {'modo': 'ProcessPoolExecutor', 'hash': resultado,
            'segundos': round(time.perf_counter() - t0, 2)}


@app.post('/hashear-sync')
def hashear_sync(vueltas: int = VUELTAS):
    """def común: FastAPI lo corre en un thread de su pool. No congela el loop,
    pero comparte el GIL con él (el loop recibe turnos cada ~5 ms)."""
    t0 = time.perf_counter()
    resultado = hashear(vueltas)
    return {'modo': 'def (threadpool)', 'hash': resultado,
            'segundos': round(time.perf_counter() - t0, 2)}


# ─────────────────────────────────────────────
# Modo --medir: levanta el server en otro proceso y mide desde afuera
# ─────────────────────────────────────────────

async def medir_ruta(cliente, ruta, vueltas):
    """Lanza el POST pesado y, mientras corre, hace GET /tareas cada 100 ms."""
    pesado = asyncio.create_task(cliente.post(ruta, params={'vueltas': vueltas},
                                              timeout=120))
    await asyncio.sleep(0.3)                       # que el cálculo ya esté corriendo
    tiempos = []
    while not pesado.done():
        t0 = time.perf_counter()
        await cliente.get('/tareas', timeout=120)
        tiempos.append(time.perf_counter() - t0)
        await asyncio.sleep(0.1)
    r = (await pesado).json()
    return r['segundos'], max(tiempos, default=0.0), len(tiempos)


async def medir(vueltas):
    import httpx
    base = f'http://127.0.0.1:{PUERTO}'
    async with httpx.AsyncClient(base_url=base) as cliente:
        # Línea de base: el GET sin nada pesado corriendo
        await cliente.get('/tareas')
        t0 = time.perf_counter()
        for _ in range(10):
            await cliente.get('/tareas')
        base_ms = (time.perf_counter() - t0) / 10 * 1000
        print(f'  GET /tareas en reposo: {base_ms:.1f} ms\n')

        print(f'  {"endpoint":<20} {"cálculo":>8} {"peor GET /tareas":>17} {"GETs":>5}')
        filas = []
        for ruta in ('/hashear', '/hashear-executor', '/hashear-sync'):
            seg, peor, n = await medir_ruta(cliente, ruta, vueltas)
            print(f'  {ruta:<20} {seg:7.2f}s {peor * 1000:14.1f} ms {n:>5}')
            filas.append((ruta, seg, peor))

    print('\n=== Para pegar en respuestas.md ===\n')
    print(f'GET /tareas en reposo: {base_ms:.1f} ms\n')
    print('| Endpoint | Duración del cálculo | Peor GET /tareas durante el cálculo |')
    print('|----------|----------------------|-------------------------------------|')
    for ruta, seg, peor in filas:
        print(f'| `{ruta}` | {seg:.2f} s | {peor * 1000:.1f} ms |')


def esperar_servidor(srv):
    import httpx
    for _ in range(100):
        if srv.poll() is not None:
            raise RuntimeError('uvicorn terminó al arrancar (ver el error de arriba)')
        try:
            httpx.get(f'http://127.0.0.1:{PUERTO}/tareas', timeout=0.5)
            return
        except httpx.HTTPError:
            time.sleep(0.1)
    raise RuntimeError('el servidor no levantó')

def puerto_libre():
    """Pide al sistema un puerto libre (bind al puerto 0) y lo devuelve.
    Así --medir/--probar no chocan con otro servidor que ya esté escuchando."""
    import socket
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def main():
    import uvicorn
    args = sys.argv[1:]
    vueltas = int(args[args.index('--vueltas') + 1]) if '--vueltas' in args else VUELTAS

    if '--medir' not in args:
        uvicorn.run(app, host='127.0.0.1', port=8000)
        return

    global PUERTO
    PUERTO = puerto_libre()
    os.environ.setdefault('NO_PROXY', '127.0.0.1,localhost')
    print(f'=== Parte D: medición 2 del TP2 ({vueltas:,} vueltas) ===\n')
    srv = subprocess.Popen(
        [sys.executable, '-m', 'uvicorn', 'ej3d_api_hashear:app',
         '--host', '127.0.0.1', '--port', str(PUERTO), '--log-level', 'warning'],
        cwd=os.path.dirname(os.path.abspath(__file__)))
    try:
        esperar_servidor(srv)
        asyncio.run(medir(vueltas))
    finally:
        srv.terminate()
        srv.wait()


if __name__ == '__main__':
    # Sin esta guarda, en macOS (spawn) cada proceso del pool volvería a
    # ejecutar main() al importar el módulo.
    main()
