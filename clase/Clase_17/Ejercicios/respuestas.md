# Clase 17: I/O Multiplexing — Respuestas

Los números son de una corrida en Linux (con `epoll`). En macOS no hay `epoll`: `ej3_comparar.py` mide `kqueue`, que cumple el mismo papel. Si querés los números de `epoll` en tu Mac, corrélo dentro de Docker (como en el TP1).

| Archivo | Qué cubre |
|---------|-----------|
| `ej1_2_busywait_fdsetsize.py` | CPU del busy-wait vs `select()`, límite de FD_SETSIZE |
| `ej3_comparar.py` | **Obligatorio**: `select`/`poll`/`epoll` (o `kqueue`), ACTIVOS configurable |
| `ej4_eco_selectors.py` | `servidor_select.py` reescrito con `selectors` |
| `ej6_chat_extendido.py` | `/nick`, `/lista` y framing con buffer por cliente |
| `ej7_hilo_unico.py` | Trabajo pesado en el loop vs mandado a un pool (self-pipe) |
| `ej_extra_adicionales.py` | Timeout de inactividad + self-pipe para SIGINT en el loop |

---

## Ejercicio 0: Direcciones en el código

1. `192.168.1.37` está en la misma red: se entrega directo, resolviendo la MAC con ARP. `192.168.2.10` no: el paquete va al gateway por defecto.
2. `docker0` suele usar `172.17.0.0/16`. Los contenedores están todos en esa misma subred, conectados al mismo bridge, así que se ven directamente sin router.
3. `getsockname()` en IPv6 devuelve 4 elementos: `('::1', puerto, flowinfo, scope_id)`.
4. `host, puerto = ...` tira `ValueError: too many values to unpack`. Lo portable es `direccion[0], direccion[1]` (o `host, puerto, *_ = ...`).
5. No aparece si probás solo con IPv4, porque ahí la tupla tiene exactamente 2 elementos.
6. `getaddrinfo` devuelve las dos familias si el nombre tiene registros A y AAAA. El orden lo decide el sistema (RFC 6724), normalmente IPv6 primero.
7. Hay que probar en orden porque podés tener dirección IPv6 pero no ruta (lo normal en Argentina): la primera falla y la siguiente IPv4 funciona.
8. `socket.create_connection()` hace ese bucle: prueba cada dirección y devuelve la primera que conecta.
9. y 10. Con dual-stack, el cliente IPv6 se ve como `::1` y el IPv4 como `::ffff:127.0.0.1`, con el prefijo de las direcciones mapeadas `::ffff:0:0/96`. Si filtrás por IP, `127.0.0.1` no matchea `::ffff:127.0.0.1`: hay que normalizar.
11. Con `V6ONLY=1`, el cliente IPv4 recibe *connection refused*.
12. Conviene ponerlo explícito porque el default cambia según el SO. Más detalle en `clase/Bloque_0/ipv6/`.

## Ejercicio 1: Ver el problema

1. El busy-wait funciona con `nc`.
2. Pero sin nadie conectado consume **100% de un núcleo**.
3. Nunca duerme: pregunta "¿hay algo?" en un bucle, el kernel contesta `BlockingIOError` y vuelve a preguntar, millones de veces por segundo.
4. `servidor_select.py` ocioso: **0%**. `select()` le pide al kernel que duerma el proceso hasta que haya un evento.
5. En el servidor secuencial de la clase 13, un cliente que no mandaba nada dejaba al servidor bloqueado en su `recv()` y nadie más era atendido. `select()` solo te devuelve los sockets que **ya** tienen datos, así que nunca te bloqueás esperando a uno en particular.

## Ejercicio 2: select() en detalle

1. `servidor_select.py` tiene **1 thread** aunque haya tres clientes.
2. El tercer cliente responde enseguida: el servidor atiende al socket que tenga datos, sin importar el orden.
3. Al matar un cliente, `recv()` devuelve `b''` y el servidor imprime la desconexión. Lo detecta el `if not datos:`.
4. y 5. Si no se hace `remove` del socket cerrado: después del `close()` el fd queda en la lista. `select()` lo reporta como listo (o como fd inválido/`EBADF`), el `recv` falla o devuelve vacío y el bucle gira sin parar: **100% de CPU**. Un fd con EOF está *siempre* legible.
7. `ValueError: filedescriptor out of range in select()`, vigilando **un solo** socket.
8. El límite de `select()` es el **número** del fd (< FD_SETSIZE = 1024), no la cantidad: usa un bitmap de 1024 bits indexado por número de descriptor.
9. `poll()` no falla con el mismo fd 1102: recibe un arreglo de estructuras, sin bitmap.
10. Es difícil de encontrar porque en desarrollo tenés pocos archivos abiertos y los fd son chicos. En producción, con muchas conexiones, logs y archivos, algún fd pasa de 1023 y el servidor explota con pocos clientes vigilados.

## Ejercicio 3: Comparar los tres (obligatorio)

**Parte A.** µs por llamada, 3 sockets activos (promedio de 200 llamadas):

| Conexiones | select | poll | epoll |
|-----------:|-------:|-----:|------:|
| 100 | 7.2 | 2.0 | 0.9 |
| 500 | 31.1 | 7.9 | 0.7 |
| 1000 | falla | 18.8 | 0.6 |
| 2000 | falla | 137.1 | 0.8 |
| 5000 | falla | 417.1 | 0.7 |

2. Entre 100 y 5000 conexiones (×50), `poll` crece de 2.0 a 417 µs: **×213**. Crece al menos linealmente; el salto extra por encima de ×50 viene de que la lista ya no entra en la caché de la CPU.
3. `epoll` se mantiene **plano**, entre 0.6 y 0.9 µs para cualquier cantidad (×0.8). No depende del total.
4. `select()` falla desde 1000 conexiones. Coincide con el 2.3: con 1000 pares de sockets hay fd mayores que 1023. Lo que lo rompe es el número de fd, no la cantidad.

**Parte B**

5. Es realista: en un servidor web la mayoría de las conexiones están ociosas en cada instante (keep-alive esperando el próximo pedido, clientes lentos leyendo, websockets que casi no hablan). Solo un puñado tiene datos a la vez.
6. `poll()` es O(n) porque en **cada** llamada le pasás la lista completa, el kernel la copia, recorre todos los fd preguntando si están listos y te la devuelve para que la recorras vos. `epoll` es O(listos) porque el registro es **persistente** en el kernel (`epoll_ctl` una vez por fd). Cuando llega un paquete, el propio kernel mete el fd en una lista de listos, y `epoll_wait` solo te devuelve esa lista.
7. Con **la mitad activos** (`--activos mitad`):

| Conexiones | Activos | poll | epoll |
|-----------:|--------:|-----:|------:|
| 100 | 50 | 2.4 | 4.6 |
| 1000 | 500 | 22.4 | 42.7 |
| 5000 | 2500 | 434.2 | 252.5 |

   La ventaja de `epoll` **desaparece** (con pocas conexiones hasta pierde). Si la mitad está lista, O(listos) = O(n/2): `epoll` también tiene que devolver miles de eventos, y encima paga el armado de cada uno. Su ventaja depende de que haya pocos listos respecto del total.

**Parte C**

8. Con 10, 50 y 100 conexiones, todos tardan entre 0.5 y 7 µs por llamada. **No vale la pena** la diferencia: un solo `recv()` o el procesamiento del pedido cuestan más que eso.
9. No tiene sentido complicarse con multiplexing cuando hay pocas conexiones simultáneas (decenas, incluso cientos): un thread por cliente (clase 14) es más simple de escribir y depurar, y funciona perfecto. Multiplexing se justifica con miles de conexiones mayormente ociosas.

**Parte D: conclusión**

Con 5000 conexiones, preguntar "¿quién tiene datos?" le cuesta a `poll` 417 µs por llamada y a `epoll` 0.7 µs, casi 600 veces menos, porque `epoll` solo mira a los que tienen algo. Apache clásico (prefork/worker) dedica un proceso o thread por conexión: 5000 conexiones son 5000 stacks y el scheduler repartiendo CPU entre miles de hilos que casi siempre están esperando. nginx usa pocos procesos worker, cada uno con un event loop sobre `epoll`: una conexión ociosa no cuesta un thread sino una entrada en una estructura del kernel, y el costo de cada vuelta del loop depende de las conexiones activas, no del total. Por eso nginx sostiene decenas de miles de conexiones con memoria y CPU casi constantes, que es exactamente el problema C10K.

## Ejercicio 4: De select a selectors

1. Desaparecen la lista `vigilados` (la mantiene el selector con `register`/`unregister`), el diccionario de direcciones (va en `data` del registro) y el `if s is srv:`: cada registro trae su propio callback.
2. `DefaultSelector` elige `EpollSelector` en Linux y `KqueueSelector` en macOS.
3. Con `SelectSelector` forzado, el comportamiento con pocos clientes es idéntico. Hereda el límite de fd < 1024.
4. Sin `unregister` antes de `close()`: con `epoll`, el kernel saca solo el fd cerrado, pero el `selectors` de Python lo sigue teniendo en su mapa. Cuando el SO reutiliza ese número de fd para un cliente nuevo, `register()` falla con `KeyError: ... is already registered`, o los eventos se despachan al callback equivocado. Con `SelectSelector` es peor: `select()` recibe un fd inválido y lanza `OSError: Bad file descriptor` en cada vuelta.

## Ejercicio 5: Escritura no bloqueante

1. Se usa `send()` y no `sendall()` porque `sendall()` insiste hasta mandar todo: si el buffer del cliente está lleno, **bloquea el único hilo** y congela a todos. En la clase 13 (un hilo por cliente) `sendall()` era lo correcto, porque bloquear afectaba solo a ese cliente.
2. Con `EVENT_WRITE` registrado permanentemente, el bucle gira al 100% de CPU: un socket casi siempre es escribible, así que `select()` vuelve al instante en cada vuelta.
3. Un cliente lento que no lee: con `sendall()`, los otros 999 quedan congelados hasta que ese cliente lea. Con buffer + `EVENT_WRITE` se manda lo que entra, el resto espera en `pendiente[conn]` y los demás siguen atendidos.
4. La memoria crece en `pendiente[conn]` (el buffer de salida de ese cliente). Hay que poner un tope: si supera N bytes, dejar de leerle (backpressure) o desconectarlo.

## Ejercicio 6: Chat multiusuario

1. En el chat no hace falta lock aunque se escriba en los sockets de B y C: hay un solo hilo. Mientras `difundir()` recorre `clientes`, nadie más puede modificar el diccionario. Con threads, otro hilo podría agregar o sacar un cliente en medio del recorrido.
2. `difundir()` encola en vez de enviar directo porque escribir podría bloquear (o mandar parcial) si el buffer de un cliente lento está lleno. Encolar y esperar `EVENT_WRITE` no frena a nadie.
3. y 4. `/nick` y `/lista`: ver `ej6_chat_extendido.py`.
5. No es cierto que cada `recv()` traiga una línea: TCP es un flujo (clase 13). Un `recv()` puede traer media línea (un mensaje largo, `nc` mandando de a pedazos, redes lentas) o varias pegadas. El chat original mandaría `"ho"` y `"la"` como dos mensajes.
6. Arreglado con un buffer de entrada por cliente: se acumula, se corta por `\n`, se procesan solo las líneas completas y el resto queda para el próximo `recv()`. En la demo, `ho` + `la be` + `to\nsegunda\ntercera ` + `linea\n` producen exactamente 3 mensajes: `hola beto`, `segunda` y `tercera linea`.

## Ejercicio 7: El costo del hilo único (`ej7_hilo_unico.py`)

1. Mientras el loop calcula el hash del primer cliente, el segundo **no** responde: el `PING` enviado a los 50 ms se contestó recién a los 0.56 s, junto con el cálculo.
2. Con `server_threads.py` de la clase 14 no pasa: cada cliente tiene su thread y el scheduler del SO los reparte. El PING se contesta enseguida (en CPU pura el GIL los alterna, pero no se bloquean hasta que el otro termine).
3. Regla: **en un event loop nada puede tardar sin devolver el control.** Un callback lento congela a todos los clientes.
4. Sin abandonar el event loop: se manda el trabajo de CPU a un **pool de procesos** y el loop solo espera el aviso de que terminó. En la versión con pool, el PING se respondió a los **0.05 s** y el cálculo a los 0.54 s. El aviso entra al loop por un socketpair registrado en el selector (self-pipe). Es el esquema del TP2: API/event loop adelante y workers atrás.
