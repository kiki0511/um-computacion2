# Clase 15: UDP — Respuestas

Los números son de una corrida en Linux. En Mac pueden variar un poco; volvé a correr los scripts para tener los tuyos.

| Archivo | Qué cubre |
|---------|-----------|
| `ej1_2_datagramas.py` | 1.9 (dos clientes, sin concurrencia), 2.1 (límites), 2.2 (truncado) |
| `ej3_protocolo_confiable.py` | **Obligatorio**: reintentos, duplicados, secuencia, timeouts |
| `ej4_5_6_connect_broadcast_mtu.py` | connect() en UDP, broadcast, fragmentación |
| `ej_extra_adicionales.py` | Servidor de tiempo RFC 868, medidor de pérdida y jitter |

---

## Ejercicio 1: Primer contacto

1. `recvfrom()` devuelve los datos **y la dirección de origen** `(ip, puerto)`. Es la única forma de saber a quién responderle.
2. Sí, el puerto efímero cambia en cada corrida: cada ejecución crea un socket nuevo y el SO le asigna un puerto libre al primer `sendto()`.
3. Con el servidor muerto, el cliente espera y a los 2 s salta el `settimeout(2.0)`. En localhost a veces llega antes un `ConnectionRefusedError` (ICMP port unreachable), pero no hay que contar con eso.
4. Sin timeout, `recvfrom()` bloquea para siempre: UDP no tiene ninguna forma de saber que del otro lado no hay nadie.
5. Sí, `nc -u -l` recibe el mensaje: UDP no tiene handshake, cualquiera que escuche en el puerto lo recibe.
6. Sí. `nc` responde a la dirección de origen del último datagrama que recibió.
7. Desaparecen `listen()`, `accept()` y el `connect()` del cliente. Quedan `bind()`, `sendto()` y `recvfrom()`.
8. En TCP cada conexión es una cuádrupla distinta (IP/puerto de origen y de destino), y por eso un socket por conexión. En UDP no hay conexión: un solo socket recibe datagramas de todos, cada uno con su origen.
9. Sí, atiende a los dos sin concurrencia (`ej1_2_datagramas.py dos_clientes`). Cada datagrama es independiente y se procesa en microsegundos; no hay un `recv()` bloqueado esperando a un cliente lento. El problema de la clase 14 aparece solo si el **procesamiento** es lento.

## Ejercicio 2: Límites del datagrama

1. Tres `sendto()` producen tres `recvfrom()`: `b'uno'`, `b'dos'`, `b'tres'`.
2. En TCP es un flujo de bytes sin límites, y dos `send()` pueden llegar en un solo `recv()`. UDP es orientado a mensajes: cada datagrama es una unidad.
3. El primero trajo 10 bytes. El segundo: nada (timeout).
4. Los 90 bytes restantes **se descartaron**. El datagrama se entrega de una vez; lo que no entra en el buffer se pierde.
5. En TCP esos 90 bytes quedaban en el buffer del kernel para el próximo `recv()`. TCP es flujo y el `recv(n)` solo limita cuánto sacás; UDP es mensaje y el `recvfrom(n)` limita cuánto del mensaje ves.
6. Conviene `recvfrom(65535)`, el máximo teórico de un datagrama UDP, para no truncar nunca.

## Ejercicio 3: Protocolo confiable (obligatorio)

**Parte A** (`perdidas.py 0.3`)
1. Llegaron 152 de 200 (se perdió el 24% con 30% configurado; es aleatorio).
2. El emisor no recibió **ningún** error: para él se enviaron los 200.
3. **UDP no avisa cuando se pierde un datagrama: la entrega no está garantizada y el emisor no se entera.**

3b. Con `tc netem reorder` aparecen saltos hacia atrás. En loopback sin `tc` da 0, porque entrega en orden. Un protocolo que asuma orden procesaría mensajes viejos como nuevos.

**Parte B** (`ej3_protocolo_confiable.py reintentos`)

La pérdida se simula en los dos sentidos (se pierde el pedido o la respuesta). Por eso P(éxito por intento) = (1-p)².

| Pérdida | Intentos promedio | Máximo | Respondidos |
|---------|-------------------|--------|-------------|
| 30% | 2.45 | 8 | 20/20 |
| 70% | 13.0 | 39 | 20/20 |

4. Con 30%: unos 2 intentos (teórico: 1/0.49 ≈ 2.04).
5. Con 70% sigue funcionando, pero hacen falta muchos más intentos (teórico: 1/0.09 ≈ 11). Por eso el tope de intentos es 50.
6. Timeout muy corto (0.01 s): en localhost anda, porque el RTT es de microsegundos. En una red real reintenta antes de que llegue la respuesta y genera duplicados y tráfico de más (punto 11). Timeout muy largo (5 s): cada pérdida cuesta 5 s; 4 mensajes tardaron 20 s. El timeout tiene que ser algo mayor que el RTT; TCP lo calcula dinámicamente.

**Parte C** (`ej3_protocolo_confiable.py duplicados`)

7. No puede saberlo: los dos casos se ven igual, un timeout.
8. El servidor ingenuo hizo **33 trabajos para 20 mensajes** (30% de pérdida) y **81 para 20** (70%). Cada respuesta perdida provocó que se reprocese el pedido.
9. "Poner en mayúsculas" es idempotente: repetirlo da lo mismo. "Transferir $100" no: ejecutarlo dos veces transfiere $200. Un pedido no idempotente con reintentos ciegos es un bug de plata.

**Parte D** (`ej3_protocolo_confiable.py secuencia`)

10. Con seq y dedup, el servidor hizo **20 trabajos para 20 mensajes**, tanto con 30% como con 70% de pérdida. Los duplicados se contestan con la respuesta guardada en `vistos[(origen, seq)]`.
11. Hace falta porque una respuesta demorada de un intento anterior puede llegar mientras espero la del pedido actual. En el punto 11 del script, el servidor demora 30 ms y el timeout es de 20 ms:
    - **Sin seq**: 9 de 10 respuestas eran de OTRO pedido. Quedan corridas un mensaje y el cliente no se da cuenta.
    - **Con seq**: 9 respuestas viejas descartadas y 0 equivocadas.
12. `confiable.py 0.6`: 29 envíos reales y 5 trabajos del servidor. Mi versión hace lo mismo, con dos diferencias: la clave de deduplicación incluye el origen (dos clientes pueden usar el mismo seq), y el cliente sigue esperando dentro del mismo intento después de descartar una respuesta vieja.

**Parte E**

13. Garantías de TCP que todavía faltan:
    - **Orden** con varios mensajes en vuelo (acá hay uno a la vez, stop-and-wait).
    - **Control de flujo**: no saturar al receptor.
    - **Control de congestión**: bajar el ritmo cuando la red pierde.
    - Además: segmentación de mensajes grandes, timeout adaptativo (RTT estimado) y limpieza del diccionario `vistos`, que crece para siempre.
14. Cuando empezás a necesitar orden, flujo continuo o control de congestión, estás reescribiendo TCP (peor). UDP con confiabilidad propia conviene solo si necesitás algo que TCP no da: baja latencia tolerando pérdidas (juegos, VoIP), multicast o control fino (QUIC).

## Ejercicio 4: connect() en UDP

1. Con `connect()`, `recv()` lanza `ConnectionRefusedError`. Viene de un ICMP *port unreachable* que manda el kernel destino.
2. Sin `connect()`, da timeout: el ICMP llega igual, pero se descarta.
3. `connect()` en UDP no hace handshake: fija el destino por defecto y **filtra** lo que se recibe (solo de ese origen). Como el socket tiene un par asociado, el kernel puede atribuirle el error ICMP.
4. Con `connect()`, los datagramas de otros orígenes se descartan en silencio. En el script, el del "intruso" no llegó.
5. Muchos firewalls bloquean ICMP y los NAT no siempre lo traducen. La ausencia de error no significa que haya alguien escuchando.

## Ejercicio 5: Broadcast

1. Sin `SO_BROADCAST`: `PermissionError: [Errno 13]`. Es una protección para que un programa no inunde la red por error: tenés que pedirlo explícitamente.
2. Servidor: `ej4_5_6_connect_broadcast_mtu.py broadcast_srv`.
3. En la misma red funciona. En redes distintas no, porque el broadcast no cruza routers.
4. Los routers no reenvían broadcast porque se multiplicaría por toda Internet (tormenta de broadcast). El broadcast queda limitado al dominio de la LAN.
5. Una máquina sin IP no puede abrir una conexión TCP: TCP necesita IP de origen, IP de destino conocida y handshake. DHCP manda un broadcast desde `0.0.0.0` a `255.255.255.255`, sin saber a quién le habla.

## Ejercicio 6: Fragmentación y MTU

1. MTU Ethernet: 1500 (en Mac: `ifconfig en0 | grep mtu`).
2. 1500 − 20 − 8 = **1472 bytes** de payload UDP.
3. En localhost llega entero en Linux. En macOS falla con `Message too long` porque `net.inet.udp.maxdgram` es 9216 por defecto.
4. y 5. Un datagrama de 60000 B son 41 fragmentos. Si se pierde cualquiera, se descarta el datagrama entero:
   - P(llega) = 0.95⁴¹ ≈ **12%**
   - Uno de 1000 B (un fragmento) llega el **95%** de las veces.

   La probabilidad de éxito cae exponencialmente con la cantidad de fragmentos: por eso la diferencia es mucho mayor que el 5% de pérdida.
