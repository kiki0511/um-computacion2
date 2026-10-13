"""
Despacho de tareas: según el tipo, a qué función de validación y de
ejecución corresponde.

Semana 1: solo `esperar` está implementada. `descargar` y `hashear`
se agregan en la semana 2.
"""

from typing import Any

from ..modelos import TipoTarea
from . import esperar

# tipo -> (validar, ejecutar)
_IMPLEMENTADAS = {
    TipoTarea.ESPERAR: (esperar.validar, esperar.ejecutar),
}


def validar(tipo: TipoTarea, parametros: dict[str, Any]) -> None:
    """Lanza ValueError si el tipo no está implementado o los parámetros son inválidos."""
    if tipo not in _IMPLEMENTADAS:
        raise ValueError(f"el tipo '{tipo.value}' todavía no está implementado")
    validador, _ = _IMPLEMENTADAS[tipo]
    validador(parametros)


async def ejecutar(tipo: TipoTarea, parametros: dict[str, Any]) -> Any:
    _, ejecutor = _IMPLEMENTADAS[tipo]
    return await ejecutor(parametros)
