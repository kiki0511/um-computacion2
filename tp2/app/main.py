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

Apagado ordenado (SIGINT / SIGTERM):
    1. Servidor.handle_exit: registra la señal y deja de aceptar tareas.
    2. Uvicorn cierra el socket y espera a que terminen los requests abiertos.
    3. lifespan (parte de apagado): espera con límite a las tareas en curso,
       cancela las que queden, vuelca el estado a JSON y cierra los recursos.
"""

import logging
import multiprocessing
import signal
from concurrent.futures import ProcessPoolExecutor
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, status

from . import config, tareas
from .modelos import Estado, Tarea, TareaIn
from .pool import Pool
from .recursos import recursos
from .registro import Registro, reportar_volcado_previo

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("tp2")

registro = Registro()
pool = Pool(registro, config.N_WORKERS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---------------------------------------------------------------- arranque
    await reportar_volcado_previo(config.DIR_ESTADO)

    recursos.cliente_http = httpx.AsyncClient(
        timeout=config.TIMEOUT_HTTP,
        follow_redirects=True,
        limits=httpx.Limits(max_connections=100),
    )
    # 'spawn' explícito: mismo comportamiento en Linux, macOS y Windows, y
    # evita hacer fork() de un proceso que ya tiene hilos (los de to_thread).
    recursos.executor = ProcessPoolExecutor(
        max_workers=config.N_PROCESOS,
        mp_context=multiprocessing.get_context("spawn"),
    )
    log.info(
        "Executor: %d procesos | USAR_EXECUTOR=%s", config.N_PROCESOS, config.USAR_EXECUTOR
    )
    pool.iniciar()

    yield  # ------------------------------------------- el servidor atiende acá

    # ---------------------------------------------------------------- apagado
    await pool.drenar(config.TIMEOUT_APAGADO)
    await pool.detener()

    ruta = await registro.volcar(config.DIR_ESTADO)
    log.info("Estado volcado en %s (%s)", ruta, registro.totales_por_estado())

    await recursos.cliente_http.aclose()
    # cancel_futures: descarta bloques de hash que nunca arrancaron
    recursos.executor.shutdown(wait=True, cancel_futures=True)
    log.info("Recursos liberados. Chau.")


app = FastAPI(title="Plataforma de Tareas Distribuidas", lifespan=lifespan)


@app.post("/tareas", status_code=status.HTTP_202_ACCEPTED)
async def crear_tarea(entrada: TareaIn) -> dict:
    if not pool.aceptando:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "el servidor se está apagando")
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
    # Si estaba ejecutando, el estado pasa a 'cancelada' recién cuando la
    # subtarea termina de cancelarse (en una vuelta próxima del loop).
    return {"id": tarea_id, "cancelacion": "solicitada"}


@app.get("/estadisticas")
async def estadisticas() -> dict:
    return {
        "por_estado": registro.totales_por_estado(),
        "tiempo_promedio_s": registro.tiempo_promedio(),
        "workers": {"total": pool.n_workers, "ocupados": pool.ocupados},
        "en_cola": pool.cola.qsize(),
        "aceptando": pool.aceptando,
    }


class Servidor(uvicorn.Server):
    """
    Uvicorn instala `handle_exit` como handler de SIGINT y SIGTERM con
    signal.signal(). Lo extendemos para que, en el instante en que llega la
    señal, el pool deje de aceptar tareas. Después uvicorn sigue con su
    apagado normal, que termina disparando la parte final del lifespan.

    Ojo: un handler de signal.signal puede correr entre dos instrucciones
    cualquiera del programa, por eso acá solo se cambia un flag y nada más.
    """

    def handle_exit(self, sig: int, frame) -> None:
        if pool.aceptando:
            log.info("Señal %s recibida: apagado ordenado", signal.Signals(sig).name)
        pool.dejar_de_aceptar()
        super().handle_exit(sig, frame)


# Guarda obligatoria: con 'spawn', cada proceso del executor re-importa este
# módulo. Sin esta guarda, cada hijo volvería a levantar el servidor.
if __name__ == "__main__":
    Servidor(uvicorn.Config(app, host="0.0.0.0", port=config.PUERTO)).run()
