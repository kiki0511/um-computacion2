# Clase 18: De yield a asyncio — Respuestas

| Archivo | Qué cubre |
|---------|-----------|
| `ej2_scheduler.py` | **Obligatorio**: scheduler propio, tarea egoísta, `dormir()`, `yield from` |
| `ej1_3_4_5_generadores_asyncio.py` | `send()`, `StopIteration.value`, el puente, `gather`, bloqueos |
| `ej_extra_adicionales.py` | Prioridades, detector de tareas egoístas, pipeline con `send()` |

---

## Ejercicio 1: Generadores que reciben

1. `TypeError: can't send non-None value to a just-started generator`. El generador todavía no llegó a ningún `yield` que pueda recibir el valor.
2. El `next(a)` inicial devuelve `0`: corre hasta el primer `yield total` y entrega el `total` inicial.
3. `send(10)` da 10 (0+10), `send(5)` da 15, `send(7)` da 22. Cada `send(n)` hace que el `yield` devuelva `n` adentro, suma y vuelve a entregar el total en el próximo `yield`.
4. No comparten el `n`: cada generador tiene su propio contador (`g1` llegó a 2 y `g2` a 1).
5. `n` vive en el **frame** del generador (`gi_frame.f_locals`), que queda suspendido en el heap. En una función común, el frame se destruye al retornar.
6. Imprime `'resultado final'`. El `return` de un generador no vuelve al que llamó: se transporta en `StopIteration.value`, porque "llamar" a un generador solo crea el objeto y el valor aparece recién al agotarlo.
7. El scheduler captura `StopIteration` para saber que la tarea terminó y no reencolarla. Con `e.value` podría recoger su resultado, que es lo que hace `asyncio` para que `await` devuelva un valor.

## Ejercicio 2: Construir el scheduler (obligatorio)

**Parte A**

1. Con tareas de 3, 1 y 2 pasos el orden es round-robin: `A1 B1 C1 A2 (B termina) C2 A3 (C termina) (A termina)`.
2. `next()` se llamó **9 veces**: 6 pasos y 3 `StopIteration` (una por tarea).
3. Una "tarea" sin `yield` no es un generador. Al llamarla se ejecuta entera **antes** de entrar al scheduler y devuelve `None`, así que el scheduler falla con `TypeError: 'NoneType' object is not an iterator`.

**Parte B**

4. Durante los 3 s de `time.sleep(3)` **ninguna otra tarea avanzó**: A y C estaban en `0.00s` y siguieron recién en `3.00s`.
5. Con threads no habría pasado: el SO interrumpe un thread cuando quiere (concurrencia **preventiva**, *preemptive*). Acá cada tarea decide cuándo soltar el control (concurrencia **cooperativa**) y el scheduler no tiene forma de quitárselo.
6. La regla: **no bloquear el event loop**. Toda tarea tiene que ceder seguido. Es lo mismo del ejercicio 7 de la clase 17: un callback lento congela a todos.

**Parte C**

7. `dormir(segundos)` hace `yield time.monotonic() + segundos`: le dice al scheduler **cuándo** quiere volver. El scheduler usa un `heapq` ordenado por ese instante y solo él duerme (`time.sleep`) hasta el próximo despertar.
8. `dormir()` no puede llamar a `time.sleep()` porque bloquearía el único hilo y sería la tarea egoísta de la Parte B.
9. Tres tareas de 3, 2 y 4 pasos con 0.15 s cada uno tardan **0.60 s** en las tres corridas. La suma de las esperas daría 1.35 s. Las esperas se solapan: el total es el de la tarea más larga (4 × 0.15).

**Parte D**

10. `yield from dormir(espera)` **delega**: los `yield` de `dormir` suben directo al scheduler, y lo que el scheduler mande con `send()` baja a `dormir`. Llamar `dormir(espera)` a secas solo **crea** el generador.
11. Sin el `yield from`, el generador de `dormir()` se crea y se descarta sin ejecutarse. No falla ruidosamente porque crear un generador es válido. El síntoma: las tareas no esperan ni se intercalan (A corre sus 3 pasos seguidos, después B) y todo termina en 0.00 s. Es el mismo error que olvidarse el `await` en asyncio, que Python al menos avisa con un `RuntimeWarning`.

## Ejercicio 3: El puente a async/await

1. Una función `async def`, al llamarla, devuelve un objeto `coroutine` y **no** ejecuta nada de su cuerpo.
2. `hasattr(c, 'send')` es `True`, y `c.send(None)` lanza `StopIteration` con `value=99`.
3. Es el mismo mecanismo del 1.3: la corrutina es un generador con otra sintaxis, y el `return` viaja en `StopIteration.value`.
4. Que `await` funcione sobre un generador `@types.coroutine` demuestra que `await` es `yield from` con otro nombre. En la demo, el `yield 'pausa'` subió hasta quien hizo `send(None)`, y el `send('hola')` bajó como resultado del `await`.
5. En sintaxis moderna:
   ```python
   async def buscar(id):
       conn = await abrir()
       datos = await leer(conn, id)
       return datos
   ```
6. `async`/`await` resolvió dos problemas de `yield from`:
   - **Ambigüedad**: con `yield from`, un generador de datos y una corrutina se veían igual. Un `yield` suelto por error convertía una función en generador sin que nadie se enterara, y se podía hacer `yield from` de cualquier iterable. Con `async def` la corrutina es un tipo propio y `await` solo acepta *awaitables*.
   - **Legibilidad y herramientas**: `async def` marca la función como asíncrona desde la firma. Permite `async for` y `async with`, y que Python avise cuando una corrutina nunca se awaiteó.

## Ejercicio 4: asyncio de verdad

1. Mi `deque` y el `while pendientes` los reemplaza el **event loop** que crea `asyncio.run()`. Encolar tareas es `gather` (crea `Task`s) y ceder es `await asyncio.sleep(0)`.
2. Sin `await` delante de `gather`, `main` sigue de largo y termina, y `asyncio.run()` **cancela** lo que quedó pendiente al cerrar. En la demo, X alcanzó a dar un paso antes de la cancelación; sin marcar el futuro aparece `_GatheringFuture exception was never retrieved`.
3. Dos `asyncio.run()` seguidos **funcionan**: cada uno crea un loop nuevo y lo cierra al terminar. Adentro de una corrutina que ya corre: `RuntimeError: asyncio.run() cannot be called from a running event loop`.
4. `saludar()` a secas no imprime nada y da `RuntimeWarning: coroutine 'saludar' was never awaited`. Con `asyncio.run(saludar())` imprime `hola`.
5. Es lo mismo que con los generadores: crear uno sin `next()` no ejecuta nada.
6. Terminan en orden de duración: `b` (0.1 s), `c` (0.2 s), `a` (0.3 s).
7. `gather` devuelve `['a', 'b', 'c']`, en el orden en que se **pasaron**, no en el que terminaron.
8. `gather` con tres corrutinas de 1 s: **1.00 s**, porque corren concurrentes. El `for` con `await`: **3.00 s**, porque cada `await` espera a que termine la anterior antes de crear la siguiente.

## Ejercicio 5: Cuándo sirve y cuándo no

`comparar.py`:

| Caso | Tiempo |
|------|--------|
| I/O secuencial | 3.00 s |
| `gather` con `asyncio.sleep` | 1.00 s |
| `gather` con `time.sleep` | 3.00 s |
| CPU secuencial | 2.07 s |
| CPU `gather` | 1.93 s |

1. En I/O-bound asyncio mejora **×3**: 3.00 s a 1.00 s.
2. Con `time.sleep()` dentro de la corrutina tarda 3.00 s y no mejora nada: `time.sleep` no cede, bloquea el único hilo.
3. En CPU-bound da **igual** (2.07 s contra 1.93 s, ruido de medición). Hay un solo hilo haciendo el mismo trabajo total; no hay esperas que solapar.
4. En general asyncio es apenas más lento en CPU por el overhead de crear `Task`s, pasar por el loop y cambiar de contexto en cada `await`, sin nada que ganar a cambio. Acá la diferencia está dentro del ruido.
5. Regla: **asyncio conviene cuando el programa pasa la mayor parte del tiempo esperando I/O (red, disco) y hay muchas esperas simultáneas.**
6. Es el mismo criterio del GIL: threads sirven para I/O y no para CPU. Asyncio es la misma idea sin threads. Para CPU hacen falta procesos (`multiprocessing` o `ProcessPoolExecutor`).
7. Las cinco descargas con `urllib.request` no se solapan porque `urlopen().read()` es **bloqueante**: no hay ningún `await` donde ceder, así que corren una tras otra (en la simulación: 2.50 s contra 0.50 s).
8. En lugar de `urllib.request` hay que usar una biblioteca asíncrona: `httpx.AsyncClient` o `aiohttp`. Si no hay alternativa, `await asyncio.to_thread(...)`, que también da 0.50 s.
9. Tres llamadas bloqueantes que no van dentro de una corrutina:
   - `time.sleep()` (usar `await asyncio.sleep()`)
   - `requests.get()` o `urllib.request.urlopen()` (usar `httpx.AsyncClient`)
   - `socket.recv()` bloqueante, `open().read()` de archivos grandes o drivers de base de datos sincrónicos como `sqlite3`/`psycopg2` (usar `asyncio.open_connection`, `aiofiles`, `asyncpg`)

## Adicionales

- **Prioridades**: una `deque` no alcanza; hace falta un heap ordenado por "pase" (cada ejecución avanza `1/prioridad`). Con A=3 y B=1: `A1 B1 A2 A3 A4 B2 A5 A6 A7 B3 A8 A9`.
- **Tareas egoístas**: se mide cada `next()` y se avisa si supera el umbral (`⚠ mala tardó 300 ms sin ceder`). Es lo que hace `loop.set_debug(True)` con `slow_callback_duration`.
- **Leer el fuente**: `asyncio/tasks.py` define `__sleep0()` con `@types.coroutine` (un generador con un `yield` pelado) y lo usa `asyncio.sleep(0)`. La biblioteca lo necesita porque una corrutina `async def` **no puede** hacer `yield` para devolverle el control al loop. En la base de la cadena de `await` tiene que haber un generador que haga el `yield` real.
