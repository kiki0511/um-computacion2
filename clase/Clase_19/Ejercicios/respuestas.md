# Clase 19: HTTP + FastAPI — Respuestas

Preparación: `python3 -m venv venv && source venv/bin/activate && pip install -r ../requirements.txt`

| Archivo | Qué cubre |
|---------|-----------|
| `ej3_api.py` | **Obligatorio**: API con PATCH, `/estadisticas` y límite de pendientes |
| `ej3_probar_api.py` | **Obligatorio**: prueba los errores, la validación, PATCH, límite y tipos |
| `ej1_2_http_crudo.py` | HTTP por socket, `\n` vs `\r\n`, sin Host, `do_DELETE`, PATCH → 501, keep-alive |
| `ej4_5_loop_y_async.py` | `--workers 3` y estado en memoria; `medir.py` con endpoints de CPU |
| `ej_extra_adicionales.py` | Cliente HTTP a mano, middleware `X-Tiempo` |

---

## Ejercicio 1: El protocolo a mano

1. La respuesta de `example.com` tiene tres partes: la línea de estado (`HTTP/1.1 200 OK`), los headers (uno por línea) y el cuerpo. La línea de estado y cada header terminan en `\r\n`; los headers se separan del cuerpo con una **línea vacía** (`\r\n\r\n`).
2. Devuelve `200`, de la familia 2xx (éxito).
3. Sin `Host:`, `example.com` responde **400 Bad Request**. HTTP/1.1 lo exige porque en una misma IP hay muchos sitios (virtual hosting) y el servidor necesita saber cuál pediste. En HTTP/1.0 era opcional porque se asumía un sitio por IP.
4. `GET /noexiste` en `example.com` devuelve **404**. Ojo: este dominio es especial y a veces responde 200 para cualquier ruta; con otro sitio da 404.
5. Con `\n` solo: `example.com` (y la mayoría de los servidores de producción) lo tolera, y el `http.server` de `crudo.py` también, porque su parser hace `rstrip('\r\n')`. En la demo, las dos variantes dan `200 OK`.
6. Es mala idea depender de esa tolerancia: la RFC exige `\r\n` y cada servidor decide cuánto se aparta. Un proxy o firewall en el medio puede interpretar los límites distinto que el servidor final, y ahí aparecen los ataques de *request smuggling*.
7. Seguros (no modifican nada): **GET** y **HEAD**.
8. Idempotentes: **GET, HEAD, PUT y DELETE**. Repetirlos deja el mismo estado final: PUT fija un valor y DELETE de algo ya borrado sigue borrado. **POST** no, porque cada POST crea un recurso nuevo o ejecuta la acción otra vez.
9. Si a un `POST` le vence el timeout, **no** es seguro reintentar: puede haberse procesado y perdido solo la respuesta, y se crearía dos veces. Un `PUT` sí se puede reintentar: el resultado es el mismo.
10. Es exactamente el problema de UDP de la clase 15: el cliente no distingue si se perdió el pedido o la respuesta. La solución también es la misma: un identificador del pedido (*idempotency key*, como el `seq`) para que el servidor detecte el duplicado y devuelva la respuesta guardada.

## Ejercicio 2: http.server es socketserver

1. `BaseHTTPRequestHandler` hereda de `StreamRequestHandler` (clase 16). Le aporta `rfile`/`wfile` con buffer: puede leer línea por línea la línea de pedido y los headers.
2. `ThreadingHTTPServer` usa `ThreadingMixIn`, el mismo de la clase 16.
3. En el `do_POST` hay que leer exactamente `Content-Length` bytes porque es el framing por longitud (clase 13). Con `recv(4096)` podrías leer de menos (el cuerpo llega en varios segmentos) o de más (con keep-alive, el siguiente pedido viene pegado en la misma conexión).
4. Con `protocol_version = 'HTTP/1.1'` el servidor responde `HTTP/1.1` y mantiene la conexión abierta (keep-alive) salvo `Connection: close`. A partir de ahí es **obligatorio** mandar `Content-Length` (o chunked), porque el cierre de la conexión ya no marca el fin del cuerpo.
5. `do_DELETE`: **204 No Content** si se borró y **404** si no existía.
6. `PATCH` sin implementar: el framework responde solo **501 Unsupported method ('PATCH')**.
7. En `crudo.py` un endpoint son unas 6–8 líneas (armar el JSON, `send_response`, `send_header` × 2, `end_headers`, `write`, y el ruteo a mano por `self.path`). En `api.py` son 2–3 (decorador, función y `return`), con validación y documentación incluidas.

## Ejercicio 3: API con FastAPI (obligatorio)

**Parte A**

1. La documentación de `/docs` la escribió **FastAPI**, generándola sola a partir de los tipos, los modelos Pydantic y los docstrings.
2. Si mandás un `tipo` que no está en la lista, da **422** con el detalle de los valores permitidos.
3. `/openapi.json` es la especificación **OpenAPI** (antes Swagger) de la API, en JSON: rutas, métodos, parámetros, esquemas y respuestas. `/docs` es una interfaz que lee ese archivo, y con él se pueden generar clientes automáticamente.

**Parte B** (`ej3_probar_api.py`)

| Pedido | Código | Mensaje | `loc` |
|--------|--------|---------|-------|
| `GET /tareas/abc` | 422 | Input should be a valid integer | `['path', 'tarea_id']` |
| `POST {"tipo":"volar"}` | 422 | Input should be 'descargar', 'hashear' or 'esperar' | `['body', 'tipo']` |
| `POST {..."prioridad":99}` | 422 | Input should be less than or equal to 5 | `['body', 'prioridad']` |
| `GET /tareas/999` | 404 | No existe esa tarea | — |

5. Los tres primeros son **422 Unprocessable Entity**: el pedido no cumple el contrato (tipos y rangos) y lo rechaza FastAPI. El último es **404 Not Found**: el pedido es válido, pero el recurso no existe, y eso lo decide **mi función**.
6. `loc` dice **dónde** está el error: en qué parte del pedido (`path`, `query`, `body`, `header`) y qué campo.
7. La validación corre **antes** de mi función. Con un `print` al entrar a `obtener()`, `/tareas/abc` nunca lo imprime (422 sin entrar), mientras que `/tareas/999` sí lo imprime.

**Parte C** (`ej3_api.py`)

8. `PATCH /tareas/{id}` usa el modelo `TareaCambio`, con todos los campos opcionales, y `model_dump(exclude_unset=True)` para aplicar solo lo que el cliente mandó. Un estado inválido da 422, un cuerpo vacío 400 y un id inexistente 404.
9. `GET /estadisticas` devuelve `{"total": 3, "por_estado": {"pendiente": 1, "ejecutando": 1, "completada": 1}}`.
10. Con 10 pendientes, el POST número 11 da **503 Service Unavailable** con `Retry-After: 5`. Elegí 503 porque es un límite de **capacidad del servidor**, temporal, y el mismo pedido va a funcionar más tarde. Descarté las alternativas:
    - 429 es rate limiting **por cliente**, y acá el límite es global.
    - 409 es un conflicto con el estado del recurso pedido, que no es el caso.
    - 400/422 dirían que el pedido está mal formado, y está perfecto.

    Al completar una tarea, el siguiente POST vuelve a dar 201.

**Parte D**

11. Sin `: int`, `/tareas/abc` ya no da 422: `tarea_id` llega como `str` (`'abc'`, y también `'5'`), la función se ejecuta y la búsqueda en el dict falla (con la API original da 404 siempre, porque `'5' != 5`).
12. Con `prioridad: str` acepta cualquier texto (`"urgente"`) y se pierde el rango 1..5. Pydantic v2 no convierte `int` a `str`: mandar `3` da 422.
13. Con cada anotación de tipo, FastAPI hace tres cosas:
    - **Valida**: rechaza con 422 lo que no cumple.
    - **Convierte**: el `"42"` de la URL pasa a `int` 42.
    - **Documenta**: aparece en OpenAPI y en `/docs`.

## Ejercicio 4: Dónde está el event loop

1. El endpoint `async` corre en el **MainThread**, dentro del event loop. El `def` común corre en un thread del **threadpool** (`AnyIO worker thread`).
2. `id_del_loop` es el mismo en todos los pedidos: hay **un solo event loop** por proceso.
3. El endpoint sincrónico dice que no hay loop porque corre en otro thread, y el loop pertenece al thread principal.
4. El loop lo crea **uvicorn**; FastAPI solo define la aplicación. **ASGI** (*Asynchronous Server Gateway Interface*) es el contrato entre el servidor (uvicorn) y la app: una corrutina `app(scope, receive, send)`. Es el sucesor asíncrono de WSGI.
5. Con `--workers 3`, el `pid` cambia: en 30 pedidos aparecieron **3 PIDs distintos**. Son 3 procesos independientes, cada uno con su loop.
6. El diccionario `tareas` **no se comparte**. Creé la tarea 1 y al pedirla 15 veces obtuve una mezcla de 200 y 404, según qué worker atendía. Cada proceso tiene su copia del dict (clase 4: procesos distintos no comparten memoria).
7. Para el TP2, el estado **no puede vivir en memoria del proceso** si hay más de un worker. Tiene que ir afuera, en algo que todos compartan: una base de datos (PostgreSQL/SQLite), Redis o el broker de la cola de tareas (lo que se ve con Celery en las clases siguientes).

## Ejercicio 5: async bien y mal

1. `medir.py`, 3 pedidos concurrentes de 1 s: `/async-bien` **1.01 s**, `/async-mal` **3.01 s**, `/sync` **1.01 s**.
2. `/async-mal` tarda el triple porque `time.sleep` dentro de un `async def` bloquea el único event loop y los tres pedidos se atienden en serie. Es la regla de la clase 18: nunca bloquear dentro de una corrutina.
3. `/sync` anda igual de bien porque FastAPI detecta que es un `def` y lo corre en el threadpool: el `time.sleep` bloquea un thread del pool, no el loop.
4. Regla:
   - `async def` si **todo** lo que espera la función es awaitable (`asyncio.sleep`, `httpx.AsyncClient`, drivers async).
   - `def` si usa algo bloqueante sin versión async.
   - Mezclar (bloqueante adentro de `async def`) es lo único que está mal.
5. El endpoint está **mal**: `requests.get` es bloqueante dentro de `async def` y congela el loop mientras espera la red.
6. Dos arreglos:
   ```python
   # (a) cambiar async def por def: FastAPI lo manda al threadpool
   @app.get('/datos')
   def datos():
       return requests.get('https://api.ejemplo.com/cosas').json()

   # (b) cambiar la biblioteca por una asíncrona
   @app.get('/datos')
   async def datos():
       async with httpx.AsyncClient() as c:
           r = await c.get('https://api.ejemplo.com/cosas')
       return r.json()
   ```
7. Cuarto grupo, cálculo pesado (un hash tarda ≈0.53 s; 3 pedidos; máquina de 2 núcleos):

| Endpoint | Tiempo | Por qué |
|----------|--------|---------|
| `/cpu-async` (`async def`) | 1.48 s | Serializa **y** bloquea el loop: nadie más es atendido |
| `/cpu-sync` (`def`) | 1.65 s | El loop queda libre, pero el GIL serializa los tres threads |
| `/cpu-procesos` (`run_in_executor` + `ProcessPoolExecutor`) | 0.84 s | Paralelismo real; limitado por los 2 núcleos |

   Para CPU ninguna de las tres formas de `medir.py` sirve de verdad. `def` al menos no congela el loop, pero no paraleliza. Lo correcto es mandar el trabajo a **procesos** y awaitear el resultado, que es la arquitectura del TP2: API asíncrona adelante y workers atrás.

## Adicionales

- **Cliente HTTP a mano**: lee la línea de estado, después headers hasta la línea vacía, y el cuerpo según `Transfer-Encoding: chunked`, `Content-Length`, o hasta el cierre si no viene ninguno.
- **Keep-alive**: con `protocol_version = 'HTTP/1.1'` se mandaron dos pedidos por la misma conexión y volvieron dos respuestas. Cada una trae su `Content-Length`: así se sabe dónde termina la primera y empieza la segunda.
- **Middleware**: `@app.middleware('http')` envuelve al endpoint. El orden es `middleware antes → endpoint → middleware después`, y en el "después" la respuesta ya existe, así que se le puede agregar `X-Tiempo` (≈203 ms para un endpoint de 200 ms).
- **Esqueleto del TP2**: `ej3_api.py` ya tiene `POST/GET /tareas`, `GET/PATCH/DELETE /tareas/{id}` y `GET /estadisticas`.
