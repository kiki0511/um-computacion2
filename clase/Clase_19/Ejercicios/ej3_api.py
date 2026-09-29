#!/usr/bin/env python3
"""
Ejercicio 3 (OBLIGATORIO): API de tareas con FastAPI.

Extiende ../api.py con:
  PATCH /tareas/{id}      cambia solo el estado (modelo con campos opcionales)
  GET   /estadisticas     cantidad de tareas por estado
  POST  /tareas           rechaza con 503 si ya hay 10 pendientes

Uso:
  pip install -r ../requirements.txt
  python3 ej3_api.py                # http://localhost:8000/docs
  python3 ej3_probar_api.py         # prueba todo sin levantar el servidor
"""
import asyncio
import os
import threading
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

MAX_PENDIENTES = 10

Estado = Literal['pendiente', 'ejecutando', 'completada']

app = FastAPI(title='Tareas', description='Clase 19 - Ejercicio 3 (obligatorio)')

tareas: dict[int, dict] = {}
proximo_id = 0


# ─────────────────────────────────────────────
# Modelos
# ─────────────────────────────────────────────

class TareaNueva(BaseModel):
    tipo: Literal['descargar', 'hashear', 'esperar']
    prioridad: int = Field(default=1, ge=1, le=5, description='1 = más baja, 5 = más alta')


class Tarea(TareaNueva):
    id: int
    estado: Estado = 'pendiente'


class TareaCambio(BaseModel):
    """Para PATCH: todo opcional. Solo se aplica lo que el cliente mandó."""
    estado: Estado | None = None
    prioridad: int | None = Field(default=None, ge=1, le=5)


class Estadisticas(BaseModel):
    total: int
    por_estado: dict[str, int]


# ─────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────

@app.get('/')
async def raiz():
    return {'servicio': 'tareas', 'docs': '/docs'}


@app.get('/tareas', response_model=list[Tarea])
async def listar(estado: Estado | None = Query(default=None),
                 limite: int = Query(default=10, ge=1, le=100)):
    items = list(tareas.values())
    if estado:
        items = [t for t in items if t['estado'] == estado]
    return items[:limite]


@app.post('/tareas', response_model=Tarea, status_code=201)
async def crear(nueva: TareaNueva):
    """
    Si ya hay MAX_PENDIENTES pendientes → 503 Service Unavailable + Retry-After.

    Por qué 503 y no otro:
      - 429 Too Many Requests es por CLIENTE (rate limiting): acá el límite es
        global, de capacidad del servidor, no culpa de quien pide.
      - 409 Conflict es para un choque con el estado del RECURSO pedido
        (p. ej. crear algo que ya existe). No es el caso.
      - 400/422 dirían que el pedido está mal formado, y está perfecto.
      - 503 = "ahora no puedo, probá más tarde": el mismo pedido idéntico va
        a funcionar cuando se liberen pendientes, y Retry-After lo indica.
    """
    global proximo_id
    pendientes = sum(1 for t in tareas.values() if t['estado'] == 'pendiente')
    if pendientes >= MAX_PENDIENTES:
        raise HTTPException(
            status_code=503,
            detail=f'Hay {pendientes} tareas pendientes (máximo {MAX_PENDIENTES}). '
                   'Reintentá más tarde.',
            headers={'Retry-After': '5'},
        )
    proximo_id += 1
    tarea = {'id': proximo_id, **nueva.model_dump(), 'estado': 'pendiente'}
    tareas[proximo_id] = tarea
    return tarea


@app.get('/tareas/{tarea_id}', response_model=Tarea)
async def obtener(tarea_id: int):
    # Este print demuestra que la validación corre ANTES: con /tareas/abc
    # nunca se imprime, FastAPI responde 422 sin entrar a la función.
    print(f'  [obtener] entré con tarea_id={tarea_id!r}')
    if tarea_id not in tareas:
        raise HTTPException(status_code=404, detail='No existe esa tarea')
    return tareas[tarea_id]


@app.patch('/tareas/{tarea_id}', response_model=Tarea)
async def modificar(tarea_id: int, cambio: TareaCambio):
    if tarea_id not in tareas:
        raise HTTPException(status_code=404, detail='No existe esa tarea')
    # exclude_unset: solo los campos que el cliente MANDÓ (no los default None)
    datos = cambio.model_dump(exclude_unset=True)
    if not datos:
        raise HTTPException(status_code=400, detail='No se envió ningún campo para cambiar')
    tareas[tarea_id].update(datos)
    return tareas[tarea_id]


@app.delete('/tareas/{tarea_id}', status_code=204)
async def borrar(tarea_id: int):
    if tarea_id not in tareas:
        raise HTTPException(status_code=404, detail='No existe esa tarea')
    del tareas[tarea_id]


@app.get('/estadisticas', response_model=Estadisticas)
async def estadisticas():
    por_estado = {e: 0 for e in ('pendiente', 'ejecutando', 'completada')}
    for t in tareas.values():
        por_estado[t['estado']] += 1
    return {'total': len(tareas), 'por_estado': por_estado}


@app.get('/quien-soy')
async def quien_soy():
    loop = asyncio.get_running_loop()
    return {'pid': os.getpid(), 'thread': threading.current_thread().name,
            'loop': type(loop).__name__, 'id_del_loop': id(loop)}


@app.get('/quien-soy-sync')
def quien_soy_sync():
    try:
        asyncio.get_running_loop()
        estado = 'HAY loop'
    except RuntimeError:
        estado = 'NO hay loop corriendo acá'
    return {'pid': os.getpid(), 'thread': threading.current_thread().name, 'loop': estado}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8000)
