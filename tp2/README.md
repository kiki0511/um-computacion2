# TP2 — Plataforma de Tareas Distribuidas

**Computación II — Universidad de Mendoza — 2026**

Un servicio HTTP al que se le encargan trabajos, que los ejecuta de forma
concurrente con un pool de workers asíncronos y permite consultar su estado y
resultado. Todo corre en un solo proceso con un event loop de `asyncio`; el
trabajo de CPU se manda a un `ProcessPoolExecutor` para no congelar la API.

---

## Índice

1. [Descripción y uso](#1-descripción-y-uso)
2. [Arquitectura](#2-arquitectura)
3. [Decisiones de diseño](#3-decisiones-de-diseño)
4. [Mediciones](#4-mediciones)
5. [Conceptos del curso aplicados](#5-conceptos-del-curso-aplicados)
6. [Limitaciones conocidas](#6-limitaciones-conocidas)
7. [Lo que aprendí](#7-lo-que-aprendí)

---

## 1. Descripción y uso

### Levantar

```bash
docker compose up --build
```

La API queda en `http://localhost:8000` (documentación interactiva en
`http://localhost:8000/docs`). El compose levanta además un segundo servicio,
`lento` (puerto 8001), que solo se usa para la medición 1.

Sin Docker (Python 3.11+):

```bash
pip install -r requirements.txt
python -m app.main
```

### Endpoints

| Método | Ruta | Qué hace |
|--------|------|----------|
| `POST` | `/tareas` | Encola una tarea. Responde `202` con su `id` al instante |
| `GET` | `/tareas` | Lista las tareas. Filtro opcional `?estado=` |
| `GET` | `/tareas/{id}` | Estado y resultado de una tarea |
| `DELETE` | `/tareas/{id}` | Cancela una tarea pendiente o en ejecución |
| `GET` | `/estadisticas` | Totales por estado, tiempo promedio, workers ocupados |

Estados: `pendiente` → `ejecutando` → `completada` / `fallida` / `cancelada`.

### Tipos de tarea

| Tipo | Parámetros | Naturaleza |
|------|-----------|------------|
| `descargar` | `urls` (lista), `secuencial` (opcional, default `false`) | I/O-bound |
| `hashear` | `texto`, `iteraciones` (SHA-256 aplicado N veces) | CPU-bound |
| `esperar` | `segundos` | I/O simulado |

Toda tarea acepta además `timeout` (segundos). Si no se manda, usa `TIMEOUT_DEFAULT`.

### Ejemplos con `curl`

```bash
# Descargar tres páginas a la vez
curl -X POST localhost:8000/tareas -H 'Content-Type: application/json' \
  -d '{"tipo": "descargar", "parametros": {"urls": ["https://www.python.org", "https://github.com", "https://www.um.edu.ar"]}}'
# {"id":"3f9a1c2e","estado":"pendiente"}

# Hash pesado (corre en el executor, la API sigue respondiendo)
curl -X POST localhost:8000/tareas -H 'Content-Type: application/json' \
  -d '{"tipo": "hashear", "parametros": {"texto": "hola", "iteraciones": 5000000}}'

# Esperar 30 s, con timeout de 5 s: termina 'fallida' por timeout
curl -X POST localhost:8000/tareas -H 'Content-Type: application/json' \
  -d '{"tipo": "esperar", "parametros": {"segundos": 30}, "timeout": 5}'

# Consultar una tarea
curl localhost:8000/tareas/3f9a1c2e

# Listar solo las que están ejecutando
curl 'localhost:8000/tareas?estado=ejecutando'

# Cancelar (sirve también si ya está ejecutando)
curl -X DELETE localhost:8000/tareas/3f9a1c2e

# Estadísticas
curl localhost:8000/estadisticas
```

Probar la cancelación en vivo: mandar un `esperar` de 60 s, consultar que esté
`ejecutando`, hacer `DELETE` y volver a consultar: queda `cancelada`.

### Apagado ordenado

```bash
docker compose stop      # manda SIGTERM al proceso (Ctrl+C manda SIGINT)
```

La API deja de aceptar tareas (`503`), espera hasta `TIMEOUT_APAGADO` segundos a
las que están ejecutando, cancela las que no terminaron y vuelca todo a
`estados/estado_<timestamp>.json` (carpeta montada en el host). Al volver a
arrancar, reporta por log el último volcado encontrado.

### Configuración

Todo por variables de entorno (en `docker-compose.yml` o al levantar, por
ejemplo `N_WORKERS=50 docker compose up --build`):

| Variable | Default | Qué controla |
|----------|---------|--------------|
| `N_WORKERS` | 4 | Workers (corrutinas) del pool |
| `TIMEOUT_DEFAULT` | 60 | Timeout de una tarea si no trae uno |
| `TIMEOUT_APAGADO` | 20 | Espera máxima a las tareas en curso al apagar |
| `USAR_EXECUTOR` | true | `false` corre el hash en el event loop (solo para la medición 2) |
| `N_PROCESOS` | núcleos | Procesos del `ProcessPoolExecutor` |
| `BLOQUE_HASH` | 200000 | Iteraciones por bloque enviado al executor |
| `TIMEOUT_HTTP` | 15 | Timeout de cada request de `descargar` |
| `MAX_URLS` / `MAX_ITERACIONES` | 100 / 10⁸ | Topes de validación |

### Estructura

```
tp2/
├── app/
│   ├── main.py            API FastAPI, lifespan (arranque/apagado) y señales
│   ├── pool.py            cola + workers + cancelación + timeouts
│   ├── registro.py        estado en memoria y volcado a JSON
│   ├── modelos.py         modelos Pydantic y estados
│   ├── recursos.py        cliente HTTP y executor compartidos
│   ├── config.py          configuración por variables de entorno
│   └── tareas/            descargar.py, hashear.py, esperar.py
├── mediciones/
│   ├── medir.py           script de las tres mediciones
│   ├── servidor_lento.py  servidor con latencia controlada (medición 1)
│   └── resultados/        datos crudos de cada medición (JSON)
├── Dockerfile
└── docker-compose.yml
```

---

## 2. Arquitectura

```
                      un solo proceso, un solo hilo: el event loop
  ┌───────────────────────────────────────────────────────────────────────┐
  │                                                                       │
  │  ┌────────────────┐  encolar(id)  ┌──────────────┐                    │
  │  │  API FastAPI   │──────────────>│ asyncio.Queue│                    │
  │  │  (uvicorn)     │               └──────┬───────┘                    │
  │  └───┬────────▲───┘                      │ await cola.get()           │
  │      │        │                          v                            │
  │      │ lee/   │                ┌───────────────────┐                  │
  │      │ escribe│                │ worker-0 … N-1    │                  │
  │      v        │                │ (corrutinas)      │                  │
  │  ┌──────────────────┐          └─────────┬─────────┘                  │
  │  │ Registro         │<─── estado ────────┤ create_task                │
  │  │ dict id -> Tarea │     y resultado    v                            │
  │  └──────────────────┘          ┌───────────────────┐                  │
  │                                │ subtarea          │                  │
  │                                │ asyncio.timeout() │                  │
  │                                └──┬──────┬──────┬──┘                  │
  │                    descargar      │      │      │  esperar            │
  │               httpx.AsyncClient <─┘      │      └─> asyncio.sleep     │
  │                  (gather)                │ hashear                    │
  └──────────────────────────────────────────┼────────────────────────────┘
                                             │ run_in_executor (por bloques)
                                             v
                                ┌──────────────────────────┐
                                │ ProcessPoolExecutor      │
                                │ procesos aparte, cada uno│
                                │ con su propio GIL        │
                                └──────────────────────────┘
```

### Flujo de una tarea

1. `POST /tareas` valida los parámetros, crea la `Tarea` (estado `pendiente`),
   la guarda en el registro y pone su `id` en la cola con `put_nowait`.
   Responde `202` en el acto: no espera a nada.
2. Un worker libre estaba suspendido en `await cola.get()`. Se despierta con el
   `id`, lo busca en el registro y, si sigue `pendiente`, la pasa a `ejecutando`.
3. El worker lanza la tarea en una **subtarea** (`asyncio.create_task`) envuelta
   en `asyncio.timeout(...)`, la guarda en `en_curso` y espera con
   `asyncio.wait`.
4. La subtarea termina de una de cuatro formas, y el worker lee cuál fue:
   - devolvió un resultado → `completada`
   - lanzó `TimeoutError` → `fallida` ("timeout: superó los N s")
   - lanzó otra excepción → `fallida` (tipo y mensaje del error)
   - fue cancelada (DELETE o apagado) → `cancelada`
5. El worker saca la tarea de `en_curso`, marca `task_done()` y vuelve a
   `await cola.get()`.

```
            DELETE (sigue en la cola)
   ┌──────────────────────────────────────────────┐
   │                                              v
pendiente ──(worker la toma)──> ejecutando      cancelada
                                  │   │   │       ^
                                  │   │   └───────┘ DELETE / apagado
                                  │   v
                                  │ completada
                                  v
                               fallida (timeout o error)
```

---

## 3. Decisiones de diseño

### ¿Por qué `asyncio.Queue` y no `queue.Queue`?

`queue.Queue` está hecha para threads: su `get()` **bloquea el hilo** hasta que
haya un elemento. Acá todos los workers y la API comparten un único hilo, el
del event loop; un `get()` bloqueante congelaría todo el servidor mientras la
cola esté vacía. Además, su Lock interno no sirve de nada en un solo hilo.

`asyncio.Queue.get()` es una corrutina: si la cola está vacía, el worker se
**suspende** en el `await` y le devuelve el control al loop, que sigue
atendiendo requests y a los demás workers. Cuando el endpoint hace
`put_nowait`, el loop despierta a uno de los workers que esperaban.

`asyncio.Queue` no es thread-safe, pero no lo necesita: solo la tocan
corrutinas del mismo loop.

### ¿Por qué el pool no necesita un `Lock`?

En `asyncio` el cambio de corrutina es **cooperativo**: solo pasa en un `await`.
Las operaciones sobre el estado compartido (el `dict` del registro, `en_curso`,
el estado de una tarea) no tienen ningún `await` en el medio, así que ningún
otro worker puede meterse a la mitad. Con threads, en cambio, el sistema
operativo puede interrumpir entre dos instrucciones cualquiera, y por eso en la
clase 11 hacía falta el Lock.

El caso a cuidar sería un "leer → `await` → escribir" sobre el mismo dato. En el
código no hay ninguno.

### ¿Cómo evito que una tarea CPU-bound congele la API?

El hash iterado es puro cálculo: no tiene ningún `await`. Si corre dentro de una
corrutina, el loop no recupera el control hasta que termina, y durante ese
tiempo nadie más avanza (la medición 2 lo muestra con números).

Por eso `hashear` usa `loop.run_in_executor(ProcessPoolExecutor, ...)`: el
cálculo corre en **otro proceso** y el worker solo hace `await` del resultado,
liberando el loop.

- **Procesos y no threads** (`asyncio.to_thread`): con threads la API también
  respondería, pero por el **GIL** varios hashes no correrían en paralelo de
  verdad. Cada proceso tiene su propio intérprete y su propio GIL, así que
  usan núcleos distintos.
- **Por bloques** de `BLOQUE_HASH` iteraciones: un proceso que está calculando
  no se puede interrumpir desde afuera. Si se mandara todo el hash de una vez,
  un `DELETE` o un timeout no tendrían efecto hasta el final. Partido en
  bloques, entre bloque y bloque hay un `await`, y ahí es donde la
  cancelación corta.
- **`spawn` explícito** como método de arranque: es el mismo en Linux, macOS y
  Windows, y evita hacer `fork()` de un proceso que ya tiene threads (los de
  `to_thread`). Por eso `main.py` tiene la guarda `if __name__ == "__main__"`.
- El executor se crea **una sola vez** en el `lifespan` y se reutiliza: crear
  procesos es caro.

La escritura del JSON de volcado también es bloqueante (I/O de disco), pero
corta: va con `asyncio.to_thread`, que alcanza porque no compite por CPU.

### ¿Cómo implementé la cancelación y qué pasa con los recursos?

Cada tarea corre en su propia `asyncio.Task` (la *subtarea*), separada del
worker. Eso permite cancelar la tarea sin matar al worker.

- **Tarea pendiente**: `asyncio.Queue` no permite sacar un elemento del medio,
  así que se marca `cancelada` en el registro. Cuando un worker la saca de la
  cola, ve que ya no está `pendiente` y la descarta.
- **Tarea ejecutando**: `DELETE` llama a `subtarea.cancel()`. Eso inyecta un
  `CancelledError` en el `await` donde la subtarea esté suspendida en ese
  momento. El worker, que la esperaba, la ve terminar cancelada y registra el
  estado. Por eso el `DELETE` responde "cancelación solicitada": el estado
  pasa a `cancelada` una vuelta de loop después.

Qué pasa con lo que quedó a medio usar, según el tipo:

| Tarea | Dónde la agarra la cancelación | Qué se libera |
|-------|-------------------------------|---------------|
| `esperar` | en el `asyncio.sleep` | nada que liberar |
| `descargar` | en el `await` de alguna descarga | `gather` propaga la cancelación a **todas** las descargas hijas; httpx cierra la conexión interrumpida. No queda ningún socket colgado. El `AsyncClient` es compartido y sigue vivo |
| `hashear` | en el `await` del bloque en curso | el bloque que ya estaba corriendo en el proceso termina igual (no se puede interrumpir) y su resultado se descarta. No se mandan más bloques |

`descargar` atrapa `Exception` por URL para que un error de red no corte toda la
tarea, pero `CancelledError` hereda de `BaseException`, así que **no** queda
atrapado ahí y la cancelación se propaga bien.

El timeout usa el mismo mecanismo: `asyncio.timeout()` cancela lo que tiene
adentro al vencer y lo convierte en `TimeoutError`.

**Sin corrutinas huérfanas**: toda tarea creada con `create_task` tiene a alguien
que la espera. Las subtareas las espera su worker, y si cancelan al worker (en
el apagado), primero cancela su subtarea y **espera a que termine** antes de
salir. A los workers los espera `detener()` con `gather`.

### ¿Qué pasa si un worker lanza una excepción no capturada?

Si la excepción viene de la **tarea**, el worker no se entera como excepción: la
subtarea la guarda y el worker la lee con `subtarea.exception()`. La tarea
queda `fallida` con el tipo y el mensaje del error, y el worker sigue con la
siguiente. Por eso el worker espera con `asyncio.wait({subtarea})` y no con
`await subtarea` (que relanzaría la excepción dentro del worker).

Sin esta separación, una excepción mataría a la corrutina del worker. asyncio
solo lo avisaría por log al recolectarla, y el pool quedaría con un worker
menos sin que nadie se entere. El `try/finally` alrededor de cada tarea
garantiza además que siempre se llame a `task_done()`.

### Otras decisiones

- **httpx y no aiohttp**: API casi igual a `requests` (fácil de leer), async
  nativo y un `AsyncClient` con pool de conexiones y límites configurables.
  Se usa **un solo cliente** para todo el servidor: reusa conexiones
  (keep-alive) y pone un tope global de 100 conexiones simultáneas.
- **Recursos en el `lifespan`**: el cliente HTTP, el executor y los workers se
  crean al arrancar y se cierran al apagar, en orden.
- **`202 Accepted`** en el `POST`: la tarea fue aceptada pero no está hecha.
- **Señales**: uvicorn instala su handler de SIGINT/SIGTERM. Lo extiendo
  (`Servidor.handle_exit`) solo para bajar el flag `aceptando`: un handler de
  señal puede correr entre dos instrucciones cualquiera, así que no hace nada
  más. El resto del apagado sucede en la parte final del `lifespan`.
- **Docker**: `CMD` en forma exec para que Python sea el PID 1 y reciba el
  SIGTERM directamente; `stop_grace_period: 30s` mayor que `TIMEOUT_APAGADO`
  para que Docker no mate el proceso con SIGKILL antes del volcado.

---

## 4. Mediciones

Todas se corren con `mediciones/medir.py`, que solo usa la biblioteca estándar
(no hay que instalar nada) y guarda los datos crudos de cada corrida en
`mediciones/resultados/`.

**Entorno:** MacBook con Apple M4 Pro (12 núcleos: 8 de rendimiento y 4 de
eficiencia), macOS 26.6.2, Docker Desktop con los 12 núcleos asignados. La
API corre en el contenedor; el script de medición, en el host.

### 4.1 Concurrencia I/O: 20 descargas secuenciales contra 20 concurrentes

```bash
docker compose up --build
python3 mediciones/medir.py io            # servidor lento local
python3 mediciones/medir.py io --reales   # 20 sitios reales
```

La misma tarea `descargar` se corre en dos modos: secuencial (un `for` con
`await` adentro) y concurrente (`asyncio.gather`), tres veces cada uno. Se
reporta la mediana. Se usaron dos fuentes:

- **Servidor lento local** (servicio `lento` del compose): 20 URLs con demoras
  fijas entre 0,2 y 1,5 s, que suman **17,88 s** y la máxima es **1,32 s**. Es
  reproducible y aísla el efecto de la concurrencia.
- **20 sitios reales**: la situación real, con latencias que no controlo.

| Fuente | Secuencial | Concurrente | Speedup |
|--------|-----------:|------------:|--------:|
| Servidor lento | 18,07 s (18,07 · 18,07 · 18,05) | 1,35 s (1,35 · 1,35 · 1,35) | **13,4x** |
| Sitios reales | 4,50 s (7,90 · 4,50 · 3,80) | 1,69 s (1,69 · 1,66 · 1,73) | **2,7x** |

**Interpretación.**

Con el servidor lento, el secuencial tardó 18,07 s: la suma de las demoras
(17,88 s) más unos 10 ms por request. Cada `await` espera la respuesta antes de
pedir la siguiente URL. El concurrente tardó 1,35 s, prácticamente la demora
máxima (1,32 s), y en las tres corridas la descarga más lenta fue justamente
esa URL. Las 20 requests salen juntas: mientras una espera la red, el loop
atiende a las demás, así que el total lo marca **la más lenta**, no la suma. El
speedup medido (13,4x) coincide con el teórico (17,88 / 1,32 = 13,5x).

Esa es la diferencia entre `gather` y un `for` con `await`: con el `for`, la
corrutina se suspende en cada descarga y no lanza la siguiente hasta volver;
con `gather` las 20 están suspendidas **a la vez**.

Con sitios reales el speedup baja a 2,7x, y la razón es la misma regla: en las
seis corridas el sitio más lento fue `www.um.edu.ar` (~1,65 s), y el
concurrente tarda casi exactamente eso. Los otros 19 sitios responden rápido,
así que la suma del secuencial es chica (4,5 s) y un solo sitio pesa más de un
tercio del total. Cuanto más parejos son los tiempos, más gana la concurrencia.

La primera corrida secuencial (7,90 s) fue más lenta que las otras dos porque
arranca en frío: resolución DNS y apertura de conexiones TLS. Después el
`AsyncClient` compartido reutiliza las conexiones (keep-alive).

**Un caso que encontré de casualidad.** En la primera versión de la lista
estaba `www.gnu.org`, que no respondió nunca: las seis corridas cortaron con
`ConnectTimeout` a los 15 s (`TIMEOUT_HTTP`). El resultado fue secuencial
22,36 s y concurrente **15,02 s**, un speedup de 1,5x. El concurrente tardó
exactamente el timeout: la tarea no termina hasta que termina su descarga más
lenta, aunque sea una que va a fallar. El error quedó reportado en el resultado
de esa URL sin cortar la tarea. Lo reemplacé por `www.rust-lang.org` para la
medición limpia; los datos de esa corrida quedaron en
`resultados/io_reales_20261024_172831.json`.

### 4.2 El event loop bloqueado

```bash
USAR_EXECUTOR=false docker compose up --build   # hash dentro del loop (mal)
python3 mediciones/medir.py loop --iteraciones 30000000
# Ctrl+C, y después:
docker compose up --build                       # hash en el executor (bien)
python3 mediciones/medir.py loop --iteraciones 30000000
```

Se manda un `hashear` de 30 millones de iteraciones y, mientras corre, el
script hace un `GET /tareas` cada 50 ms, cada uno esperando al anterior. Se
mide cuánto tarda en responder cada uno.

| Modo | Duración del hash | `GET /tareas` en reposo | GET atendidos durante el hash | Latencia prom. | Latencia máx. |
|------|------------------:|------------------------:|------------------------------:|---------------:|--------------:|
| Sin `run_in_executor` | 5,42 s | 1,0 ms | **1** | 5415,9 ms | **5415,9 ms** |
| Con `run_in_executor` | 5,32 s | 3,4 ms | **93** | 4,7 ms | **6,3 ms** |

**Interpretación.**

Sin executor, en 5,42 segundos de hash la API atendió **un solo request**, y
ese request tardó 5415,9 ms: toda la duración del hash. El `POST` había
respondido en 1,2 ms (antes de que el worker arrancara el cálculo); el
siguiente `GET` llegó cuando el loop ya estaba adentro del `for` del hash. La
conexión llega igual y el kernel la acepta, pero queda esperando en el socket,
porque el loop no vuelve a preguntarle a `epoll` qué sockets tienen datos
hasta que el hash termina (clase 17). Desde afuera, el servidor estuvo colgado
cinco segundos y medio: tampoco se habría disparado un timeout ni atendido un
`DELETE`.

Con executor, durante 5,32 segundos de hash se atendieron **93 requests** y el
peor tardó 6,3 ms, del mismo orden que con la API en reposo. Es casi mil veces
menos latencia (5415,9 ms contra 6,3 ms).

El hash no se hizo más rápido: tardó lo mismo en los dos casos (5,42 s contra
5,32 s). Una sola tarea va bloque por bloque, así que usa un proceso por vez y
no gana paralelismo. Lo que cambió es **quién espera**: sin executor, todo el
servidor espera al hash; con executor, solo espera el worker que lo pidió.

### 4.3 Techo del pool

```bash
docker compose up --build                      # 4 workers
python3 mediciones/medir.py techo --tipo esperar
python3 mediciones/medir.py techo --tipo hashear
# Ctrl+C, y después:
N_WORKERS=1000 docker compose up --build
python3 mediciones/medir.py techo --tipo esperar --niveles 1,64,256,1000
python3 mediciones/medir.py techo --tipo hashear --niveles 1,4,8,12,16,24,48 --iteraciones 5000000
```

Se mandan k tareas de golpe y se mide el tiempo total (de la primera creada a
la última terminada), cuánto esperaron en la cola y cuánto tardaron
ejecutándose. Hay que mirar las dos últimas columnas: dicen **dónde** se
espera.

**`esperar` 1 s, con 4 workers:**

| Tareas | Tiempo total | Ideal ⌈k/4⌉ s | Espera en cola (prom.) | Ejecución (prom.) | Tareas/s |
|-------:|-------------:|--------------:|-----------------------:|------------------:|---------:|
| 1 | 1,01 s | 1 s | 0,00 s | 1,01 s | 1,0 |
| 2 | 1,00 s | 1 s | 0,00 s | 1,00 s | 2,0 |
| 4 | 1,01 s | 1 s | 0,00 s | 1,00 s | 4,0 |
| 8 | 2,02 s | 2 s | 0,50 s | 1,01 s | 4,0 |
| 16 | 4,02 s | 4 s | 1,50 s | 1,00 s | 4,0 |
| 32 | 8,03 s | 8 s | 3,50 s | 1,00 s | 4,0 |
| 64 | 16,07 s | 16 s | 7,51 s | 1,00 s | 4,0 |

**`esperar` 1 s, con 1000 workers:**

| Tareas | Tiempo total | Ideal | Espera en cola (prom.) | Ejecución (prom.) | Tareas/s |
|-------:|-------------:|------:|-----------------------:|------------------:|---------:|
| 1 | 1,01 s | 1 s | 0,00 s | 1,00 s | 1,0 |
| 64 | 1,03 s | 1 s | 0,00 s | 1,00 s | 62,1 |
| 256 | 1,11 s | 1 s | 0,00 s | 1,00 s | 231,2 |
| 1000 | 1,33 s | 1 s | 0,00 s | 1,00 s | 753,8 |

**`hashear` 10⁶ iteraciones, con 4 workers (y 12 procesos en el executor):**

| Tareas | Tiempo total | Espera en cola (prom.) | Ejecución (prom.) | Tareas/s |
|-------:|-------------:|-----------------------:|------------------:|---------:|
| 1 | 0,19 s | 0,00 s | 0,19 s | 5,1 |
| 2 | 0,18 s | 0,00 s | 0,18 s | 11,1 |
| 4 | 0,20 s | 0,00 s | 0,20 s | 20,0 |
| 8 | 0,40 s | 0,10 s | 0,20 s | 20,2 |
| 16 | 0,79 s | 0,29 s | 0,20 s | 20,3 |
| 32 | 1,57 s | 0,68 s | 0,20 s | 20,4 |
| 64 | 3,15 s | 1,46 s | 0,20 s | 20,3 |

**`hashear` 5·10⁶ iteraciones, con 1000 workers (y 12 procesos):**

| Tareas | Tiempo total | Espera en cola (prom.) | Ejecución (prom.) | Tareas/s |
|-------:|-------------:|-----------------------:|------------------:|---------:|
| 1 | 0,91 s | 0,00 s | 0,91 s | 1,1 |
| 4 | 1,01 s | 0,00 s | 1,00 s | 4,0 |
| 8 | 1,03 s | 0,00 s | 1,02 s | 7,8 |
| 12 | 1,34 s | 0,00 s | 1,29 s | 8,9 |
| 16 | 1,79 s | 0,00 s | 1,71 s | 8,9 |
| 24 | 2,61 s | 0,00 s | 2,55 s | 9,2 |
| 48 | 5,22 s | 0,01 s | 5,10 s | 9,2 |

**Interpretación.** No hay un solo techo: según el tipo de tarea y la
configuración, el límite está en un lugar distinto, y las columnas de cola y
ejecución dicen cuál es.

1. **`esperar` con 4 workers: el techo es `N_WORKERS`.** Hasta 4 tareas todo
   tarda 1 s. Desde ahí el total sigue exacto a ⌈k/4⌉ s (16,07 s para 64
   tareas, contra 16 s ideal), las tareas/s quedan clavadas en 4,0 y la
   ejecución de cada tarea sigue siendo 1,00 s. Lo único que crece es la
   **espera en la cola** (hasta 7,51 s). El límite no es asyncio ni la CPU (un
   `sleep` no gasta nada): es la cantidad de workers que configuré.

2. **`esperar` con 1000 workers: el techo pasa a ser el loop mismo.** Con
   workers de sobra, la cola queda en 0 y la ejecución en 1,00 s incluso con
   1000 tareas: 1000 corrutinas durmiendo a la vez no le cuestan nada al loop.
   Lo que sí crece es el total (1,33 s para 1000), porque un solo hilo tiene
   que recibir cada `POST`, parsear el HTTP, validar con Pydantic y responder:
   en mi máquina, unas 750 tareas por segundo. Parte de ese límite es también
   el cliente de medición, que manda los `POST` desde 32 threads.

3. **`hashear` con 4 workers: otra vez el techo son los workers, no la CPU.**
   Con 12 procesos disponibles, las tareas/s se estancan en ~20, que es
   exactamente 4 workers / 0,2 s por tarea. Ocho de los doce procesos quedan
   ociosos: el pool de corrutinas es el que limita cuántos hashes se piden a la
   vez. La espera crece en la cola, y la ejecución se mantiene en 0,20 s.

4. **`hashear` con 1000 workers: el techo son los núcleos.** Ahora la cola
   queda en 0 (siempre hay un worker libre), pero desde 12 tareas la
   **ejecución** empieza a crecer: 1,29 s, 2,55 s, 5,10 s. La tarea figura
   `ejecutando`, pero sus bloques están esperando turno dentro del executor.
   Las tareas/s se estancan en ~9. Con 12 procesos y 0,91 s por tarea, el
   ideal serían ~13; queda en 9 porque el M4 Pro tiene 8 núcleos de
   rendimiento y 4 de eficiencia, mucho más lentos, y además Docker corre en
   una máquina virtual. Agregar workers ya no sirve: el cuello es la CPU
   física.

La conclusión de las cuatro tablas: para I/O, el límite es configuración (los
workers) y después el propio loop; para CPU, el límite son los núcleos, y la
cantidad de workers útil es aproximadamente la de procesos del executor.

---

## 5. Conceptos del curso aplicados

| Concepto | Dónde está | Clase |
|----------|-----------|-------|
| Productor-consumidor | `POST /tareas` produce, los workers de `pool.py` consumen de la `asyncio.Queue`. Es el patrón de la clase 11 con corrutinas en vez de threads: no hace falta Lock porque el loop no interrumpe entre `await`s | 11, 21 |
| El event loop como multiplexor | uvicorn corre sobre un loop que usa `epoll` por debajo. La medición 2 muestra qué pasa cuando el loop no vuelve a consultarlo | 17 |
| Corrutinas y puntos de suspensión | Cada `await` es como el `yield` del scheduler cooperativo: ahí la corrutina cede el control. Por eso `time.sleep()` en una corrutina es un bug (frena el hilo entero) y `asyncio.sleep()` no (suspende solo esa corrutina) | 18 |
| API HTTP con FastAPI | `main.py`: endpoints `async`, modelos Pydantic, códigos 202/404/409/422/503, `lifespan` para los recursos | 19 |
| I/O de red concurrente | `descargar.py`: `gather` contra `for` con `await`, un cliente compartido | 20 |
| Timeouts y cancelación | `asyncio.timeout()` en `_correr`, `task.cancel()` en el `DELETE`, `CancelledError` propagándose a las corrutinas hijas | 20, 21 |
| Executors | `hashear.py`: `run_in_executor` con `ProcessPoolExecutor`; `registro.py`: `asyncio.to_thread` para escribir el JSON | 21, 22 |
| Futures y pickle | `run_in_executor` devuelve un future; la función del hash está a nivel de módulo porque viaja pickleada al otro proceso | 9, 22 |
| GIL: threads contra procesos | por qué el hash va a procesos y no a threads | 10, 21 |
| Señales | handler de SIGINT/SIGTERM que solo cambia un flag (reentrancia: un handler puede correr en cualquier momento) | 6, 20 |
| Docker | `Dockerfile` con `CMD` en forma exec (PID 1 recibe SIGTERM), compose con dos servicios en la misma red | 1, 2 |

---

## 6. Limitaciones conocidas

- **Cola sin límite.** Si llegan 10.000 tareas de golpe, se aceptan todas: no
  hay backpressure. Lo primero que se degrada es la latencia de la API, porque
  el loop tiene que atender esos 10.000 `POST` uno por uno, y después la
  memoria. Con `asyncio.Queue(maxsize=...)` se podría responder `503` cuando
  se llena.
- **`GET /tareas` sin paginación.** Serializa todas las tareas en el hilo del
  loop; con decenas de miles de tareas, ese mismo request frena al resto.
- **El registro nunca borra tareas.** Crece mientras el servidor esté vivo.
- **Cancelar una pendiente no la saca de la cola**: queda ocupando lugar hasta
  que un worker la descarta.
- **`hashear` se cancela por bloques**: el bloque que ya estaba en el proceso
  termina igual (unos 0,2 s de trabajo desperdiciado).
- **Con `USAR_EXECUTOR=false`** no andan ni el timeout ni la cancelación del
  hash: el loop está bloqueado y no puede disparar nada. Es a propósito, para
  la medición 2.
- **`descargar` lee cada respuesta entera en memoria** para medir su tamaño.
  Un archivo muy grande la ocupa toda.
- **El volcado no se recarga**: al arrancar solo se reporta. Las tareas que
  quedaron `pendiente` no se retoman. Si el proceso muere con SIGKILL, no hay
  volcado.
- **Sin supervisión de workers**: si un worker muriera por un bug fuera de la
  tarea (no por un error de la tarea, que sí está cubierto), no se relanza.
- **Sin autenticación ni límite por cliente.**

---

## 7. Lo que aprendí

Lo que más me costó entender es que en asyncio todo corre en un solo hilo y que eso funciona solo porque cada corrutina "suelta" el control en los `await`. Lo leí en las clases, pero recién lo entendí cuando medí el loop bloqueado: con el hash dentro del loop, durante 5,4 segundos la API atendió un solo request, y ese request tardó exactamente lo mismo que el hash. No es que la API estuviera lenta: estuvo literalmente congelada, y desde afuera no había forma de distinguirla de un servidor caído. Con el executor el hash tardó lo mismo, pero se atendieron 93 requests en ese tiempo. Ahí entendí que el executor no hace más rápido el cálculo, sino que cambia quién tiene que esperarlo.

Algo que no esperaba fue que las mediciones mostraran cosas que no había pensado. Cuando medí con sitios reales, gnu.org no respondía nunca y la descarga concurrente tardó 15 segundos, justo el timeout: la tarea no termina hasta que termina su descarga más lenta, aunque sea una que va a fallar. También me sorprendió que con 4 workers y 12 procesos el sistema no usara ni la mitad de la CPU: el límite no lo ponía el procesador sino cuántos workers había configurado. Y cuando subí a 1000 workers, el techo pasó a ser los núcleos, pero no los 12 que esperaba, porque mi procesador tiene núcleos de rendimiento y de eficiencia que no rinden igual. Aprendí que el "techo" de un sistema no es un número fijo, sino que depende de qué tipo de trabajo le das.

Comparando con el TP1, la forma de pensar la concurrencia es casi la opuesta. En el TP1 todo eran procesos separados, cada uno con su memoria, y para compartir datos necesitaba un Manager o pipes, y las señales podían llegar en cualquier momento. Acá todo comparte la misma memoria y no necesito ningún Lock, porque sé exactamente dónde se puede cortar mi código: solo en los `await`. Eso lo hace más fácil de razonar, pero también más frágil, porque un solo `time.sleep()` o un cálculo largo traba todo el servidor. Si lo tuviera que hacer de nuevo, le pondría un límite a la cola desde el principio, porque hoy aceptaría 10.000 tareas de golpe sin quejarse.

