"""
Despacho de tareas: según el tipo, a qué función de validación y de
ejecución corresponde.
"""

from typing import Any

from ..modelos import TipoTarea
from . import descargar, esperar, hashear

# tipo -> (validar, ejecutar)
_IMPLEMENTADAS = {
    TipoTarea.DESCARGAR: (descargar.validar, descargar.ejecutar),
    TipoTarea.HASHEAR: (hashear.validar, hashear.ejecutar),
    TipoTarea.ESPERAR: (esperar.validar, esperar.ejecutar),
}


def validar(tipo: TipoTarea, parametros: dict[str, Any]) -> None:
    """Lanza ValueError si los parámetros son inválidos."""
    validador, _ = _IMPLEMENTADAS[tipo]
    validador(parametros)


async def ejecutar(tipo: TipoTarea, parametros: dict[str, Any]) -> Any:
    _, ejecutor = _IMPLEMENTADAS[tipo]
    return await ejecutor(parametros)
