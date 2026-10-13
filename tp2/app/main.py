"""
API HTTP de la plataforma de tareas distribuidas (FastAPI).

Endpoints:
    POST   /tareas          encola una tarea y responde al instante (202)
    GET    /tareas          lista tareas, filtro opcional ?estado=
    GET    /tareas/{id}     estado y resultado de una tarea
    DELETE /tareas/{id}     cancela una tarea pendiente o en ejecución
    GET    /estadisticas    totales por estado, tiempos promedio, workers ocupados

Ningún endpoint espera a que una tarea termine: solo leen o escriben el
registro en memoria, o ponen algo en la cola. Por eso responden enseguida.
"""

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, status

from . import config, tareas
from .modelos import Estado, Tarea, TareaIn
from .pool import Pool
from .registro import Registro

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("tp2")

registro = Registro()
pool = Pool(registro, config.N_WORKERS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Arranque y apagado. El pool se crea acá porque necesita el event loop corriendo."""
    pool.iniciar()
    yield
    # Semana 2: apagado ordenado (dejar de aceptar, drenar con límite, volcar JSON)
    await pool.detener()


app = FastAPI(title="Plataforma de Tareas Distribuidas", lifespan=lifespan)


@app.post("/tareas", status_code=status.HTTP_202_ACCEPTED)
async def crear_tarea(entrada: TareaIn) -> dict:
    try:
        tareas.validar(entrada.tipo, entrada.parametros)
    except ValueError as e:
        raise HTTPException(422, str(e))

    tarea = Tarea(
        tipo=entrada.tipo,
        parametros=entrada.parametros,
        timeout=entrada.timeout or config.TIMEOUT_DEFAULT,
    )
    pool.encolar(tarea)
    return {"id": tarea.id, "estado": tarea.estado}


@app.get("/tareas")
async def listar_tareas(estado: Estado | None = None) -> list[Tarea]:
    return registro.listar(estado)


@app.get("/tareas/{tarea_id}")
async def obtener_tarea(tarea_id: str) -> Tarea:
    tarea = registro.obtener(tarea_id)
    if tarea is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "tarea inexistente")
    return tarea


@app.delete("/tareas/{tarea_id}")
async def cancelar_tarea(tarea_id: str) -> dict:
    tarea = registro.obtener(tarea_id)
    if tarea is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "tarea inexistente")
    if not pool.cancelar(tarea_id):
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"la tarea ya terminó ({tarea.estado.value})"
        )
    # Si estaba ejecutando, el estado pasa a 'cancelada' recién cuando el worker
    # procesa el CancelledError (en el próximo ciclo del loop), no en esta línea.
    return {"id": tarea_id, "cancelacion": "solicitada"}


@app.get("/estadisticas")
async def estadisticas() -> dict:
    return {
        "por_estado": registro.totales_por_estado(),
        "tiempo_promedio_s": registro.tiempo_promedio(),
        "workers": {"total": pool.n_workers, "ocupados": pool.ocupados},
        "en_cola": pool.cola.qsize(),
    }


# Guarda obligatoria: en macOS/Windows el ProcessPoolExecutor (semana 2) usa
# 'spawn' y re-importa este módulo en cada proceso hijo. Sin esta guarda, cada
# hijo volvería a levantar el servidor.
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=config.PUERTO)
