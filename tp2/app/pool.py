"""
Pool de workers: N corrutinas que consumen ids de tarea de una asyncio.Queue.

Patrón productor-consumidor (clase 11), pero con corrutinas en vez de threads:
- Productor: el endpoint POST /tareas, que hace `encolar()`.
- Consumidores: los N workers, que hacen `await cola.get()`.

No hace falta Lock: los workers corren todos en el mismo hilo (el del event
loop) y solo se ceden el control en los `await`. Entre un `await` y el
siguiente, ningún otro worker puede tocar el estado compartido.

Cancelación de una tarea en ejecución: el worker NO ejecuta la tarea
directamente, sino que la envuelve en su propia asyncio.Task (`subtarea`).
Así el DELETE puede cancelar esa subtarea sin matar al worker, que sigue
vivo para la próxima tarea.
"""

import asyncio
import logging

from . import tareas
from .modelos import ESTADOS_FINALES, Estado, Tarea, ahora
from .registro import Registro

log = logging.getLogger(__name__)


class Pool:
    def __init__(self, registro: Registro, n_workers: int) -> None:
        self.registro = registro
        self.n_workers = n_workers
        self.cola: asyncio.Queue[str] = asyncio.Queue()
        self._workers: list[asyncio.Task] = []
        # id de tarea -> subtarea que la está ejecutando ahora
        self.en_curso: dict[str, asyncio.Task] = {}

    # ---------------------------------------------------------------- ciclo de vida

    def iniciar(self) -> None:
        """Lanza los N workers. Tiene que llamarse con el event loop corriendo."""
        for i in range(self.n_workers):
            w = asyncio.create_task(self._worker(i), name=f"worker-{i}")
            self._workers.append(w)
        log.info("Pool iniciado con %d workers", self.n_workers)

    async def detener(self) -> None:
        """Cancela los workers y espera a que terminen (sin corrutinas huérfanas)."""
        for w in self._workers:
            w.cancel()
        # gather con return_exceptions para que un CancelledError no corte la espera
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        log.info("Pool detenido")

    # ---------------------------------------------------------------- API pública

    def encolar(self, tarea: Tarea) -> None:
        """Registra la tarea y la pone en la cola. No bloquea: la cola no tiene límite."""
        self.registro.agregar(tarea)
        self.cola.put_nowait(tarea.id)

    def cancelar(self, tarea_id: str) -> bool:
        """
        Cancela una tarea pendiente o en ejecución.
        Devuelve False si la tarea ya estaba en un estado final.
        """
        tarea = self.registro.obtener(tarea_id)
        if tarea is None or tarea.estado in ESTADOS_FINALES:
            return False

        if tarea.estado == Estado.PENDIENTE:
            # Sigue en la cola: la marcamos y el worker la descarta al sacarla.
            # (asyncio.Queue no permite sacar un elemento del medio.)
            tarea.estado = Estado.CANCELADA
            tarea.finalizada = ahora()
            return True

        # Está ejecutando: cancelamos su subtarea. El worker se entera porque
        # su `await subtarea` lanza CancelledError, y ahí marca el estado.
        subtarea = self.en_curso.get(tarea_id)
        if subtarea is not None:
            subtarea.cancel()
        return True

    @property
    def ocupados(self) -> int:
        return len(self.en_curso)

    # ---------------------------------------------------------------- worker

    async def _worker(self, numero: int) -> None:
        while True:
            tarea_id = await self.cola.get()  # se suspende si la cola está vacía
            try:
                tarea = self.registro.obtener(tarea_id)
                if tarea is None or tarea.estado != Estado.PENDIENTE:
                    continue  # fue cancelada mientras esperaba en la cola
                await self._ejecutar(tarea, numero)
            finally:
                self.cola.task_done()

    async def _ejecutar(self, tarea: Tarea, numero: int) -> None:
        tarea.estado = Estado.EJECUTANDO
        tarea.iniciada = ahora()
        log.info("worker-%d ejecuta %s (%s)", numero, tarea.id, tarea.tipo.value)

        subtarea = asyncio.create_task(tareas.ejecutar(tarea.tipo, tarea.parametros))
        self.en_curso[tarea.id] = subtarea
        try:
            tarea.resultado = await subtarea
            tarea.estado = Estado.COMPLETADA

        except asyncio.CancelledError:
            # Dos casos posibles que lanzan el mismo error:
            # a) cancelaron la subtarea (DELETE)  -> la tarea queda cancelada,
            #    el worker sigue vivo.
            # b) cancelaron AL WORKER (apagado)   -> hay que cancelar también la
            #    subtarea y dejar que el CancelledError siga subiendo.
            # `cancelling()` (Python 3.11+) dice si la cancelación es para esta
            # corrutina (el worker) o vino de la subtarea.
            tarea.estado = Estado.CANCELADA
            if asyncio.current_task().cancelling():
                subtarea.cancel()
                raise

        except Exception as e:
            # Excepción no capturada de la tarea: la tarea falla, el worker NO muere.
            tarea.estado = Estado.FALLIDA
            tarea.error = f"{type(e).__name__}: {e}"
            log.warning("tarea %s falló: %s", tarea.id, tarea.error)

        finally:
            tarea.finalizada = ahora()
            self.en_curso.pop(tarea.id, None)
