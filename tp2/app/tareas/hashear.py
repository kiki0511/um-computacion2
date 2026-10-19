"""
Tarea `hashear` (CPU-bound): aplica SHA-256 N veces sobre un texto.

El problema: este cálculo no tiene ningún `await`. Si corre dentro del
event loop, el loop no puede atender a nadie más hasta que termine: la API
entera queda congelada (eso es lo que muestra la medición 2).

La solución: mandarlo a un ProcessPoolExecutor con run_in_executor. El
cálculo corre en OTRO proceso y el event loop solo hace `await` del
resultado, mientras sigue atendiendo requests.

Por qué procesos y no hilos (asyncio.to_thread): hashear 32 bytes es puro
Python + C cortito, y el GIL deja correr un solo hilo de Python a la vez.
Con hilos la API respondería, pero varios hashes no correrían en paralelo
de verdad. Con procesos, cada uno tiene su propio intérprete y su propio
GIL, así que usan varios núcleos.

Por qué en bloques: un proceso que está calculando NO se puede cancelar
desde afuera. Si mandáramos los N millones de iteraciones de una, un
DELETE no tendría efecto hasta el final. Partiéndolo en bloques de
BLOQUE_HASH iteraciones, entre bloque y bloque hay un `await`: ahí es
donde la cancelación (o el timeout) corta la tarea. El bloque que estaba
en vuelo termina en su proceso y su resultado se descarta.
"""

import asyncio
import hashlib
from typing import Any

from .. import config
from ..recursos import recursos


def hash_iterado(datos: bytes, iteraciones: int) -> bytes:
    """
    Aplica SHA-256 `iteraciones` veces. Función pura y a nivel de módulo:
    tiene que poder serializarse (pickle) para mandarse a otro proceso.
    """
    for _ in range(iteraciones):
        datos = hashlib.sha256(datos).digest()
    return datos


def validar(parametros: dict[str, Any]) -> None:
    texto = parametros.get("texto")
    iteraciones = parametros.get("iteraciones")
    if not isinstance(texto, str):
        raise ValueError("'texto' es obligatorio y debe ser un string")
    if not isinstance(iteraciones, int) or isinstance(iteraciones, bool):
        raise ValueError("'iteraciones' es obligatorio y debe ser un entero")
    if not 1 <= iteraciones <= config.MAX_ITERACIONES:
        raise ValueError(f"'iteraciones' debe estar entre 1 y {config.MAX_ITERACIONES}")


async def ejecutar(parametros: dict[str, Any]) -> dict[str, Any]:
    datos = parametros["texto"].encode()
    iteraciones = parametros["iteraciones"]

    if not config.USAR_EXECUTOR:
        # MAL A PROPÓSITO (medición 2): bloquea el event loop entero.
        # Ni la API, ni los otros workers, ni el timeout pueden hacer nada
        # hasta que esta línea termine.
        resultado = hash_iterado(datos, iteraciones)
        return {"hash": resultado.hex(), "iteraciones": iteraciones, "executor": False}

    loop = asyncio.get_running_loop()
    restantes = iteraciones
    bloques = 0
    while restantes > 0:
        n = min(restantes, config.BLOQUE_HASH)
        # El cálculo corre en otro proceso; este await libera el event loop.
        datos = await loop.run_in_executor(recursos.executor, hash_iterado, datos, n)
        restantes -= n
        bloques += 1

    return {
        "hash": datos.hex(),
        "iteraciones": iteraciones,
        "bloques": bloques,
        "executor": True,
    }
