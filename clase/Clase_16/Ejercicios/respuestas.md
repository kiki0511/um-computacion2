# Clase 16: socketserver — Respuestas

Los números son de una corrida en Linux. Volvé a correr los scripts para tener los de tu máquina.

| Archivo | Qué cubre |
|---------|-----------|
| `ej1_progresion.py` | Pasos 1–6: mínimo, concurrencia, framing, estado, errores |
| `ej2_mixins.py` | **Obligatorio**: mixins, MRO, forking + `Value`, `daemon_threads` |
| `ej4_comandos_extendido.py` | NICK, BROADCAST, desconexiones, timeout de 30 s |
| `ej5_limite.py` | Threads y memoria con 200 y 1000 conexiones |
| `ej_extra_adicionales.py` | Servidor de archivos con framing por longitud, selector de `serve_forever` |

---

## Ejercicio 1: La progresión

**1.1**
1. `self.request` es el `socket.socket` de la conexión aceptada (en TCP). En UDP es una tupla `(datos, socket)`.
2. `id(self)` cambia en cada conexión: se crea **un handler nuevo por conexión**.
3. `handle()` se ejecuta **una vez por conexión**, no por mensaje. Si el cliente manda tres mensajes, hay que leerlos dentro de un bucle en `handle()`.

**1.2**

4. Si relanzás enseguida después de que alguien se conectó: `OSError: [Errno 98] Address already in use` (48 en macOS).
5. Sin haberte conectado nunca, no da error. El puerto queda en `TIME_WAIT` solo si hubo una conexión y el servidor cerró primero; sin conexión no hay nada en `TIME_WAIT`.
6. Con `allow_reuse_address = True` (que activa `SO_REUSEADDR` antes del `bind`) desaparece.

**1.3** (`ej1_progresion.py concurrencia`)

| Servidor | Segundo cliente | PIDs |
|----------|-----------------|------|
| `TCPServer` | 2.00 s | 1 |
| `ThreadingTCPServer` | 1.00 s | 1 (mismo proceso) |
| `ForkingTCPServer` | 1.00 s | 2 distintos (un hijo por conexión) |

**1.4**

10. Con `recv(1024)` llega `b'UNO\nDOS\n'` en un solo bloque.
11. Con `rfile` se itera línea por línea: `b'UNO\n'` y `b'DOS\n'`.
12. No hay que mezclar `self.rfile` con `self.request.recv()`: `rfile` es un archivo con buffer. Puede haber leído del socket más de lo que te devolvió, y esos bytes quedan en su buffer. Un `recv()` directo se los saltearía o los leería desordenados.

**1.5**

13. El contador en el handler siempre da 1: `self.contador += 1` crea un atributo de instancia en un handler que es nuevo en cada conexión.
14. En el servidor sí cuenta: 1, 2, 3, 4.
15. Sin el `Lock` y con 200 conexiones puede que no se pierda ninguna: `+= 1` son varias instrucciones bytecode y el GIL rara vez cambia de thread justo en el medio. Que no falle en una prueba **no** demuestra que sea correcto; la race condition existe y aparece bajo otra carga, en otra versión de Python o en free-threading.

**1.6**

16. El servidor no se cae: `handle_error()` imprime el traceback y sigue atendiendo.
17. Sí, `finish()` se ejecuta aunque `handle()` falle (está en un `finally` del `__init__` del handler). El orden es `setup → handle → finish → handle_error`.
18. Si sacás `super().setup()`, `StreamRequestHandler` nunca crea `self.rfile` ni `self.wfile`: `AttributeError` en `handle()`. Tampoco se aplica el `timeout`.

## Ejercicio 2: Los mixins (obligatorio)

**Parte A**

1. `ThreadingMixIn` define 3 métodos: `process_request_thread`, `process_request` y `server_close`. La concurrencia la produce `process_request`, que crea un `threading.Thread` con target `process_request_thread` y lo arranca.
2. `BaseServer.process_request` llama a `finish_request()` y a `shutdown_request()` **en el mismo hilo** (bloquea hasta terminar). El del mixin hace lo mismo, pero dentro de un thread nuevo, y vuelve enseguida a `accept()`.
3. `ForkingMixIn` cosecha en `collect_children()`, que hace `os.waitpid(..., WNOHANG)`. Lo llama `service_actions()`, que `serve_forever()` ejecuta en cada vuelta del bucle (como máximo cada `poll_interval` = 0.5 s). Por eso no quedan zombies como en la clase 14: la cosecha ya está hecha.
4. `class ThreadingTCPServer(ThreadingMixIn, TCPServer): pass`. Cero código propio: todo es la combinación.

**Parte B**

5. MRO de `Bien`: `Bien → ThreadingMixIn → TCPServer → BaseServer`. MRO de `Mal`: `Mal → TCPServer → BaseServer → ThreadingMixIn`.
6. En `Bien`, `process_request` lo provee `ThreadingMixIn`. En `Mal`, lo provee `BaseServer`, que en el MRO aparece antes que el mixin.
7. Con 2 clientes de 1 s cada uno:
   - `Bien`: **1.00 s** (en paralelo)
   - `Mal`: **2.00 s** (en serie, igual que `TCPServer`)
8. `Mal` no lanza ningún error. Arranca y responde bien, solo que no concurre. Es peligroso porque pasa todas las pruebas funcionales y el problema aparece recién en producción, bajo carga.

**Parte C**

9. Con `ForkingTCPServer` y un `int` en el servidor, todas las respuestas dan `1`.
10. `fork()` copia la memoria del padre (copy-on-write). Cada hijo incrementa **su** copia del servidor y termina; el padre nunca ve el cambio (clase 4).
11. Se arregla con memoria compartida: `multiprocessing.Value('i', 0)` con `get_lock()` al incrementar (clase 9). Resultado: `1, 2, 3, 4, 5`.
12. El `Value` va en el `__init__` del **servidor**. Así se crea una sola vez en el padre, antes de cualquier fork, y todos los hijos heredan el mismo segmento compartido. Creado en el handler, cada hijo tendría el suyo y volvería a dar siempre 1.

**Parte D**

13. Sin `daemon_threads`, con un cliente `nc` abierto y Ctrl+C, el servidor **no termina**: al salir, el intérprete hace `join()` de los threads no-daemon y el handler sigue bloqueado en `recv()`. En la prueba automática, el proceso seguía vivo 2 s después del SIGINT.
14. Con `daemon_threads = True` termina enseguida (código 0): los threads daemon se abandonan al salir. El costo es que se cortan conexiones a mitad de camino.

## Ejercicio 3: UDP

1. En `EchoUDPCrudo`, `self.request` es una tupla `(datos: bytes, socket)`.
2. Hay que pasar `self.client_address` al `sendto()` porque el socket UDP es **uno solo para todos** y no está conectado a nadie. En TCP, cada socket de conexión ya sabía quién era el otro extremo.
3. `DatagramRequestHandler` esconde el `recvfrom`/`sendto`: te da `self.rfile` (con el datagrama ya leído) y `self.wfile` (un buffer que se manda con `sendto` en `finish()`).
4. Sí, existe `ThreadingUDPServer`. Tiene sentido cuando el **procesamiento** de un datagrama es lento: sin threads, un pedido lento demora a todos los demás. La concurrencia no es por conexión sino por pedido.

## Ejercicio 4: Un servidor de verdad (`ej4_comandos_extendido.py`)

1. El apodo vive en el **servidor** (`self.server.nicks[direccion]`). Si viviera en el handler, `QUIEN` no podría leer los de los demás. Va protegido con el lock porque lo leen otros threads.
2. `BROADCAST` guarda el `wfile` de cada cliente en `self.server.clientes` y le escribe a todos menos al emisor.
3. Si un cliente se desconecta mientras otro le escribe, `write()` lanza `BrokenPipeError`/`OSError` (o `ValueError` si el wfile ya se cerró). `difundir()` lo captura, saca al cliente y sigue con los demás. Además escribe **fuera** del lock, para que un cliente lento no bloquee a todo el servidor.
4. `timeout = 30` en el handler: `StreamRequestHandler.setup()` hace `settimeout(30)`, `readline()` lanza `TimeoutError` y se desconecta al cliente.
5. Con `ForkingTCPServer`, `BROADCAST` **no** funcionaría: cada conexión es otro proceso, con su copia de `clientes`, y no ve los sockets de las demás.

## Ejercicio 5: El límite (`ej5_limite.py`)

| Conexiones | Threads | RSS |
|------------|---------|-----|
| 1 | 2 | 10.2 MB |
| 200 | 201 | 15.2 MB |
| 1000 | 1001 | 35.4 MB |

- Un thread por conexión, más el principal. El RSS crece poco porque el stack de cada thread se reserva virtualmente y solo se usa lo que se toca, pero el espacio virtual y los recursos del kernel crecen linealmente.
- Abrir las 1000 tardó **2 min 20 s**. `request_queue_size` es 5 por defecto, así que la cola de `listen()` desborda, el kernel descarta SYN y los clientes reintentan a los 1, 3, 7… segundos.
- **No resuelve C10K.** `socketserver` no cambia el modelo, solo lo empaqueta: sigue siendo un thread (o un proceso) por conexión. A 10 000 conexiones serían 10 000 threads, con su memoria, sus cambios de contexto y el límite de threads del sistema. Para eso hace falta multiplexing (clase 17).

## Adicionales

**Comparar con la clase 14**: `server_threads.py` tiene 68 líneas y `eco_tcp.py` tiene 62 con tres variantes. Lo que `socketserver` resuelve solo:

| Qué | Clase 14 | socketserver |
|-----|----------|--------------|
| `socket` + `bind` + `listen` | a mano | constructor |
| `SO_REUSEADDR` | a mano | `allow_reuse_address` |
| Bucle de `accept()` | a mano | `serve_forever()` |
| Thread/fork por cliente | a mano | mixin |
| Cosechar hijos | handler de SIGCHLD | `collect_children()` |
| Cerrar la conexión | `with conn` | `shutdown_request()` |
| Excepciones del handler | try/except propio | `handle_error()` |
| Shutdown ordenado | no había | `shutdown()` |

**Leer el fuente**: `serve_forever()` usa `selectors.PollSelector` (o `SelectSelector` si no hay poll) con `select(poll_interval)` para vigilar el socket de escucha y chequear el pedido de `shutdown()`. Es el multiplexing de la clase 17, aplicado a un solo fd.
