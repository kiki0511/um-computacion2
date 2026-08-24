# Clase 12: Redes - Respuestas ejercicios de observación

> Los comandos se corren en el contenedor Docker (Ubuntu) del curso.
> Los valores concretos (IPs, puertos, TTLs) varían según la máquina y el momento.
> Las respuestas conceptuales son generales.

---

## Ejercicio 1: Reconocimiento de tu propia máquina

### 1.1 Interfaces y direcciones (`ip addr show`)

**1. ¿Cuántas interfaces tenés? ¿Cuál es la loopback?**

Típicamente hay dos interfaces:
- `lo` → loopback (`127.0.0.1/8`). Es una interfaz virtual interna; el tráfico no sale a la red física.
- `eth0` (o `ens3`, `enp0s3`, etc.) → la interfaz de red real del contenedor.

**2. ¿Cuál es tu IP local? ¿Es privada?**

En el contenedor Docker la IP suele ser del rango `172.17.0.x` o `172.18.0.x`.
Sí es privada: pertenece al rango `172.16.0.0–172.31.255.255` (definido en RFC 1918).
No es ruteable en Internet; solo existe dentro de la red de Docker.

**3. ¿Tenés IPv6? ¿Empieza con `fe80:`?**

Sí, Docker asigna una dirección link-local IPv6 que empieza con `fe80:`.
Es link-local: solo vale en el segmento de red inmediato (no sale al router). No se usa para comunicación entre distintas redes.

---

### 1.2 Rutas (`ip route`)

**4. ¿Cuál es tu gateway por defecto?**

La línea `default via X.X.X.X dev eth0` indica el gateway.
En Docker suele ser `172.17.0.1` (el host Docker que hace NAT hacia Internet).

**5. ¿Qué relación tiene el gateway con tu IP?**

Están en la misma subred. Si mi IP es `172.17.0.2/16`, el gateway `172.17.0.1` también está en `172.17.0.0/16`. Todo tráfico hacia IPs fuera de esa subred sale por ese gateway; el gateway es quien tiene conectividad hacia afuera.

---

### 1.3 Puertos en escucha (`ss -tlnp`)

**6. Tres servicios escuchando:**

| Puerto | Dirección | Servicio típico |
|--------|-----------|-----------------|
| 22     | 0.0.0.0   | SSH             |
| 53     | 127.0.0.1 | DNS local (systemd-resolved) |
| 5432   | 127.0.0.1 | PostgreSQL (si instalado) |

*(Los valores reales dependen de lo que esté corriendo en el contenedor.)*

**7. `127.0.0.1` vs `0.0.0.0`: ¿qué implica?**

- `127.0.0.1` → solo acepta conexiones desde la misma máquina (loopback). Alguien en la misma red wifi **no puede** conectarse.
- `0.0.0.0` o `*` → acepta conexiones en todas las interfaces. Alguien en la misma red wifi **sí puede** conectarse si el firewall lo permite.

Implicación de seguridad: exponer un servicio en `0.0.0.0` lo hace alcanzable desde la red. Para servicios internos (bases de datos, caches) es una práctica común escuchar solo en `127.0.0.1`.

---

## Ejercicio 2: Resolución de nombres

### `dig www.um.edu.ar`

**1. ¿Qué IP devuelve?**

La sección `ANSWER SECTION` muestra la IP del servidor de la Universidad de Mendoza.
Ejemplo: `163.10.x.x` (dirección pública argentina).

**2. ¿Cuál es el TTL? ¿Qué significa?**

El TTL (Time To Live) indica cuántos segundos es válida esa respuesta en cache.
Si dice `TTL 300`, cualquier resolver intermedio puede guardar esa respuesta 5 minutos sin volver a preguntar al servidor autoritativo. Cuando el TTL llega a cero, el cache la descarta y consulta de nuevo.

**3. Si lo corrés de nuevo enseguida, ¿bajó el TTL?**

Sí, baja. El resolver local (o el del sistema) cacheó la respuesta y va restando el tiempo transcurrido. Cuando llega a 0, vuelve a consultar. Eso explica por qué un cambio de DNS "tarda en propagarse": los caches siguen sirviendo el valor viejo hasta que expira el TTL original.

---

### `dig google.com +short`

**4. ¿Cuántas IPs devuelve? ¿Para qué?**

Google devuelve varias IPs (típicamente 4-8). Esto se llama **round-robin DNS**: distribuye la carga entre múltiples servidores. Cada cliente recibe una lista y elige (generalmente la primera); distintos clientes reciben distintos órdenes, repartiendo el tráfico geográfica y funcionalmente.

**5. ¿El tiempo de resolución cambia en la segunda consulta?**

Sí, la segunda consulta es más rápida porque el resolver local ya tiene la respuesta en cache. El caching lo hace el resolver del sistema operativo o un servidor DNS intermedio. El servidor autoritativo de Google no es consultado en la segunda vez.

---

## Ejercicio 3: Cliente y servidor con netcat

### 3.1 Conversación básica

**1. ¿Qué pasa si cerrás el cliente? ¿Y el servidor?**

- Si cerrás el **cliente** con Ctrl+C: el servidor recibe EOF (fin de archivo) en su extremo y termina también. `nc -l` no vuelve a escuchar; habría que relanzarlo.
- Si cerrás el **servidor**: el cliente recibe un error de conexión (connection reset o EOF) y termina.

**2. Cuádrupla de la conexión (`ss -tnp | grep 8080`):**

```
State   Local Address:Port   Peer Address:Port
ESTAB   127.0.0.1:8080       127.0.0.1:XXXXX
ESTAB   127.0.0.1:XXXXX      127.0.0.1:8080
```

Los cuatro valores son: IP origen, puerto origen, IP destino, puerto destino. Son dos filas porque el SO ve ambos extremos localmente.

**3. ¿Se pueden conectar dos clientes a la vez a `nc -l`?**

No. `nc -l` acepta una sola conexión y termina. Para aceptar múltiples conexiones necesitaría un bucle o la flag `-k` (keep-listening) en algunas versiones. Eso es exactamente el problema que resuelve `accept()` en la clase 13.

---

### 3.2 El puerto ocupado

**4. Error al abrir otro `nc -l 8080`:**

```
nc: Address already in use
```

Significa que el socket (IP:puerto) ya está siendo usado por otro proceso. El SO no permite que dos procesos escuchen en la misma cuádrupla. Solución: liberar el puerto antes, o usar `SO_REUSEADDR`.

---

### 3.3 Loopback vs todas las interfaces

**5. ¿Por qué un servidor de desarrollo escucha en `127.0.0.1`?**

Para que solo sea accesible desde la misma máquina. Evita exponer accidentalmente el servidor a otros dispositivos de la red, lo cual sería un riesgo de seguridad si el servidor no tiene autenticación o no está listo para recibir tráfico externo.

---

## Ejercicio 4: HTTP a mano

### `printf 'GET / HTTP/1.1\r\nHost: example.com\r\nConnection: close\r\n\r\n' | nc example.com 80`

**1. Código de estado:**

`HTTP/1.1 200 OK` → éxito.

**2. Tres headers de la respuesta:**

| Header | Significado |
|--------|-------------|
| `Content-Type: text/html; charset=UTF-8` | El cuerpo es HTML en codificación UTF-8 |
| `Content-Length: 1256` | El cuerpo tiene 1256 bytes |
| `Cache-Control: max-age=604800` | La respuesta puede cachearse 7 días |

**3. ¿Qué pasa si sacás el header `Host`?**

En HTTP/1.1 el header `Host` es obligatorio. Sin él algunos servidores devuelven `400 Bad Request`. Razón: un mismo servidor IP puede alojar múltiples dominios (virtual hosting); el header `Host` le dice cuál de ellos está pidiendo el cliente. Sin él, el servidor no sabe a qué sitio responder.

**4. `GET /noexiste` → ¿qué código?**

`HTTP/1.1 404 Not Found` → el recurso no existe en ese servidor.

---

### Finales de línea

**5. ¿Funciona con `\n` en lugar de `\r\n`?**

Depende del servidor. Muchos son tolerantes y aceptan `\n` solo. Pero el estándar HTTP (RFC 7230) exige `\r\n` como fin de línea.

Depender de esa tolerancia es mala idea porque:
- No todos los servidores son tolerantes (distintas implementaciones, distintos comportamientos).
- El código deja de ser portable e interoperable.
- En producción puede fallar silenciosamente con ciertos servidores o proxies.

---

## Ejercicio 5: Observar el handshake (tcpdump)

### Identificar los tres paquetes del handshake

```
IP cliente > servidor: Flags [S]        → SYN: "quiero conectarme"
IP servidor > cliente: Flags [S.]       → SYN-ACK: "aceptado, yo también"
IP cliente > servidor: Flags [.]        → ACK: "confirmado"
```

**1. Los tres paquetes del handshake:** `[S]`, `[S.]`, `[.]`

**2. ¿Cuántos paquetes para mandar "test"?**

Bastante más que 1. Además del handshake (3 paquetes), hay al menos:
- 1 paquete con los datos ("test\n")
- 1 ACK del servidor
- 2-4 paquetes para el cierre (FIN/ACK de cada lado)

Total: ~7-9 paquetes para mandar 5 bytes útiles. Ilustra el overhead de TCP: los encabezados y el protocolo de control pesan más que el dato real en mensajes pequeños.

**3. El cierre: banderas `[F]`**

El cierre usa FIN:
```
cliente → servidor: [F.]   FIN: "termino de mandar"
servidor → cliente: [.]    ACK
servidor → cliente: [F.]   FIN: "yo también termino"
cliente → servidor: [.]    ACK
```

Son 4 pasos porque cada extremo cierra su dirección por separado (half-close). Uno puede terminar de enviar y seguir recibiendo.

---

## Ejercicio 7: Puertos efímeros

**1. Rango en Linux (`/proc/sys/net/ipv4/ip_local_port_range`):**

Linux usa por defecto `32768–60999`, distinto del `49152–65535` que recomienda IANA.

¿Por qué? Porque el rango de IANA es una recomendación (RFC 6335), no un estándar obligatorio. Linux adoptó su propio rango históricamente antes de que IANA lo formalizara, y mantenerlo evita romper compatibilidad. Que el estándar sea una recomendación implica que distintos SO pueden (y lo hacen) elegir rangos diferentes sin violar ninguna norma técnica, siempre que no choquen con puertos conocidos.

**2. ¿Los puertos de origen están dentro del rango efímero?**

Sí. El SO asigna automáticamente un puerto libre dentro de ese rango a cada `create_connection()`. Los puertos asignados varían (no siguen un patrón fijo; el kernel elige pseudo-aleatoriamente para evitar colisiones y mitigar ataques de predicción).

**3. IPv4 vs IPv6 (`getsockname()`):**

- IPv4: tupla de 2 elementos → `('IP', puerto)`
- IPv6: tupla de 4 elementos → `('IP', puerto, flowinfo, scope_id)`

Forzar con `socket.AF_INET` obliga IPv4; con `socket.AF_INET6` obliga IPv6.

**4. `ss -tn state established`:**

Cada conexión tiene su cuádrupla única. Aunque el IP y puerto de destino sean los mismos para todas (`example.com:80`), cada una tiene un puerto de origen distinto → el SO las distingue sin ambigüedad.

**5. ¿Cuántas conexiones simultáneas al mismo servidor:puerto?**

Tantas como puertos efímeros disponibles: en Linux ~28.000 (`60999 - 32768`).

- Hacia el **mismo servidor y puerto**: límite = tamaño del rango efímero (~28k en Linux).
- Hacia **servidores distintos**: el límite es por cuádrupla; se multiplica por la cantidad de destinos distintos (en teoría hasta 65535 × cantidad de IPs destino).

Esto explica el problema de agotamiento de puertos en balanceadores de carga que salen siempre con la misma IP de origen hacia el mismo backend.

---

*Computación II - 2026 - Clase 12*
