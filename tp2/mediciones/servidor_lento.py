"""
Servidor HTTP "lento" para la medición 1 (concurrencia I/O).

Responde cada request después de una demora controlada, como si fuera un
sitio remoto con latencia. Sirve para medir descargas sin depender de cómo
ande internet ese día: con demoras fijas, el resultado es reproducible.

    GET /demora/{segundos}?bytes=N   espera `segundos` y devuelve N bytes

Usa asyncio.sleep, así que atiende muchas descargas a la vez sin problema:
mientras una espera, el event loop atiende a las demás. (Si usara
time.sleep, el servidor mismo serializaría las descargas y la medición
no mediría nada de nuestra API.)

Corre como un servicio aparte del docker-compose (`lento`, puerto 8001).
Desde el contenedor de la API se lo alcanza como http://lento:8001/...
"""

import asyncio

from fastapi import FastAPI, Query, Response

app = FastAPI(title="Servidor lento (solo para mediciones)")


@app.get("/demora/{segundos}")
async def demora(segundos: float, bytes: int = Query(1000, ge=0, le=10_000_000)) -> Response:
    await asyncio.sleep(segundos)
    return Response(content=b"x" * bytes, media_type="application/octet-stream")
