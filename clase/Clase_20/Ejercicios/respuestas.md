# Clase 20: Asyncio en red — Respuestas

Preparación: `pip install httpx requests`

| Archivo | Qué cubre |
|---------|-----------|
| `ej3_descargas.py` | **Obligatorio**: secuencial vs `gather`, `requests` adentro, semáforo, ulimit, `return_exceptions` |
| `ej1_2_4_5_asyncio_red.py` | Eco lento, formas de leer, `drain`, locks, timeouts y cancelación |
| `ej_extra_adicionales.py` | Chat y servidor de comandos en asyncio, proxy asíncrono |

`ej3_descargas.py` usa por defecto un servidor HTTP local que tarda 0.3 s por pedido, para que los números no dependan de la conexión. Con `--real` descarga de `https://example.com`: corrélo así en tu Mac para tener los números de Internet.

---

## Ejercicio 1: El servidor eco

1. Con tres clientes conectados, `eco_async.py` reporta **1 thread**.
2. `server_threads.py` de la clase 14, con tres clientes, tiene 4 threads (uno por cliente más el principal).
3. En asyncio una conexión es un **objeto** (una `Task` con su `StreamReader`/`StreamWriter`); en la clase 14 era un **thread**.
4. Con `--lento`, el segundo cliente **no** espera al primero: dos clientes con 1 s de demora cada uno tardan **1.00 s** en total.
5. `await asyncio.sleep(3)` no congela a los demás porque cede el control al loop, que atiende a los otros clientes mientras tanto.
6. Con `time.sleep(demora)` los dos clientes tardan **2.00 s**: bloquea el único hilo y se atienden en serie.
7. Con `kill -TERM`, imprime `Cerrando: no se aceptan conexiones nuevas`. Al salir del `async with srv`, `asyncio.run()` cancela las tareas de los clientes: cada una imprime `<dirección> cancelada` y, desde su `finally`, `- <dirección> (conectados: N)`.
8. `loop.add_signal_handler()` no ejecuta el handler **en el momento** en que llega la señal (interrumpiendo cualquier línea, como `signal.signal()`): lo encola como un callback más del event loop, internamente con un self-pipe (`set_wakeup_fd`).
9. Importa por la async-signal-safety: el handler corre en un punto seguro, entre dos pasos del loop. Ahí puede hacer cualquier cosa (tocar estructuras, cerrar el servidor, crear tareas) sin riesgo de interrumpir una operación a medias. Es el patrón self-pipe de la clase 6, hecho por la biblioteca.

## Ejercicio 2: write, drain y el framing

1. `writer.write()` no lleva `await` porque solo copia los bytes al buffer del transporte, que es inmediato. `drain()` sí, porque **puede tener que esperar** a que el buffer baje del límite alto si el cliente no está leyendo.
2. Sin `await writer.drain()`, el servidor sigue funcionando con `nc`: con clientes que leen, el buffer se vacía solo.
3. `drain()` sirve para la **contrapresión** (backpressure). Con un cliente que manda 100 MB y nunca lee:

| | Pico del buffer de salida en el servidor |
|---|---|
| Sin `drain()` | **91 MB** |
| Con `drain()` | **0.1 MB** |

   Con `drain()`, el servidor deja de leer mientras no puede escribir, y el cliente queda frenado por el control de flujo de TCP.

4. Con un cliente que manda `'hola\nmundo\n'`:

| Llamada | Resultado |
|---------|-----------|
| `read(100)` | `b'hola\nmundo\n'` |
| `readline()` | `b'hola\n'` |
| `readexactly(4)` | `b'hola'` |
| `readuntil(b'\n')` | `b'hola\n'` |

5. Corresponden a los dos framings de la clase 13:
   - **Delimitador**: `readline()` y `readuntil()`.
   - **Longitud**: `readexactly(n)`, típicamente después de leer un prefijo con `struct`.
6. `readexactly(100)` con 11 bytes y cierre: `IncompleteReadError: 11 bytes read on a total of 100 expected bytes`. La excepción trae los bytes parciales en `.partial`.
7. `read()` con el cliente cerrado devuelve `b''`: es la señal de EOF, igual que `recv()` devolviendo `b''` en la clase 13.

## Ejercicio 3: Concurrencia de clientes (obligatorio)

**Parte A** (`descargas.py`, 12 descargas simuladas con suma de demoras de 5.7 s y la más lenta de 0.9 s)

| Modo | Tiempo |
|------|--------|
| Secuencial | 5.71 s |
| `gather` | 0.85 s |
| Semáforo de 4 | 1.55 s |
| Timeout de 0.8 s | 0.80 s, 1 cancelada |

1. `gather` tarda lo que la más lenta: todas arrancan juntas y las esperas se solapan, así que el total es el máximo, no la suma.
2. El semáforo da un tiempo intermedio: corren de a 4, así que son varias tandas y cada tanda tarda lo que su más lenta.
3. Con el timeout de 0.8 s se canceló **1** tarea. Esa tarea recibió `CancelledError` en su `await` pendiente, ejecutó su limpieza (`finally`) y terminó sin resultado.

**Parte B** (servidor local, 0.3 s por pedido)

4. 10 descargas: secuencial **3.50 s**, concurrentes con `gather` **0.36 s** (**×9.6**).
5. El `AsyncClient` se crea **una vez** porque mantiene un pool de conexiones: reutiliza conexiones TCP abiertas (keep-alive, clase 19) y se ahorra el handshake TCP, y el TLS en HTTPS, en cada descarga. Uno por descarga pagaría ese costo diez veces y no compartiría límites.
6. Con `requests` dentro de la corrutina tarda **3.08 s**, igual que secuencial: `requests.get` es bloqueante, así que el loop queda congelado en cada descarga y no hay solapamiento. Es la regla de las clases 18 y 19.

**Parte C**

7. Con `Semaphore(3)`: **1.38 s**. Son ⌈10/3⌉ = 4 tandas de ~0.3 s.
8. Acotar la concurrencia evita dos problemas:
   - **Agotar descriptores de archivo** en el cliente: cada conexión es un fd y hay un `ulimit -n`.
   - **Saturar al servidor o a la red**: 10 000 pedidos simultáneos a un mismo host son un ataque de denegación de servicio, y te van a bloquear (HTTP 429) o se van a caer por timeouts. También acota la memoria, porque todas las respuestas en vuelo ocupan RAM a la vez.
9. 200 URLs sin semáforo, con el límite del pool de httpx desactivado y `ulimit -n 64`: **56 ok y 144 errores** `ConnectError`, con causa de fondo `OSError: [Errno 24] Too many open files`. Con `Semaphore(20)` y el mismo ulimit: 200 ok. En la práctica httpx ya limita a 100 conexiones por defecto (`Limits(max_connections=100)`). En macOS el `ulimit -n` por defecto es 256, así que ahí se ve sin tocar nada.

**Parte D**

10. Con una URL inválida y `gather` normal, la primera excepción (`ConnectError`) se propaga desde el `await gather(...)`: se pierden los resultados de las 8 buenas, aunque esas tareas siguen corriendo.
11. Con `return_exceptions=True` se obtienen las 9 posiciones: 8 resultados y 1 `ConnectError` devuelta como **valor**, en su lugar de la lista.
12. Para el TP2 conviene **`return_exceptions=True`** (o manejar cada tarea por separado). Es una plataforma de tareas independientes: que una falle no tiene que tirar a las demás. Cada tarea termina en `completada` o en `error`, con su mensaje, y el sistema sigue. El `gather` normal sirve cuando las partes son un todo y si una falla no tiene sentido seguir.

## Ejercicio 4: Locks, o su ausencia

1. Con 1000 tareas de `sumar()`, el contador queda exactamente en **1000**.
2. Con 1000 threads en la clase 11, `+= 1` no es atómico: el SO puede cambiar de thread entre el leer y el escribir (se pierden sumas, sobre todo sin GIL o con más trabajo en el medio).
3. En corrutinas no hace falta `Lock` porque el cambio de contexto **solo** ocurre en un `await`. `contador += 1` no tiene ningún `await`, así que se ejecuta completo sin interrupción.
4. 100 transferencias de $1 con un `await` en el medio: el saldo final es **incorrecto** (origen = 999, destino = 100, total = 1099).
5. Ahora hay race condition, aunque sea un solo hilo, porque el `await asyncio.sleep(0)` entre leer el saldo y escribirlo le da el control a las otras 99 tareas. Todas leen `saldo = 1000` antes de que alguna escriba: *read-modify-write* partido por un punto de suspensión.
6. Con `asyncio.Lock`: origen = 900, destino = 100, total = 1000. Se usa `async with` porque adquirir el lock puede **esperar**: si otra tarea lo tiene, hay que ceder el control al loop en vez de bloquear el hilo. Un `with` común (o `threading.Lock`) bloquearía el loop entero, y si el dueño del lock es otra corrutina, sería un deadlock.
7. Regla: **en asyncio hace falta un lock cuando una sección crítica contiene un `await`**. Si no hay `await` en el medio, es atómica por construcción.

## Ejercicio 5: Timeouts y cancelación

1. Si vence `asyncio.timeout(2)`, lanza `TimeoutError` (en 3.11+ `asyncio.TimeoutError` es un alias).
2. `operacion_lenta()` **se cancela**: recibe `CancelledError` en su `await` (en la demo, `cancelada: True`).
3. `wait_for()` hace lo mismo: cancela y lanza `TimeoutError`. La diferencia es la forma: `timeout()` es un context manager que puede envolver varios `await` y cuyo plazo se puede reprogramar; `wait_for()` envuelve una sola corrutina.
4. Orden de los mensajes en la última parte de `descargas.py`:
   1. la tarea recibió `CancelledError` en su `await`
   2. `finally`: limpieza hecha
   3. quien la canceló también la ve
5. La tarea recibe el `CancelledError` en el **próximo `await`** en el que está (o va a estar) suspendida. `cancel()` solo **pide** la cancelación, y la excepción se inyecta cuando el loop la reanuda.
6. Una corrutina que calcula 2 s sin ningún `await` **no** se puede cancelar a tiempo: `cancel()` no la frenó y devolvió `'terminé igual'` a los 2.0 s. Nunca vuelve al loop, así que no hay dónde inyectar la excepción. Es la cooperación obligatoria de la clase 18.
7. Si se captura `CancelledError` y no se relanza, la tarea "sobrevive": devuelve `'sigo viva'` y `cancelled()` da `False`. Quien la canceló cree que no pasó nada. Rompe `timeout()`, `wait_for()`, `TaskGroup` y el apagado ordenado, que esperan que la cancelación se propague. Si hay que limpiar, se hace en un `finally` o se captura y se **relanza**.
8. `CancelledError` hereda de `BaseException` y no de `Exception` para que un `except Exception:` genérico (manejo de errores de negocio) **no** la trague por accidente. Como `KeyboardInterrupt` y `SystemExit`, es una señal de control de flujo, no un error.

## Ejercicio 6: La escala

1. `escala.py` en Linux (`ulimit -n` = 20000):

| Clientes | OK | Tiempo | Threads |
|---------:|---:|-------:|--------:|
| 100 | 100 | 0.02 s | 1 |
| 500 | 500 | 0.11 s | 1 |
| 1000 | 1000 | 0.25 s | 1 |
| 2000 | 2000 | 0.56 s | 1 |
| 5000 | 5000 | 1.72 s | 1 |

   El proceso usa **1 thread** en todos los casos.
2. Hasta 5000 no falló nada. El primer techo es la cantidad de **descriptores de archivo**: cada conexión usa 2 fd (cliente y servidor en el mismo proceso de prueba).
3. Sí se relaciona: con un `ulimit -n` de 256 (el default de macOS) y 2 fd por cliente, el techo teórico queda en ~120 clientes antes de `OSError: Too many open files`. Se sube con `ulimit -n 10240`.
4. 5000 clientes como threads, con 4 MB de stack cada uno, serían **~20 GB** de espacio virtual reservado (el RSS real es menor, pero el kernel igual tiene que administrar 5000 threads y repartir CPU entre ellos).
5. Con asyncio, 5000 clientes se atendieron en 1.72 s con **un solo thread**: cada conexión es una `Task` de unos cientos de bytes más sus buffers, no un thread con su stack de megabytes. En la clase 14, con un thread por cliente, 5000 clientes eran ~20 GB de stacks virtuales y un scheduler repartiendo tiempo entre miles de hilos que casi siempre esperan. Asyncio, apoyado en `epoll`/`kqueue` (clase 17), solo trabaja con las conexiones que tienen datos, así que el costo de una conexión ociosa es casi nulo. El techo pasa a ser el `ulimit -n` y la memoria de los buffers, no la cantidad de threads. Por eso asyncio resuelve el problema C10K.

## Adicionales

- **Chat**: con asyncio queda más legible que la versión con `selectors`. `readline()` resuelve el framing, `drain()` la contrapresión, y no hay que manejar `EVENT_WRITE` ni buffers de salida a mano.
- **Servidor de comandos**: ya **no** hace falta el `Lock` de la clase 16. Ninguna sección que toca `conexiones` o `activos` tiene un `await` adentro.
- **Proxy**: dos tareas por conexión (cliente→destino y destino→cliente) con `asyncio.wait(..., FIRST_COMPLETED)`. Cuando un sentido cierra, se cancela el otro.
