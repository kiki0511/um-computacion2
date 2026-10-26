"""
Pool de workers: N corrutinas que consumen ids de tarea de una asyncio.Queue.

Patrón productor-consumidor (clase 11), pero con corrutinas en vez de threads:
- Productor: el endpoint POST /tareas, que hace `encolar()`.
- Consumidores: los N workers, que hacen `await cola.get()`.

No hace falta Lock: los workers corren todos en el mismo hilo (el del event
loop) y solo se ceden el control en los `await`. Entre un `await` y el
siguiente, ningún otro worker puede tocar el estado compartido.

Cada tarea corre en su propia asyncio.Task (la "subtarea"), separada del
worker. Eso permite:
- Cancelar una tarea en ejecución (DELETE) sin matar al worker.
- Ponerle un timeout a la tarea sin que afecte al worker.
- Que una excepción de la tarea no mate al worker: queda guardada en la
  subtarea y el worker solo la lee.
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
        # Pasa a False al recibir SIGINT/SIGTERM: no se aceptan ni arrancan tareas nuevas
        self.aceptando = True

    # ---------------------------------------------------------------- ciclo de vida

    def iniciar(self) -> None:
        """Lanza los N workers. Tiene que llamarse con el event loop corriendo."""
        for i in range(self.n_workers):
            w = asyncio.create_task(self._worker(i), name=f"worker-{i}")
            self._workers.append(w)
        log.info("Pool iniciado con %d workers", self.n_workers)

    def dejar_de_aceptar(self) -> None:
        self.aceptando = False

    async def drenar(self, limite: float) -> None:
        """
        Apagado, paso 1: espera hasta `limite` segundos a que terminen las
        tareas en curso. Las pendientes no se arrancan (quedan 'pendiente'
        en el volcado). Lo que no termine a tiempo lo cancela `detener()`.
        """
        self.dejar_de_aceptar()
        if not self.en_curso:
            return
        log.info("Esperando hasta %.0fs a %d tareas en curso", limite, len(self.en_curso))
        _, sin_terminar = await asyncio.wait(list(self.en_curso.values()), timeout=limite)
        if sin_terminar:
            log.warning("%d tareas no terminaron a tiempo: se cancelan", len(sin_terminar))

    async def detener(self) -> None:
        """
        Apagado, paso 2: cancela los workers y espera a que terminen. Cada
        worker, al ser cancelado, cancela su subtarea y espera a que libere
        sus recursos antes de salir: no quedan corrutinas huérfanas.
        """
        for w in self._workers:
            w.cancel()
        # return_exceptions: que el CancelledError de cada worker no corte la espera
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

        # Está ejecutando: cancelamos su subtarea. El worker la está esperando
        # y, cuando termine de cancelarse, registra el estado final.
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
                if not self.aceptando:
                    continue  # apagándonos: queda 'pendiente' para el volcado
                await self._ejecutar(tarea, numero)
            finally:
                self.cola.task_done()

    async def _ejecutar(self, tarea: Tarea, numero: int) -> None:
        tarea.estado = Estado.EJECUTANDO
        tarea.iniciada = ahora()
        log.info("worker-%d ejecuta %s (%s)", numero, tarea.id, tarea.tipo.value)

        subtarea = asyncio.create_task(self._correr(tarea), name=f"tarea-{tarea.id}")
        self.en_curso[tarea.id] = subtarea
        try:
            # asyncio.wait (y no `await subtarea`) porque:
            # - no relanza la excepción de la subtarea: la leemos después.
            # - si cancelan AL WORKER, no cancela sola a la subtarea: lo
            #   hacemos nosotros abajo, y esperamos a que termine.
            await asyncio.wait({subtarea})
        except asyncio.CancelledError:
            # Cancelaron al worker (apagado del servidor).
            subtarea.cancel()
            await asyncio.wait({subtarea})  # que libere sus recursos antes de seguir
            self._registrar_final(tarea, subtarea, por_apagado=True)
            raise  # el worker tiene que terminar: propagamos la cancelación
        else:
            self._registrar_final(tarea, subtarea)
        finally:
            self.en_curso.pop(tarea.id, None)

    async def _correr(self, tarea: Tarea):
        """Lo que corre dentro de la subtarea: la tarea real, con su timeout."""
        # Al vencer, asyncio.timeout cancela lo que está adentro y lanza TimeoutError.
        async with asyncio.timeout(tarea.timeout):
            return await tareas.ejecutar(tarea.tipo, tarea.parametros)

    def _registrar_final(
        self, tarea: Tarea, subtarea: asyncio.Task, por_apagado: bool = False
    ) -> None:
        """
        El estado final sale de CÓMO terminó la subtarea. Si terminó bien justo
        antes del apagado, queda 'completada' aunque el worker se esté cancelando.
        """
        tarea.finalizada = ahora()

        if subtarea.cancelled():
            tarea.estado = Estado.CANCELADA
            if por_apagado:
                tarea.error = "cancelada por apagado del servidor"
            return

        error = subtarea.exception()
        if error is None:
            tarea.resultado = subtarea.result()
            tarea.estado = Estado.COMPLETADA
        elif isinstance(error, TimeoutError):
            tarea.estado = Estado.FALLIDA
            tarea.error = f"timeout: superó los {tarea.timeout:g}s"
            log.warning("tarea %s: %s", tarea.id, tarea.error)
        else:
            # Excepción no capturada de la tarea: la tarea falla, el worker NO muere.
            tarea.estado = Estado.FALLIDA
            tarea.error = f"{type(error).__name__}: {error}"
            log.warning("tarea %s falló: %s", tarea.id, tarea.error)
