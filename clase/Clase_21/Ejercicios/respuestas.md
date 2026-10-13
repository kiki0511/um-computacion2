# Clase 21: Asyncio avanzado — Respuestas

Preparación (Python 3.11+, por `TaskGroup` y `except*`): `pip install fastapi uvicorn httpx`

| Archivo | Qué cubre |
|---------|-----------|
| `ej1_cola.py` | Reparto entre workers, `task_done`/`join`, backpressure, centinela contra cancelación, `PriorityQueue` |
| `ej2_grupos.py` | `ExceptionGroup`, `except*` contra `except`, `gather` contra `TaskGroup` caso por caso |
| `ej3_executor.py` | **Obligatorio**, partes A, B y C: loop bloqueado, threads contra procesos, costo de los procesos |
| `ej3d_api_hashear.py` | **Obligatorio**, parte D: la medición 2 del TP2 en una API FastAPI |
| `ej4_sincronizacion.py` | `asyncio.Lock`, `Semaphore` contra `Queue`, `Event` |
| `ej5_esqueleto_tp2.py` | El esqueleto del TP2: cola, pool, workers, cancelación y apagado. `--probar` recorre todos los casos |
| `ej_extra_adicionales.py` | Reintentos con backoff, `/estadisticas`, prioridad sin inanición, atraso del loop en vivo |

El ejercicio 3 pide **números propios**: los huecos `___` se llenan corriendo `ej3_executor.py` y `ej3d_api_hashear.py --medir` en la Mac. Los dos scripts imprimen al final una tabla lista para pegar acá.

---

## Ejercicio 1: La cola

### 1.1 El reparto

| Workers | Tiempo | Ideal | Reparto |
|---------|--------|-------|---------|
| 3 | 0.21 s | 0.20 s | 4 / 4 / 4 |
| 6 | 0.10 s | 0.10 s | 2 / 2 / 2 / 2 / 2 / 2 |

1. Con 12 tareas de 0.05 s y 3 workers tarda **0.21 s**. Secuencial habría tardado **0.60 s** (12 × 0.05).
2. Quedó **parejo, 4 / 4 / 4**, pero no siempre es así. Sale parejo porque todas las tareas duran lo mismo y los workers vuelven a `get()` en el mismo orden. Con duraciones distintas (0.01 s a 0.12 s) el reparto fue **3 / 6 / 3**: el worker que termina antes vuelve antes a la cola y se lleva más trabajo. El reparto es **dinámico** (lo toma quien está libre), no un round-robin fijo, y eso es justamente lo que conviene.
3. Con 6 workers tarda **0.10 s**, la mitad. Acá da justo porque 12 / 6 = 2 rondas exactas. En general no se reduce exactamente a la mitad:
   - Hay overhead fijo que no se reparte: planificar las corrutinas, los `put`/`get` y la resolución del timer.
   - La división puede no ser exacta. Con 13 tareas, 6 workers hacen 3 rondas, no 2.17.
   - Con trabajo real, los workers compiten por el recurso de abajo (red, CPU del executor).

### 1.2 task_done

4. Sin `task_done()`, **`join()` se cuelga para siempre**. Al segundo la cola está vacía (`qsize() = 0`) pero el contador interno de pendientes sigue en **12**.
5. La cola lleva un contador de **tareas sin terminar** (`_unfinished_tasks`):
   - `put()` lo **sube** en 1.
   - `get()` **no lo toca**: sacar un ítem no es terminarlo.
   - `task_done()` lo **baja** en 1.
   - `join()` espera a que ese contador llegue a **0** (internamente, un `Event` que se setea en ese momento).

   Por eso `qsize()` y "pendientes" son cosas distintas: una cuenta lo que está en la cola, la otra lo que no se terminó.
6. Va en un `finally` porque, si `procesar()` lanza una excepción (o cancelan al worker), la línea de después **no se ejecuta**. El contador nunca baja y `join()` queda colgado. Con `task_done()` después de `procesar()` y una tarea que falla, el contador quedó en **1** y `join()` no volvió.

### 1.3 Backpressure

| maxsize | Tiempo del productor (10 ítems) | `put()` que esperaron |
|---------|---------------------------------|-----------------------|
| 2 | 0.35 s | 7 / 10 |
| 100 | 0.00 s | 0 / 10 |

7. Con `maxsize=2` el productor tarda **0.35 s**; con `maxsize=100`, **0.00 s**.
8. Está esperando **en `await cola.put(i)`**. Con la cola llena, `put()` suspende al productor en un Future interno hasta que un `get()` libera un lugar. Va al ritmo del consumidor: 7 de los 10 `put()` tuvieron que esperar.
9. Con cola infinita, **la memoria crece sin límite**, lineal con los pedidos. Medido con `tracemalloc`, 10.000 pedidos de 1 KB ocupan **12.9 MB**; con un millón serían ~1.3 GB y el proceso muere por OOM. Pasa además algo peor antes de eso: la latencia también crece sin límite, porque el pedido 10.000 espera a que se procesen los 9.999 anteriores. Con `maxsize=100` quedan 100 en cola (**0.12 MB**) y se rechazan 9.900.
10. **`503 Service Unavailable`**, con un header `Retry-After`. Significa "estoy sobrecargado, es temporal, probá después". Si el límite fuera por cliente (rate limiting) correspondería **`429 Too Many Requests`**. En la API hay que usar `put_nowait()` y atrapar `asyncio.QueueFull`. Un `await cola.put()` dejaría el POST colgado esperando lugar, y el TP2 pide que el POST responda al instante.

### 1.4 Apagado

| Modo | Tiempo de apagado | Tareas completas | Cortadas a la mitad |
|------|-------------------|------------------|---------------------|
| Cancelar | 0.00 s | 3 | t3, t4, t5 |
| Centinela | 0.15 s | 6 | ninguna |

11. **Cancelar** es instantáneo pero brutal: cada worker recibe un `CancelledError` en el `await` donde esté, aunque sea a mitad de una tarea. Con **centinela**, el worker sale solo cuando lo saca de la cola. Como la cola es FIFO, el centinela llega después de todo el trabajo que ya estaba encolado: terminan lo que tenían y se retiran.
12. La tarea que estaba procesando **se corta a la mitad**: el `CancelledError` aparece en su `await`, corre el `finally` (que hace el `task_done()`) y el trabajo se pierde. No vuelve a la cola ni queda registrado como terminado. En el TP2 hay que decidir qué hacer con ella: marcarla `cancelada`, o re-encolarla si se quiere retomar.
13. Porque **cada centinela lo consume un solo worker**, y ese worker hace `return`: no vuelve a leer, así que no puede "pasarlo". Con un solo centinela para 3 workers, **salió 1 y los otros 2 siguen bloqueados en `get()`** para siempre.

### 1.5 Prioridades

14. Con `asyncio.PriorityQueue` y tuplas `(prioridad, tarea)` sale primero el **número más chico**: `['urgente' (1), 'normal' (3), 'cuando puedas' (5)]`.
15. Con dos tareas de igual prioridad, el segundo `put` da:

    `TypeError: '<' not supported between instances of 'dict' and 'dict'`

    La cola es un heap que compara las tuplas elemento por elemento. Si la prioridad empata, pasa a comparar el segundo elemento, y dos `dict` no se pueden comparar. Se arregla con un **desempate único**: `(prioridad, contador, tarea)` con `itertools.count()`. El contador nunca empata, así que nunca se llega a comparar la tarea, y de paso mantiene el **orden FIFO** entre tareas de igual prioridad. Si las tareas fueran strings no daría error, pero el bug sería peor por silencioso: se ordenarían alfabéticamente.
16. **Inanición** (starvation), el mismo problema de readers-writers de la clase 11, donde los lectores podían dejar a un escritor esperando para siempre. Con urgentes llegando cada 0.04 s y un worker que tarda 0.05 s, en 1.5 s se atendieron **29 urgentes y la de baja prioridad nunca salió**. La solución (envejecimiento) está en `ej_extra_adicionales.py`.

---

## Ejercicio 2: Grupos de tareas

Preguntas 1 a 4, con la salida de `grupos.py`:

1. Con `gather`, **la tarea A sigue corriendo** después de que falla la otra. `gather` propaga la primera excepción a quien lo esperaba, pero **no cancela** a las demás: A queda huérfana, sin nadie que la espere.
2. Con `TaskGroup`, **B se cancela** (imprime `B: me cancelaron`). La canceló **el propio `TaskGroup`**: cuando una tarea del grupo falla, cancela a todas las hermanas que siguen corriendo y no sale del `async with` hasta que terminaron.
3. Porque en un servidor que corre semanas, cada huérfana es una fuga: memoria, sockets abiertos, conexiones a la base, CPU. Además nadie va a leer su resultado ni su excepción, así que un error ahí se pierde (como mucho aparece un `Task exception was never retrieved` en el log). Con miles de pedidos, se acumula hasta que el servidor se cae.
4. Porque `except*` no elige **una** rama: cada rama se queda con **la parte del grupo** que coincide con su tipo, y lo que sobra sigue a la rama siguiente. El grupo tenía un `ValueError` y un `TypeError`, entonces entró a las dos. Un `except` común elige la primera rama que coincide con el objeto entero y no mira las demás.

### 2.1 ExceptionGroup (`ej2_grupos.py`)

5. Con tres tareas que fallan con `ValueError` al mismo tiempo, **llegan las tres** a `eg.exceptions`: `['falló la 0', 'falló la 1', 'falló la 2']`. El grupo junta todas las excepciones que ocurrieron antes de que la cancelación alcanzara a las demás.
6. Depende de qué se ponga en el `except`:
   - `except ValueError:` **no lo captura**, porque lo que sale es un `ExceptionGroup`, no un `ValueError`.
   - `except ExceptionGroup as eg:` **sí lo captura**, porque `ExceptionGroup` es una subclase de `Exception` como cualquier otra. Lo que se pierde es el filtrado por tipo: hay que recorrer `eg.exceptions` a mano, o usar `eg.split(ValueError)`, que separa el grupo en lo que coincide y el resto (es lo que `except*` hace por debajo).

### 2.2 Cuál usar

7. Cada caso, con su elección:

| Caso | Elección | Por qué |
|------|----------|---------|
| 10 URLs; si una falla quiero las otras 9 | `gather(..., return_exceptions=True)` | Las fallas no tienen que cancelar a nadie. Se devuelven mezcladas con los resultados (en la demo: 9 bien, 1 con error) |
| Conexión a la base + el worker que la usa | `TaskGroup` | Viven y mueren juntas: si se cae la conexión, el worker no tiene sentido y el grupo lo cancela (en la demo: `worker cancelado`) |
| 4 workers que viven lo que el servidor | Ninguno de los dos "a secas": `create_task` en el `lifespan`, guardando las referencias | Cada worker atrapa sus propios errores para no morirse. Un `TaskGroup` tiraría todo el servidor abajo ante un solo error. `gather` no sirve porque no se espera un resultado: se espera que vivan |
| Lote donde si uno falla el lote es inválido | `TaskGroup` | Al primer error cancela a las que faltan y no se gasta trabajo en un lote que ya no sirve (en la demo, el ítem 2 falla y solo terminaron el 0 y el 1) |

8. `TaskGroup` no devuelve resultados: **se guardan las `Task` que devuelve `create_task()`** y, afuera del `async with` (donde ya terminaron todas), se lee `.result()` de cada una.

---

## Ejercicio 3: Sacar el trabajo del loop (obligatorio)

Para correrlo en la Mac:

```bash
python3 ej3_executor.py            # partes A, B y C (~1 minuto)
python3 ej3d_api_hashear.py --medir # parte D
```

### Parte A: el loop bloqueado

1. Con `VUELTAS = 3.000.000`:

| Forma | Duración | Peor atraso del loop |
|-------|----------|----------------------|
| Sin executor | ___ s | ___ ms |
| `ProcessPoolExecutor` | ___ s | ___ ms |
| `asyncio.to_thread` | ___ s | ___ ms |

2. Sin executor, **el atraso es prácticamente toda la duración del cálculo**: ___ ms. Durante ese lapso el loop no ejecuta nada más. En un servidor eso significa que no se aceptan conexiones nuevas, no se responde ningún pedido (ni un `GET` trivial), no se disparan los timeouts y no avanza ninguna otra corrutina. Desde afuera, el servidor parece caído durante ese tiempo.
3. Mejoró **la disponibilidad del loop**, no el cálculo. El trabajo tarda lo mismo porque es la misma CPU haciendo las mismas vueltas, pero corre en otro lado, y el loop queda libre (atraso de pocos ms) para seguir atendiendo a todos los demás mientras tanto. Es la diferencia entre concurrencia y velocidad: el cliente que pidió el hash espera lo mismo, pero los otros ya no esperan por él.
4. Porque un `sleep(0.05)` es un timer, y el timer solo se dispara si el loop está libre para atenderlo. Si el loop vuelve a tiempo, el atraso es casi 0. Cualquier demora extra es tiempo en que el loop estuvo ocupado con algo que no cedía el control. Mide justo lo que importa (cuánto tarda el loop en atender un callback listo) sin depender de la red ni del cliente. No sirve medir la duración del cálculo, porque esa no cambia. Es la métrica de "loop lag" que se usa en producción.

### Parte B: threads contra procesos

5. Con 4 tareas CPU-bound simultáneas:

| Caso | Threads | Procesos |
|------|---------|----------|
| 4 tareas CPU | ___ s | ___ s |
| 1 tarea CPU | ___ s | ___ s |
| 4 tareas I/O (`time.sleep(2)`) | ___ s | ___ s |

6. Por el **GIL** (clase 10): dentro de un proceso, un solo thread a la vez ejecuta bytecode de Python. Los 4 threads se turnan, así que tardan ≈ 4 veces lo que tarda una tarea. `hashlib` suelta el GIL solo con entradas de más de ~2 KB, y acá cada vuelta hashea 32 bytes, así que no lo suelta. Cada proceso tiene su propio intérprete y su propio GIL, y con 4 núcleos o más corren de verdad en paralelo: tardan ≈ lo mismo que una sola tarea.
7. Con una sola tarea **no hay competencia por el GIL**: el único thread que calcula lo tiene casi todo el tiempo (el loop casi no lo pide, porque está esperando). Los procesos pagan el pickle y el viaje por el pipe, pero eso es despreciable frente a segundos de cálculo. Los dos tardan ≈ lo que tarda el cálculo.
8. Con `time.sleep` **dejan de diferenciarse**: los dos tardan ≈ 2 s. `time.sleep` suelta el GIL mientras espera, así que los threads esperan en paralelo. Para I/O bloqueante los threads alcanzan y son más baratos que los procesos. Para CPU-bound hacen falta procesos.

### Parte C: el costo de los procesos

9. Da un error de pickle. En Python 3.13: `AttributeError: Can't get local object 'parte_c.<locals>.<lambda>'`; en versiones anteriores, `PicklingError: Can't pickle <function <lambda>>`. Pasa porque `ProcessPoolExecutor` manda la función y sus argumentos al proceso hijo **pickleados** por un pipe. Una función se picklea **por referencia** (módulo + nombre) y el hijo la vuelve a importar. Una `lambda`, o una función definida adentro de otra, no tiene un nombre importable. Por eso las funciones del executor tienen que estar a nivel de módulo.
10. Comparación de lo que cuesta cada viaje al pool:

| Argumento | Tiempo por llamada |
|-----------|--------------------|
| Un número | ___ ms |
| Lista de 1 millón de números (~4.9 MB pickleados) | ___ ms |
| Referencia: `sum()` de esa lista en el mismo proceso | ___ ms |

   El argumento se serializa, viaja por el pipe y se deserializa en el hijo: el costo crece con el tamaño. Con la lista grande, **el viaje cuesta más que el cálculo**. Conviene mandar poco (un nombre de archivo, un rango) y que el hijo consiga los datos, o mandar trabajo que valga el viaje.
11. Porque crear el pool es **crear procesos**. En macOS con `spawn` eso es arrancar un intérprete nuevo e importar el módulo entero, decenas de ms. Medido:

| | Tiempo por tarea |
|-|------------------|
| Pool nuevo por tarea | ___ ms |
| Pool reutilizado | ___ ms |

   Con el pool creado una vez en el `lifespan`, cada tarea solo paga el viaje de ida y vuelta.

### Parte D: en una API (`ej3d_api_hashear.py`)

12. `POST /hashear` es un `async def` que llama a `hashear()` directamente, sin executor.
13. y 15. Lanzando el POST pesado y midiendo `GET /tareas` mientras corre:

`GET /tareas` en reposo: ___ ms

| Endpoint | Duración del cálculo | Peor `GET /tareas` durante el cálculo |
|----------|----------------------|---------------------------------------|
| `/hashear` (sin executor) | ___ s | ___ ms |
| `/hashear-executor` | ___ s | ___ ms |
| `/hashear-sync` (`def`, para comparar) | ___ s | ___ ms |

   Sin executor, el `GET` tarda **lo que le falta al cálculo**: el pedido llega al socket, pero nadie lo lee hasta que el loop se libera. Con executor responde como en reposo.
14. Con `run_in_executor` y el `ProcessPoolExecutor` creado en el `lifespan`, el `GET` no se entera del cálculo.

   El endpoint `/hashear-sync` es un `def` común, y FastAPI lo corre en su threadpool. No congela el loop, pero comparte el GIL con él: el loop recibe turnos cada ~5 ms (el intervalo de cambio del GIL), así que el `GET` tarda algunos ms más que con procesos. Para CPU de verdad, procesos.

### Verificación

- [ ] Los tres tiempos y los tres atrasos, con números propios
- [x] Explicaste qué significa el atraso para un servidor
- [x] Explicaste qué mejora el executor si el trabajo tarda lo mismo
- [ ] Mediste threads contra procesos con 4 tareas CPU-bound
- [x] Explicaste la diferencia con el GIL
- [ ] Probaste qué pasa con una tarea sola y explicaste por qué empatan
- [x] Probaste el error de pasar una lambda al executor
- [ ] Hiciste la medición en una API real (parte D)

---

## Ejercicio 4: Sincronización async

### 4.1 Cuándo hace falta

1. La regla de la clase 20: hace falta un `asyncio.Lock` **solo cuando hay un `await` entre leer un estado compartido y escribirlo**. Entre dos `await`, una corrutina corre sin que nadie la interrumpa, porque el loop cambia de tarea únicamente en los `await`.
2. `incrementar()` **no necesita lock**: `contador += 1` no tiene ningún `await`, así que ninguna otra corrutina puede meterse en el medio. 100.000 llamadas concurrentes dieron **100.000**. Ojo: esto vale para corrutinas en el mismo loop. Si el contador lo tocaran threads, sí haría falta un `threading.Lock`.
3. `transferir()` **sí lo necesita**: entre `saldo = cuentas[a]` y `cuentas[a] = saldo - monto` hay un `await log(monto)`. Ahí el loop cambia de corrutina, y las otras leen el mismo saldo viejo.
4. Con 100 transferencias de $1 desde una cuenta con $1000:

| Versión | a | b | Total |
|---------|---|---|-------|
| Sin lock | 999 | 100 | **1099** |
| Con `asyncio.Lock` | 900 | 100 | 1000 |

   Sin lock, las 100 leyeron `saldo = 1000` y todas escribieron 999, así que **aparecieron $99**. Es la race condition de la clase 11, pero ahora el "cambio de contexto" está en un lugar que se puede ver: el `await`.

### 4.2 Semáforo contra cola

5. `Semaphore(5)` limita **cuántas corrutinas entran a una sección a la vez**. Las 20 tareas se crean de golpe y 15 quedan esperando en el semáforo. Con una `Queue` y 5 workers **existen solo 5 corrutinas**: el trabajo son datos que esperan en la cola, y los workers sobreviven al lote.
6. Cuándo conviene cada uno:
   - **`Semaphore`**: un lote fijo y conocido que se lanza con `gather` y del que se quieren los resultados en orden. También para limitar un recurso dentro de código que ya es concurrente, por ejemplo máximo 5 conexiones a la base desde los handlers de la API.
   - **`Queue` + workers**: trabajo que llega de forma continua (un servidor), cuando hace falta backpressure (`maxsize`), consumidores de vida larga o un apagado ordenado. Es el caso del TP2.
7. Con 20 URLs de 0.2 s contra un servidor local que cuenta los pedidos simultáneos:

| Versión | Tiempo | OK | Pico de pedidos simultáneos en el servidor |
|---------|--------|----|--------------------------------------------|
| `Semaphore(5)` | 0.98 s | 20/20 | 5 |
| `Queue` + 5 workers | 0.99 s | 20/20 | 5 |

   Las dos respetan el límite y tardan lo mismo (ideal: 4 rondas × 0.2 s = 0.8 s, más el costo de las conexiones). Para un lote así quedó **más clara la del semáforo**: menos código y `gather` devuelve los resultados en orden sin un diccionario aparte.

### 4.3 Event

8. Con un `Event`, los 3 workers quedan en `await listo.wait()` hasta que la inicialización hace `set()` a los 0.30 s, y ahí arrancan los tres juntos.
9. Si se llama `set()` antes de que alguien haga `wait()`, el `wait()` **vuelve al instante** (0.003 ms). Un `Event` es un **estado** (una bandera que queda en `True`), no una notificación. Es distinto de `Condition.notify()`, que se pierde si nadie está esperando en ese momento.
10. Se "desetea" con **`clear()`**, que vuelve la bandera a `False`, y los `wait()` siguientes se bloquean. Sirve para estados que van y vienen: pausar y reanudar, "hay conexión", "hay datos nuevos". En la demo, `clear()` pausa a un worker, pero la pausa toma efecto **en su próximo `wait()`**: la tarea que ya estaba haciendo la termina (pasó de 2 a 3 durante la pausa) y después se queda quieto hasta el `set()`.

---

## Ejercicio 5: El esqueleto del TP2

`ej5_esqueleto_tp2.py` cumple los 8 puntos del enunciado:

| Punto | Cómo |
|-------|------|
| 1. Partir de `api.py` (clase 19) | Mismos endpoints, modelo Pydantic y estructura |
| 2. Cola, pool y workers en el `lifespan` | `asyncio.Queue(maxsize=100)`, `ProcessPoolExecutor(2)`, 4 workers con `create_task` |
| 3. `POST` responde al instante | `put_nowait()` y **202 Accepted** ("lo recibí, todavía no lo hice"). Si la cola está llena, 503 con `Retry-After` |
| 4. Estados | `pendiente` → `ejecutando` → `completada` (además `fallida` y `cancelada`) |
| 5. `GET /tareas/{id}` | Devuelve el diccionario de la tarea con su estado |
| 6. `hashear` al executor, `esperar` al loop | `run_in_executor` contra `asyncio.sleep` |
| 7. `DELETE` cancela en ejecución | Cancela la `Task` que la ejecuta. Si está pendiente, la marca y el worker la saltea |
| 8. Apagado con centinela | Cancela las pendientes, un centinela por worker, espera hasta 10 s, cancela los que no salieron y cierra el pool |

Salida de `python3 ej5_esqueleto_tp2.py --probar` (3 workers):

```
POST esperar  {'segundos': 1}                          -> 202 id=1 en   2.1 ms
POST hashear  {'texto': 'tp2', 'iteraciones': 2000000} -> 202 id=2 en   1.6 ms
...
DELETE /tareas/4 -> 200 cancelada (estaba pendiente)
DELETE /tareas/3 -> 200 cancelada (estaba ejecutando)
DELETE /tareas/3 otra vez -> 409 La tarea ya está cancelada

tarea 1 esperar  completada   1.00s
tarea 2 hashear  completada   0.85s
tarea 3 esperar  cancelada    0.31s  cancelada por el usuario
tarea 4 esperar  cancelada        -  cancelada por el usuario
tarea 5 hashear  fallida      0.00s  ValueError: invalid literal for int() ...

SIGTERM con una tarea en curso: los workers libres se retiran, el ocupado
termina su tarea y se retira, el pool se cierra: "apagado ordenado completo"
```

Decisiones que conviene saber explicar (son las preguntas de corrección del TP2):

- **Por qué no hay `Lock`.** Todo el estado (`tareas`, `en_curso`) lo toca un solo thread, el del loop. Además, entre marcar `ejecutando` y registrar la `Task` en `en_curso` no hay ningún `await`, así que un `DELETE` nunca ve una a medias. La cola reparte el trabajo: es productor-consumidor (clase 11) sin estado compartido que proteger.
- **Por qué `await asyncio.wait({ejecucion})` y no `await ejecucion`.** `asyncio.wait` no propaga la cancelación de la tarea. Así el worker distingue "cancelaron la tarea", que viene de un `DELETE` y el worker sigue vivo, de "cancelaron al worker", que viene del apagado forzado y le llega como `CancelledError`.
- **Qué pasa si una tarea lanza una excepción.** Queda en `ejecucion.exception()` y la tarea pasa a `fallida` con el motivo. Si el error es un bug del propio worker, lo atrapa el `except Exception` del bucle y el worker sigue vivo. Si se muriera, la cola quedaría con un consumidor menos para siempre, sin que nadie se entere.
- **Cancelar un `hashear` en ejecución no detiene el proceso hijo.** Se cancela el Future que el loop está esperando y la tarea pasa a `cancelada`, pero el proceso del pool sigue calculando hasta terminar, y el resultado se descarta. No hay forma limpia de interrumpir un proceso del pool a la mitad. Es una **limitación conocida** que el TP2 pide documentar.
- **Las señales las maneja uvicorn.** Con Ctrl+C o `SIGTERM`, uvicorn ejecuta la parte del `lifespan` que está después del `yield`. Ahí va el apagado ordenado. En el TP2 se le suma el volcado a `estado_<timestamp>.json`.

Lo que falta para el TP2: la tarea `descargar` (httpx asíncrono), el timeout por tarea, `/estadisticas`, el volcado a JSON, Docker y las tres mediciones.

---

## Ejercicios adicionales (`ej_extra_adicionales.py --probar`)

### Workers con reintentos

El contador de intentos se guarda **en la propia tarea**, no en el worker, porque el reintento lo puede tomar cualquier otro worker. El worker no duerme durante el backoff (quedaría ocupado sin hacer nada): una tarea de fondo espera y la vuelve a encolar. Esa tarea se guarda en un `set` porque el loop solo mantiene una referencia débil a las tasks, y sin la referencia el recolector de basura la puede borrar a mitad de camino.

```
{'fallas': 2}: completada en 3 intentos, arrancó a los [0.0, 0.2, 0.6] s
{'fallas': 9}: fallida en 4 intentos, arrancó a los [0.0, 0.2, 0.6, 1.4] s
```

Las distancias entre intentos son 0.2, 0.4 y 0.8 s: el backoff exponencial.

### Estadísticas en vivo

`GET /estadisticas` devuelve tareas por estado, tamaño de la cola, workers ocupados, tiempo promedio de procesamiento y el atraso del loop:

```
{'por_estado': {'completada': 2, 'fallida': 1}, 'en_cola': 0, 'workers_ocupados': '0/1',
 'tiempo_promedio_s': 0.25, 'atraso_loop_ms': {'ultimo': 0.2, 'max_ultimo_segundo': 453.8, ...}}
```

### Cola con prioridad real, sin inanición

La clave de orden no es la prioridad sola sino un **plazo**: `llegada + (5 − prioridad) × ENVEJECIMIENTO`. Una tarea de prioridad alta adelanta a una baja, pero solo hasta `ENVEJECIMIENTO` segundos por nivel de diferencia. Pasado ese tiempo, la baja va antes que cualquier alta que llegue después. Tiene una ventaja sobre el envejecimiento "clásico", que recalcula prioridades periódicamente: la clave se calcula una vez al encolar y el heap funciona sin cambios.

Con 1 worker, una tarea de prioridad 1 y 15 de prioridad 5 llegando más rápido de lo que se atienden:

| | Posición de la tarea de prioridad 1 |
|-|-------------------------------------|
| Sin envejecimiento | 16ª de 16 (si las altas no paran, no sale nunca) |
| Con envejecimiento (0.25 s por nivel) | 11ª de 16 |

### Medir el loop en vivo

Una tarea de fondo hace `sleep(0.05)` en bucle y guarda el atraso en una `deque`, que `/estadisticas` expone. El tipo `bloquear` hace `time.sleep()` dentro del loop, mal a propósito: en reposo el atraso máximo fue **3.3 ms**, y después de un `bloquear` de 0.5 s subió a **453.8 ms**. Es la métrica que avisa, en producción, que algo está bloqueando el event loop.
