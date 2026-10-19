"""
Registro en memoria de todas las tareas (dict id -> Tarea).

No usa Lock: todo el acceso ocurre desde corrutinas del mismo event loop,
y ninguna de estas funciones tiene un `await` adentro. El loop solo cambia
de corrutina en un `await`, así que cada operación es atómica de hecho.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

from .modelos import Estado, Tarea, ahora

log = logging.getLogger(__name__)


class Registro:
    def __init__(self) -> None:
        self._tareas: dict[str, Tarea] = {}

    def agregar(self, tarea: Tarea) -> None:
        self._tareas[tarea.id] = tarea

    def obtener(self, tarea_id: str) -> Tarea | None:
        return self._tareas.get(tarea_id)

    def listar(self, estado: Estado | None = None) -> list[Tarea]:
        """Todas las tareas, o solo las de un estado. Ordenadas por creación."""
        tareas = self._tareas.values()
        if estado is not None:
            tareas = [t for t in tareas if t.estado == estado]
        return sorted(tareas, key=lambda t: t.creada)

    def totales_por_estado(self) -> dict[str, int]:
        totales = {e.value: 0 for e in Estado}
        for t in self._tareas.values():
            totales[t.estado.value] += 1
        return totales

    def tiempo_promedio(self) -> dict[str, float | None]:
        """Duración promedio (segundos) de las tareas completadas, por tipo."""
        duraciones: dict[str, list[float]] = {}
        for t in self._tareas.values():
            if t.estado == Estado.COMPLETADA and t.duracion is not None:
                duraciones.setdefault(t.tipo.value, []).append(t.duracion)
        return {
            tipo: round(sum(lista) / len(lista), 4)
            for tipo, lista in duraciones.items()
        }

    # ---------------------------------------------------------------- persistencia

    async def volcar(self, directorio: str) -> Path:
        """
        Guarda todas las tareas en <directorio>/estado_<timestamp>.json.

        Escribir un archivo es I/O bloqueante, así que va con asyncio.to_thread:
        corre en un hilo aparte y el event loop no se frena mientras tanto.
        """
        carpeta = Path(directorio)
        ruta = carpeta / f"estado_{datetime.now():%Y%m%d_%H%M%S}.json"
        contenido = json.dumps(
            {
                "volcado": ahora().isoformat(),
                "totales": self.totales_por_estado(),
                "tareas": [t.model_dump(mode="json") for t in self.listar()],
            },
            indent=2,
            ensure_ascii=False,
        )

        def escribir() -> None:
            carpeta.mkdir(parents=True, exist_ok=True)
            ruta.write_text(contenido, encoding="utf-8")

        await asyncio.to_thread(escribir)
        return ruta


async def reportar_volcado_previo(directorio: str) -> None:
    """Al arrancar: si hay un volcado anterior, lo informa por log (no lo recarga)."""

    def leer_ultimo() -> tuple[Path, dict] | None:
        volcados = sorted(Path(directorio).glob("estado_*.json"))
        if not volcados:
            return None
        return volcados[-1], json.loads(volcados[-1].read_text(encoding="utf-8"))

    try:
        encontrado = await asyncio.to_thread(leer_ultimo)
    except (OSError, json.JSONDecodeError) as e:
        log.warning("No se pudo leer el volcado previo: %s", e)
        return

    if encontrado is None:
        log.info("Sin volcados previos en '%s/'", directorio)
        return
    ruta, datos = encontrado
    log.info(
        "Volcado previo encontrado: %s (%d tareas, %s)",
        ruta.name,
        len(datos.get("tareas", [])),
        datos.get("totales", {}),
    )
