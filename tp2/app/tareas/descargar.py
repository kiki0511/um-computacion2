"""
Tarea `descargar` (I/O-bound): baja una lista de URLs y devuelve, por cada
una, el código de estado, el tamaño y cuánto tardó.

Modo concurrente (default): todas las descargas se lanzan juntas con
asyncio.gather. Mientras una espera la respuesta de la red, el event loop
atiende a las otras, así que N descargas tardan ~ lo que la más lenta.

Modo secuencial ("secuencial": true): un `for` con `await` adentro. Cada
descarga espera a que termine la anterior, así que tarda la SUMA. Existe
solo para la medición 1 (comparar contra el concurrente).

Por qué httpx y no aiohttp: API casi idéntica a requests (fácil de leer),
async nativo, y el AsyncClient trae pool de conexiones con límites
configurables. `requests` está prohibido porque es bloqueante: cada
request frenaría el event loop entero.

Cancelación a mitad de una descarga: el CancelledError se propaga a cada
corrutina hija de gather. httpx cierra la conexión de la respuesta
interrumpida, así que no queda ningún socket abierto colgado.
"""

import asyncio
import time
from typing import Any

from .. import config
from ..recursos import recursos


def validar(parametros: dict[str, Any]) -> None:
    urls = parametros.get("urls")
    if not isinstance(urls, list) or not urls:
        raise ValueError("'urls' es obligatorio y debe ser una lista no vacía")
    if len(urls) > config.MAX_URLS:
        raise ValueError(f"máximo {config.MAX_URLS} URLs por tarea")
    for url in urls:
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            raise ValueError(f"URL inválida: {url!r}")
    if not isinstance(parametros.get("secuencial", False), bool):
        raise ValueError("'secuencial' debe ser true o false")


async def _descargar_una(url: str) -> dict[str, Any]:
    """Baja una URL. Un error de red se reporta en el resultado, no corta la tarea."""
    inicio = time.perf_counter()
    try:
        respuesta = await recursos.cliente_http.get(url)
        return {
            "url": url,
            "estado": respuesta.status_code,
            "bytes": len(respuesta.content),
            "segundos": round(time.perf_counter() - inicio, 4),
        }
    except Exception as e:  # CancelledError NO entra acá: hereda de BaseException
        return {
            "url": url,
            "error": f"{type(e).__name__}: {e}",
            "segundos": round(time.perf_counter() - inicio, 4),
        }


async def ejecutar(parametros: dict[str, Any]) -> dict[str, Any]:
    urls = parametros["urls"]
    inicio = time.perf_counter()

    if parametros.get("secuencial", False):
        resultados = []
        for url in urls:
            resultados.append(await _descargar_una(url))
    else:
        resultados = await asyncio.gather(*(_descargar_una(u) for u in urls))

    return {
        "modo": "secuencial" if parametros.get("secuencial") else "concurrente",
        "total_segundos": round(time.perf_counter() - inicio, 4),
        "descargas": resultados,
    }
