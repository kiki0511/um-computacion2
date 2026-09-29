#!/usr/bin/env python3
"""
Ejercicio 3 (OBLIGATORIO) - pruebas de ej3_api.py.

Usa el TestClient de FastAPI (no hace falta levantar uvicorn) para:
  - Parte B: provocar los cuatro errores y mostrar código + mensaje + loc
  - Parte B.7: mostrar que la validación ocurre ANTES de la función
  - Parte C: PATCH, /estadisticas y el límite de 10 pendientes
  - Parte D: qué pasa sin la anotación : int y con prioridad: str

Uso:
  python3 ej3_probar_api.py
"""
import contextlib
import io
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

import ej3_api

cliente = TestClient(ej3_api.app)


def mostrar(nombre, r):
    cuerpo = r.json() if r.content else None
    if isinstance(cuerpo, dict) and isinstance(cuerpo.get('detail'), list):
        d = cuerpo['detail'][0]
        resumen = f"msg={d['msg']!r} loc={d['loc']}"
    else:
        resumen = json.dumps(cuerpo, ensure_ascii=False)
    print(f'  {nombre:<44} → {r.status_code}  {resumen}')


def reiniciar():
    ej3_api.tareas.clear()
    ej3_api.proximo_id = 0


def parte_b():
    print('=== Parte B: los cuatro errores ===')
    reiniciar()
    salida = io.StringIO()
    with contextlib.redirect_stdout(salida):
        r1 = cliente.get('/tareas/abc')
    mostrar('GET /tareas/abc', r1)
    mostrar('POST {"tipo":"volar"}', cliente.post('/tareas', json={'tipo': 'volar'}))
    mostrar('POST {"tipo":"esperar","prioridad":99}',
            cliente.post('/tareas', json={'tipo': 'esperar', 'prioridad': 99}))
    with contextlib.redirect_stdout(salida):
        r4 = cliente.get('/tareas/999')
    mostrar('GET /tareas/999', r4)

    print('\n=== Parte B.7: ¿la validación corre antes? ===')
    impresos = salida.getvalue().strip().splitlines()
    print(f'  prints de obtener(): {impresos}')
    print('  → con /tareas/abc la función NUNCA se ejecutó (422 antes de entrar);')
    print('    con /tareas/999 sí entró, validó el int, y la función decidió el 404.\n')


def parte_c():
    print('=== Parte C: PATCH, estadísticas y límite ===')
    reiniciar()
    for tipo in ('descargar', 'hashear', 'esperar'):
        cliente.post('/tareas', json={'tipo': tipo})
    mostrar('PATCH /tareas/1 {"estado":"ejecutando"}',
            cliente.patch('/tareas/1', json={'estado': 'ejecutando'}))
    mostrar('PATCH /tareas/2 {"estado":"completada"}',
            cliente.patch('/tareas/2', json={'estado': 'completada'}))
    mostrar('PATCH /tareas/2 {"estado":"volando"}',
            cliente.patch('/tareas/2', json={'estado': 'volando'}))
    mostrar('PATCH /tareas/2 {}', cliente.patch('/tareas/2', json={}))
    mostrar('PATCH /tareas/99 {"estado":"completada"}',
            cliente.patch('/tareas/99', json={'estado': 'completada'}))
    mostrar('GET /estadisticas', cliente.get('/estadisticas'))

    reiniciar()
    codigos = [cliente.post('/tareas', json={'tipo': 'esperar'}).status_code for _ in range(10)]
    print(f'  10 POST seguidos → {codigos}')
    r = cliente.post('/tareas', json={'tipo': 'esperar'})
    mostrar('POST número 11', r)
    print(f'  header Retry-After: {r.headers.get("retry-after")}')
    cliente.patch('/tareas/1', json={'estado': 'completada'})
    mostrar('POST tras completar una', cliente.post('/tareas', json={'tipo': 'esperar'}))
    print()


def parte_d():
    print('=== Parte D: los tipos importan ===')
    app = FastAPI()

    @app.get('/sin-tipo/{tarea_id}')
    async def sin_tipo(tarea_id):
        return {'recibido': tarea_id, 'tipo_python': type(tarea_id).__name__}

    class ConStr(BaseModel):
        prioridad: str

    @app.post('/prioridad-str')
    async def prioridad_str(m: ConStr):
        return {'prioridad': m.prioridad}

    c = TestClient(app)
    mostrar('GET /sin-tipo/abc (sin : int)', c.get('/sin-tipo/abc'))
    mostrar('GET /sin-tipo/5   (sin : int)', c.get('/sin-tipo/5'))
    mostrar('POST prioridad: str con "urgente"', c.post('/prioridad-str', json={'prioridad': 'urgente'}))
    mostrar('POST prioridad: str con 3 (int)', c.post('/prioridad-str', json={'prioridad': 3}))
    print('  → sin anotación todo llega como str y nadie valida; con str la prioridad')
    print('    acepta cualquier texto y ya no hay rango 1..5 que controlar.\n')


if __name__ == '__main__':
    parte_b()
    parte_c()
    parte_d()
