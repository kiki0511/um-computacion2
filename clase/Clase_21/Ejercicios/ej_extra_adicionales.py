#!/usr/bin/env python3
"""
Ejercicios adicionales de la Clase 21, juntos en una API:

  1. Workers con reintentos: backoff exponencial, hasta MAX_REINTENTOS.
     El contador de intentos viaja DENTRO de la tarea (no en el worker:
     el reintento lo puede tomar cualquier otro).
  2. GET /estadisticas: tareas por estado, tamaño de la cola, workers
     ocupados y tiempo promedio de procesamiento.
  3. Cola con prioridad SIN inanición: la clave de orden es un "plazo"
     = llegada + (5 - prioridad) * ENVEJECIMIENTO. Una tarea de prioridad
     alta adelanta a una baja, pero solo hasta ENVEJECIMIENTO segundos por
     nivel: pasado ese tiempo, la baja va primero que las altas nuevas.
  4. Atraso del event loop medido en vivo (como executor.py) y expuesto
     en /estadisticas.

Tipos de tarea:
  esperar    {"segundos": 1}       I/O simulado
  inestable  {"fallas": 2}         falla las primeras N veces (para reintentos)
  bloquear   {"segundos": 0.5}     time.sleep EN el loop, MAL a propósito:
                                   sirve para ver subir el atraso del loop

Uso:
  pip install fastapi uvicorn httpx
  python3 ej_extra_adicionales.py            # servidor en localhost:8000
  python3 ej_extra_adicionales.py --probar   # demuestra los cuatro puntos
"""
import asyncio
import collections
import itertools
import os
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

N_WORKERS = int(os.environ.get('WORKERS', 4))
MAX_REINTENTOS = 3
BACKOFF_BASE = 0.2                         # 0.2, 0.4, 0.8 s ...
ENVEJECIMIENTO = float(os.environ.get('ENVEJECIMIENTO', 1.0))   # s por nivel
LATIDO = 0.05

tareas: dict[int, dict] = {}
ids = itertools.count(1)
desempate = itertools.count()              # para que la PriorityQueue no compare dicts
ocupados: set[int] = set()                 # ids de workers trabajando
atrasos = collections.deque(maxlen=200)    # últimos atrasos del loop, en ms
de_fondo: set[asyncio.Task] = set()        # referencias a las tareas sueltas (ver nota)


class TareaNueva(BaseModel):
    tipo: Literal['esperar', 'inestable', 'bloquear']
    prioridad: int = Field(default=3, ge=1, le=5, description='5 = más alta')
    parametros: dict = {}


# ─────────────────────────────────────────────
# 3. Prioridad con envejecimiento
# ─────────────────────────────────────────────

def clave(tarea: dict) -> float:
    """Menor clave = sale antes. Usa la llegada ORIGINAL, así un reintento no
    pierde su lugar: ya esperó, ya 'envejeció'."""
    return tarea['creada'] + (5 - tarea['prioridad']) * ENVEJECIMIENTO


def encolar(cola: asyncio.PriorityQueue, tarea: dict):
    cola.put_nowait((clave(tarea), next(desempate), tarea['id']))


# ─────────────────────────────────────────────
# Ejecución
# ─────────────────────────────────────────────

async def ejecutar(tarea: dict):
    p = tarea['parametros']
    if tarea['tipo'] == 'esperar':
        await asyncio.sleep(float(p.get('segundos', 1)))
        return 'ok'
    if tarea['tipo'] == 'inestable':
        if tarea['intentos'] <= int(p.get('fallas', 1)):
            raise ConnectionError(f'falla simulada en el intento {tarea["intentos"]}')
        return f'salió en el intento {tarea["intentos"]}'
    if tarea['tipo'] == 'bloquear':
        time.sleep(float(p.get('segundos', 0.5)))     # BUG a propósito
        return 'bloqueé el loop'


# ─────────────────────────────────────────────
# 1. Reintentos con backoff exponencial
# ─────────────────────────────────────────────

async def reencolar_despues(cola, tarea, espera):
    await asyncio.sleep(espera)
    tarea['estado'] = 'pendiente'
    encolar(cola, tarea)


def programar_reintento(cola, tarea, error):
    espera = BACKOFF_BASE * 2 ** (tarea['intentos'] - 1)
    tarea.update(estado='reintentando', error=error, proximo_intento_en=espera)
    # NO se duerme en el worker: quedaría ocupado sin hacer nada.
    # Una tarea de fondo espera y la vuelve a meter en la cola.
    t = asyncio.create_task(reencolar_despues(cola, tarea, espera))
    de_fondo.add(t)                   # el loop guarda solo una referencia DÉBIL:
    t.add_done_callback(de_fondo.discard)   # sin esto el GC la puede borrar


async def worker(wid: int, cola: asyncio.PriorityQueue):
    while True:
        _, _, tid = await cola.get()
        tarea = tareas[tid]
        ocupados.add(wid)
        try:
            tarea['intentos'] += 1
            tarea.update(estado='ejecutando', inicio=time.time())
            tarea['historial'].append(round(time.time() - tarea['creada'], 2))
            try:
                tarea['resultado'] = await ejecutar(tarea)
                tarea.update(estado='completada', fin=time.time())
            except Exception as e:
                error = f'{type(e).__name__}: {e}'
                if tarea['intentos'] <= MAX_REINTENTOS:
                    programar_reintento(cola, tarea, error)
                else:
                    tarea.update(estado='fallida', error=error, fin=time.time())
        finally:
            ocupados.discard(wid)
            cola.task_done()


# ─────────────────────────────────────────────
# 4. Medidor del atraso del loop
# ─────────────────────────────────────────────

async def medidor_loop():
    while True:
        t0 = time.perf_counter()
        await asyncio.sleep(LATIDO)
        atrasos.append((time.perf_counter() - t0 - LATIDO) * 1000)


@asynccontextmanager
async def ciclo(app: FastAPI):
    app.state.cola = asyncio.PriorityQueue(maxsize=1000)
    app.state.fondo = [asyncio.create_task(worker(i, app.state.cola))
                       for i in range(N_WORKERS)]
    app.state.fondo.append(asyncio.create_task(medidor_loop()))
    yield
    for t in [*app.state.fondo, *de_fondo]:
        t.cancel()
    await asyncio.gather(*app.state.fondo, *de_fondo, return_exceptions=True)


app = FastAPI(title='Tareas: adicionales de la clase 21', lifespan=ciclo)


@app.post('/tareas', status_code=202)
async def crear(nueva: TareaNueva, request: Request):
    tid = next(ids)
    tarea = {'id': tid, **nueva.model_dump(), 'estado': 'pendiente',
             'creada': time.time(), 'intentos': 0, 'historial': []}
    try:
        encolar(request.app.state.cola, tarea)
    except asyncio.QueueFull:
        raise HTTPException(503, 'Cola llena', headers={'Retry-After': '5'})
    tareas[tid] = tarea
    return tarea


@app.get('/tareas/{tid}')
async def obtener(tid: int):
    if tid not in tareas:
        raise HTTPException(404, 'No existe esa tarea')
    return tareas[tid]


# ─────────────────────────────────────────────
# 2. Estadísticas en vivo
# ─────────────────────────────────────────────

@app.get('/estadisticas')
async def estadisticas(request: Request):
    por_estado = collections.Counter(t['estado'] for t in tareas.values())
    duraciones = [t['fin'] - t['inicio'] for t in tareas.values()
                  if t['estado'] == 'completada']
    recientes = list(atrasos)[-20:]                 # último segundo, aprox.
    return {
        'por_estado': dict(por_estado),
        'en_cola': request.app.state.cola.qsize(),
        'workers_ocupados': f'{len(ocupados)}/{N_WORKERS}',
        'tiempo_promedio_s': round(sum(duraciones) / len(duraciones), 3) if duraciones else None,
        'atraso_loop_ms': {
            'ultimo': round(atrasos[-1], 1) if atrasos else None,
            'max_ultimo_segundo': round(max(recientes), 1) if recientes else None,
            'max_historico': round(max(atrasos), 1) if atrasos else None,
        },
    }


# ─────────────────────────────────────────────
# --probar
# ─────────────────────────────────────────────

class Servidor:
    """Levanta esta misma API con uvicorn en otro proceso, con el entorno dado."""
    def __init__(self, puerto, **entorno):
        import httpx
        os.environ.setdefault('NO_PROXY', '127.0.0.1,localhost')
        env = {**os.environ, **entorno}
        self.srv = subprocess.Popen(
            [sys.executable, '-m', 'uvicorn', 'ej_extra_adicionales:app',
             '--port', str(puerto), '--log-level', 'warning'],
            cwd=os.path.dirname(os.path.abspath(__file__)), env=env)
        self.c = httpx.Client(base_url=f'http://127.0.0.1:{puerto}', timeout=30)
        for _ in range(100):
            try:
                self.c.get('/estadisticas')
                break
            except httpx.HTTPError:
                time.sleep(0.1)

    def post(self, tipo, prioridad=3, **params):
        return self.c.post('/tareas', json={'tipo': tipo, 'prioridad': prioridad,
                                            'parametros': params}).json()['id']

    def tarea(self, tid):
        return self.c.get(f'/tareas/{tid}').json()

    def esperar_fin(self, tids):
        while any(self.tarea(t)['estado'] not in ('completada', 'fallida') for t in tids):
            time.sleep(0.1)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.c.close()
        self.srv.terminate()
        self.srv.wait()


def demo_prioridad(envejecimiento):
    with Servidor(8026, WORKERS='1', ENVEJECIMIENTO=str(envejecimiento)) as s:
        s.post('esperar', prioridad=5, segundos=0.3)      # ocupa al único worker
        baja = s.post('esperar', prioridad=1, segundos=0.2)
        altas = []
        for _ in range(15):
            altas.append(s.post('esperar', prioridad=5, segundos=0.2))
            time.sleep(0.1)
        s.esperar_fin([baja, *altas])
        orden = sorted([baja, *altas], key=lambda t: s.tarea(t)['inicio'])
        return orden.index(baja) + 1


def probar():
    print('=== 3. Prioridad con envejecimiento (1 worker) ===')
    print('  Una tarea de prioridad 1 y después 15 de prioridad 5, una cada 0.1 s.')
    print('  Cada una tarda 0.2 s: llegan más rápido de lo que se atienden.')
    for env, nombre in ((1000, 'sin envejecimiento (1000 s/nivel)'),
                        (0.25, 'con envejecimiento (0.25 s/nivel)')):
        pos = demo_prioridad(env)
        print(f'  {nombre:<36} la de prioridad 1 salió {pos}ª de 16')
    print('  -> sin envejecimiento sale última: si las altas no paran, no sale nunca\n')

    with Servidor(8027, WORKERS='1') as s:
        print('=== 1. Reintentos con backoff (máximo 3, base 0.2 s) ===')
        ok = s.post('inestable', fallas=2)
        mal = s.post('inestable', fallas=9)
        s.esperar_fin([ok, mal])
        for tid in (ok, mal):
            t = s.tarea(tid)
            print(f'  {t["parametros"]}: {t["estado"]} en {t["intentos"]} intentos, '
                  f'arrancó a los {t["historial"]} s')
            if t['estado'] == 'fallida':
                print(f'      error final: {t["error"]}')
        print('  (las distancias entre intentos crecen: 0.2, 0.4, 0.8 s)\n')

        print('=== 2 y 4. Estadísticas y atraso del loop ===')
        time.sleep(1.2)
        e = s.c.get('/estadisticas').json()
        print(f'  en reposo:             atraso máx. último segundo = '
              f'{e["atraso_loop_ms"]["max_ultimo_segundo"]} ms')
        s.post('bloquear', segundos=0.5)
        time.sleep(0.8)
        e = s.c.get('/estadisticas').json()
        print(f'  después de "bloquear": atraso máx. último segundo = '
              f'{e["atraso_loop_ms"]["max_ultimo_segundo"]} ms  <- se ve el time.sleep')
        print(f'  GET /estadisticas -> {e}')


if __name__ == '__main__':
    if '--probar' in sys.argv:
        probar()
    else:
        import uvicorn
        uvicorn.run(app, host='127.0.0.1', port=8000)
