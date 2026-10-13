#!/usr/bin/env python3
"""
Ejercicio 5: El esqueleto del TP2.

Parte de api.py de la clase 19 y agrega, en el lifespan:
  - una asyncio.Queue con maxsize (backpressure: si está llena, 503)
  - un ProcessPoolExecutor (creado UNA vez) para lo CPU-bound
  - N workers (corrutinas) que consumen la cola

Flujo de una tarea:
  POST /tareas ──> tareas[id] = pendiente ──> cola.put_nowait(id) ──> 202 al toque
                                                   │
  worker: cola.get() ──> ejecutando ──> esperar: asyncio.sleep en el loop
                                    └─> hashear: run_in_executor (otro proceso)
                     ──> completada / fallida / cancelada

Lo que el ejercicio pide (puntos 1 a 8) está todo. Lo que NO está, porque es
el resto del TP2: descargar, timeouts, estadísticas, volcado a JSON y mediciones.

Uso:
  pip install fastapi uvicorn httpx
  python3 ej5_esqueleto_tp2.py            # servidor en localhost:8000 (ver /docs)
  python3 ej5_esqueleto_tp2.py --probar   # levanta el server y recorre todos los casos

  curl -X POST localhost:8000/tareas -H 'Content-Type: application/json' \\
       -d '{"tipo": "esperar", "parametros": {"segundos": 10}}'
  curl localhost:8000/tareas/1
  curl -X DELETE localhost:8000/tareas/1
"""
import asyncio
import hashlib
import logging
import os
import signal
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel

N_WORKERS = int(os.environ.get('WORKERS', 4))
MAXSIZE = int(os.environ.get('MAXSIZE', 100))
LIMITE_APAGADO = 10           # segundos que se espera a las tareas en curso
CENTINELA = None              # None no puede ser un id válido: sirve de centinela

log = logging.getLogger('tareas')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s',
                    datefmt='%H:%M:%S')
logging.getLogger('httpx').setLevel(logging.WARNING)     # que no ensucie --probar


# ─────────────────────────────────────────────
# Trabajo CPU-bound: nivel de módulo para que viaje pickleado al proceso hijo
# ─────────────────────────────────────────────

def hashear(texto: str, iteraciones: int) -> str:
    h = texto.encode()
    for _ in range(iteraciones):
        h = hashlib.sha256(h).digest()
    return h.hex()


# ─────────────────────────────────────────────
# Estado en memoria
# ─────────────────────────────────────────────
# Sin Lock: todo esto se toca desde UN solo thread (el del event loop) y
# nunca hay un await entre leer y escribir un mismo campo.

tareas: dict[int, dict] = {}                   # id -> datos de la tarea
en_curso: dict[int, asyncio.Task] = {}         # id -> Task que la ejecuta
terminadas: dict[int, asyncio.Event] = {}      # id -> Event que se setea al final
proximo_id = 0


class TareaNueva(BaseModel):
    tipo: Literal['hashear', 'esperar']
    parametros: dict = {}     # hashear: texto, iteraciones | esperar: segundos


# ─────────────────────────────────────────────
# Ejecución
# ─────────────────────────────────────────────

async def ejecutar(tarea: dict, pool: ProcessPoolExecutor):
    p = tarea['parametros']
    if tarea['tipo'] == 'esperar':
        # I/O simulado: directo en el loop, cede el control mientras duerme
        segundos = float(p.get('segundos', 1))
        await asyncio.sleep(segundos)
        return {'durmio': segundos}

    if tarea['tipo'] == 'hashear':
        # CPU-bound: al executor. Si lo llamara directo, congela el loop (ej. 3)
        texto = str(p.get('texto', 'hola'))
        iteraciones = int(p.get('iteraciones', 1_000_000))
        loop = asyncio.get_running_loop()
        return {'hash': await loop.run_in_executor(pool, hashear, texto, iteraciones)}

    raise ValueError(f'tipo desconocido: {tarea["tipo"]}')


def cerrar(tarea: dict, estado: str, **datos):
    tarea.update(estado=estado, fin=time.time(), **datos)
    terminadas[tarea['id']].set()


async def worker(wid: int, cola: asyncio.Queue, pool: ProcessPoolExecutor):
    log.info('worker %d listo', wid)
    while True:
        tid = await cola.get()
        try:
            if tid is CENTINELA:
                log.info('worker %d se retira', wid)
                return                                  # el finally hace task_done

            tarea = tareas[tid]
            if tarea['estado'] == 'cancelada':          # la cancelaron en la cola
                continue

            # Estos dos pasos van juntos, sin await en el medio: así un DELETE
            # nunca ve 'ejecutando' sin la Task registrada en en_curso.
            tarea.update(estado='ejecutando', inicio=time.time(), worker=wid)
            ejecucion = asyncio.create_task(ejecutar(tarea, pool))
            en_curso[tid] = ejecucion

            try:
                # asyncio.wait NO propaga la cancelación de 'ejecucion' (la del
                # DELETE): así distinguimos "cancelaron la tarea" de "cancelaron
                # al worker" (apagado forzado), que sí llega acá como excepción.
                await asyncio.wait({ejecucion})
            except asyncio.CancelledError:
                ejecucion.cancel()
                await asyncio.gather(ejecucion, return_exceptions=True)
                cerrar(tarea, 'cancelada', error='apagado del servidor')
                raise
            finally:
                en_curso.pop(tid, None)

            if ejecucion.cancelled():
                cerrar(tarea, 'cancelada', error='cancelada por el usuario')
            elif ejecucion.exception() is not None:
                e = ejecucion.exception()
                cerrar(tarea, 'fallida', error=f'{type(e).__name__}: {e}')
            else:
                cerrar(tarea, 'completada', resultado=ejecucion.result())
            log.info('worker %d: tarea %d -> %s', wid, tid, tarea['estado'])

        except asyncio.CancelledError:
            raise
        except Exception:
            # Cualquier error NUESTRO (un bug) no tiene que matar al worker:
            # si muere, la cola se queda con un consumidor menos para siempre.
            log.exception('worker %d: error inesperado con la tarea %s', wid, tid)
        finally:
            cola.task_done()


# ─────────────────────────────────────────────
# Arranque y apagado
# ─────────────────────────────────────────────

@asynccontextmanager
async def ciclo(app: FastAPI):
    app.state.cerrando = False
    app.state.cola = asyncio.Queue(maxsize=MAXSIZE)
    app.state.pool = ProcessPoolExecutor(max_workers=2)
    app.state.workers = [asyncio.create_task(worker(i, app.state.cola, app.state.pool))
                         for i in range(N_WORKERS)]
    log.info('%d workers, cola con maxsize=%d', N_WORKERS, MAXSIZE)

    yield                                   # acá la API atiende pedidos

    # uvicorn llega acá con Ctrl+C o SIGTERM (instala sus propios handlers)
    log.info('apagando: no se aceptan tareas nuevas')
    app.state.cerrando = True
    cola = app.state.cola

    # 1. Lo que todavía no arrancó se cancela (no tiene sentido empezarlo ahora)
    while not cola.empty():
        tid = cola.get_nowait()
        cerrar(tareas[tid], 'cancelada', error='apagado del servidor')
        cola.task_done()

    # 2. Un centinela por worker: terminan la tarea en curso y salen solos
    for _ in app.state.workers:
        await cola.put(CENTINELA)
    _, siguen = await asyncio.wait(app.state.workers, timeout=LIMITE_APAGADO)

    # 3. Si alguno no terminó a tiempo, se lo cancela (su tarea queda 'cancelada')
    for w in siguen:
        w.cancel()
    await asyncio.gather(*app.state.workers, return_exceptions=True)
    if siguen:
        log.info('%d workers cancelados por superar %d s', len(siguen), LIMITE_APAGADO)

    # 4. shutdown(wait=True) bloquea: se hace en un thread para no congelar el loop
    await asyncio.to_thread(app.state.pool.shutdown, wait=True, cancel_futures=True)
    log.info('apagado ordenado completo')


app = FastAPI(title='Plataforma de tareas (esqueleto)', lifespan=ciclo)


# ─────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────

@app.post('/tareas', status_code=202)
async def crear(nueva: TareaNueva, request: Request):
    """202 Accepted: 'lo recibí, todavía no lo hice'. Responde al instante."""
    global proximo_id
    if request.app.state.cerrando:
        raise HTTPException(503, 'El servidor se está apagando')

    proximo_id += 1
    tarea = {'id': proximo_id, **nueva.model_dump(), 'estado': 'pendiente',
             'creada': time.time()}
    try:
        request.app.state.cola.put_nowait(proximo_id)   # NO await put(): no esperar
    except asyncio.QueueFull:
        raise HTTPException(503, 'Cola llena, probá más tarde',
                            headers={'Retry-After': '5'})
    tareas[proximo_id] = tarea
    terminadas[proximo_id] = asyncio.Event()
    return tarea


@app.get('/tareas')
async def listar(estado: str | None = Query(default=None)):
    return [t for t in tareas.values() if estado is None or t['estado'] == estado]


@app.get('/tareas/{tid}')
async def obtener(tid: int):
    if tid not in tareas:
        raise HTTPException(404, 'No existe esa tarea')
    return tareas[tid]


@app.delete('/tareas/{tid}')
async def cancelar(tid: int):
    if tid not in tareas:
        raise HTTPException(404, 'No existe esa tarea')
    tarea = tareas[tid]

    if tarea['estado'] == 'pendiente':
        # Sigue en la cola: se marca y el worker la saltea cuando la saque
        cerrar(tarea, 'cancelada', error='cancelada por el usuario')
    elif tarea['estado'] == 'ejecutando':
        en_curso[tid].cancel()
        # Esperar a que el worker registre la cancelación, para responder
        # con el estado final y no con 'ejecutando'
        await asyncio.wait_for(terminadas[tid].wait(), timeout=5)
    else:
        raise HTTPException(409, f'La tarea ya está {tarea["estado"]}')
    return tarea


# ─────────────────────────────────────────────
# --probar: recorre los casos contra un servidor real
# ─────────────────────────────────────────────

def puerto_libre():
    """Pide al sistema un puerto libre (bind al puerto 0) y lo devuelve.
    Así --medir/--probar no chocan con otro servidor que ya esté escuchando."""
    import socket
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def probar():
    import httpx
    puerto = puerto_libre()
    os.environ.setdefault('NO_PROXY', '127.0.0.1,localhost')
    env = {**os.environ, 'WORKERS': '3'}
    srv = subprocess.Popen(
        [sys.executable, '-m', 'uvicorn', 'ej5_esqueleto_tp2:app', '--port', str(puerto),
         '--log-level', 'warning'],
        cwd=os.path.dirname(os.path.abspath(__file__)), env=env)
    c = httpx.Client(base_url=f'http://127.0.0.1:{puerto}', timeout=30)
    try:
        for _ in range(100):
            if srv.poll() is not None:
                raise RuntimeError('uvicorn terminó al arrancar (ver el error de arriba)')
            try:
                c.get('/tareas')
                break
            except httpx.HTTPError:
                time.sleep(0.1)

        print('\n=== 1. POST responde al instante (3 workers) ===')
        pedidos = [
            ('esperar', {'segundos': 1}),                         # 1 completa
            ('hashear', {'texto': 'tp2', 'iteraciones': 2_000_000}),  # 2 executor
            ('esperar', {'segundos': 30}),                        # 3 se cancela corriendo
            ('esperar', {'segundos': 30}),                        # 4 se cancela en la cola
            ('hashear', {'iteraciones': 'muchas'}),               # 5 falla
        ]
        for tipo, params in pedidos:
            t0 = time.perf_counter()
            r = c.post('/tareas', json={'tipo': tipo, 'parametros': params})
            ms = (time.perf_counter() - t0) * 1000
            print(f'  POST {tipo:<8} {str(params):<44} -> {r.status_code} '
                  f'id={r.json()["id"]} en {ms:5.1f} ms')

        time.sleep(0.3)
        print('\n=== 2. GET mientras corren ===')
        for t in c.get('/tareas').json():
            print(f'  tarea {t["id"]}: {t["estado"]}')

        # Primero la 4: si cancelara antes la 3, ese worker se libera y la 4 arranca
        print('\n=== 3. DELETE de la 4 (pendiente) y de la 3 (ejecutando) ===')
        for tid in (4, 3):
            r = c.delete(f'/tareas/{tid}')
            print(f'  DELETE /tareas/{tid} -> {r.status_code} {r.json()["estado"]}: '
                  f'{r.json().get("error")}')
        r = c.delete('/tareas/3')
        print(f'  DELETE /tareas/3 otra vez -> {r.status_code} {r.json()["detail"]}')

        print('\n=== 4. Estado final ===')
        while c.get('/tareas', params={'estado': 'ejecutando'}).json() or \
                c.get('/tareas', params={'estado': 'pendiente'}).json():
            time.sleep(0.2)
        for t in c.get('/tareas').json():
            extra = t.get('error') or t.get('resultado')
            dur = f'{t["fin"] - t["inicio"]:.2f}s' if 'inicio' in t else '-'
            print(f'  tarea {t["id"]} {t["tipo"]:<8} {t["estado"]:<11} {dur:>6}  {extra}')

        print('\n=== 5. Apagado ordenado con una tarea en curso (SIGTERM) ===')
        c.post('/tareas', json={'tipo': 'esperar', 'parametros': {'segundos': 1}})
        time.sleep(0.2)
        t0 = time.perf_counter()
        srv.send_signal(signal.SIGTERM)
        srv.wait(timeout=20)
        print(f'  el servidor terminó en {time.perf_counter() - t0:.2f}s, después de '
              f'esperar a la tarea en curso')
        print(f'  código de salida {srv.returncode}: uvicorn re-emite la SIGTERM al '
              f'final del apagado (-15 = terminado por la señal 15)')
    finally:
        c.close()
        if srv.poll() is None:
            srv.terminate()
            srv.wait()


if __name__ == '__main__':
    # Guarda obligatoria en macOS: el ProcessPoolExecutor usa 'spawn' y
    # re-importa este archivo en cada proceso hijo.
    if '--probar' in sys.argv:
        probar()
    else:
        import uvicorn
        uvicorn.run(app, host='127.0.0.1', port=8000)
