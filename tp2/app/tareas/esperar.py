"""
Tarea `esperar`: duerme N segundos.

Sirve para probar cancelación, timeouts y ver el estado en vivo.
Usa asyncio.sleep (NO time.sleep): asyncio.sleep suspende solo esta
corrutina y le devuelve el control al event loop; time.sleep frenaría
el hilo entero y con él toda la API.
"""

import asyncio
from typing import Any


def validar(parametros: dict[str, Any]) -> None:
    """Lanza ValueError si los parámetros no sirven."""
    segundos = parametros.get("segundos")
    if not isinstance(segundos, (int, float)) or isinstance(segundos, bool):
        raise ValueError("'segundos' es obligatorio y debe ser un número")
    if segundos < 0:
        raise ValueError("'segundos' no puede ser negativo")


async def ejecutar(parametros: dict[str, Any]) -> dict[str, Any]:
    segundos = parametros["segundos"]
    await asyncio.sleep(segundos)
    return {"durmio": segundos}
