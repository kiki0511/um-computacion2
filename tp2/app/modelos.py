"""
Modelos de datos (Pydantic) de la plataforma de tareas.

- Estado: los 5 estados posibles de una tarea.
- TipoTarea: los tipos de tarea que acepta el sistema.
- TareaIn: lo que manda el cliente en el POST.
- Tarea: la tarea completa, tal como la guarda el registro y la devuelve la API.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Estado(str, Enum):
    PENDIENTE = "pendiente"
    EJECUTANDO = "ejecutando"
    COMPLETADA = "completada"
    FALLIDA = "fallida"
    CANCELADA = "cancelada"


# Estados de los que una tarea ya no sale
ESTADOS_FINALES = {Estado.COMPLETADA, Estado.FALLIDA, Estado.CANCELADA}


class TipoTarea(str, Enum):
    DESCARGAR = "descargar"
    HASHEAR = "hashear"
    ESPERAR = "esperar"


def ahora() -> datetime:
    """Fecha y hora actual en UTC (con zona, para que el JSON sea inequívoco)."""
    return datetime.now(timezone.utc)


class TareaIn(BaseModel):
    """Cuerpo del POST /tareas."""

    tipo: TipoTarea
    parametros: dict[str, Any] = Field(default_factory=dict)
    # Que sea finito y mayor que 0 se valida en el endpoint (main.py), no
    # acá: si Pydantic rechaza un Infinity o un NaN, FastAPI incluye ese valor
    # en el cuerpo del 422, no lo puede pasar a JSON y termina respondiendo 500.
    timeout: float | None = Field(
        default=None, description="Segundos (> 0); si no se manda, usa el default"
    )


class Tarea(BaseModel):
    """Tarea completa con su estado y resultado."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    tipo: TipoTarea
    parametros: dict[str, Any]
    timeout: float
    estado: Estado = Estado.PENDIENTE
    creada: datetime = Field(default_factory=ahora)
    iniciada: datetime | None = None
    finalizada: datetime | None = None
    resultado: Any = None
    error: str | None = None

    @property
    def duracion(self) -> float | None:
        """Segundos que estuvo ejecutándose (None si no arrancó o no terminó)."""
        if self.iniciada and self.finalizada:
            return (self.finalizada - self.iniciada).total_seconds()
        return None
