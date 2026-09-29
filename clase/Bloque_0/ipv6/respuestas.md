# Bloque 0 — IPv6: respuestas

El código del obligatorio está en `ej3_dual_stack.py` (`python3 ej3_dual_stack.py demo`).

## Ejercicio 1: Leer y escribir direcciones

| # | Original | Comprimida |
|---|----------|------------|
| 1 | `2001:0db8:0000:0000:0000:ff00:0042:8329` | `2001:db8::ff00:42:8329` |
| 2 | `0000:...:0001` | `::1` |
| 3 | `fe80:0000:0000:0000:0202:b3ff:fe1e:8329` | `fe80::202:b3ff:fe1e:8329` |
| 4 | `2001:0db8:0000:0000:0001:0000:0000:0001` | `2001:db8::1:0:0:1` |

5. `::` significa "todos los grupos de ceros que falten para llegar a 8". Si aparece dos veces no se sabe cuántos ceros van en cada una. `2001:db8::1::1` podría ser `2001:db8:0:1:0:0:0:1` o `2001:db8:0:0:0:1:0:1`. Por eso se permite una sola vez; cuando empatan dos secuencias de igual largo se comprime la primera (RFC 5952), como en la 4.

Expandidas:
- 6: `0000:0000:0000:0000:0000:0000:0000:0001`
- 7: `2001:0db8:0000:0000:0000:8a2e:0370:7334`
- 8: `ff02:0000:0000:0000:0000:0000:0000:0001`

9. `2001:db8::/32` está reservado para documentación (RFC 3849), igual que `192.0.2.0/24` en IPv4. No es ruteable, así que la stdlib la marca como privada/reservada.
10. `is_global` solo mira si el rango no está en la tabla de reservados; no tiene en cuenta que multicast es otra categoría. Conclusión: hay que combinar flags (`is_multicast`, `is_link_local`, etc.), no confiar en uno solo.

## Ejercicio 2: Las direcciones de tu máquina

- Una `fe80::` por cada interfaz activa. Con Docker hay muchas porque cada `veth`/bridge es una interfaz con su propia link-local.
- Un `/64` deja 64 bits para hosts (2⁶⁴ direcciones) contra 8 bits (254 hosts) de un `/24` doméstico.
- `ping6 fe80::1` sin interfaz es ambiguo: la misma link-local puede existir en todos los enlaces. Hace falta el scope (`%en0` en Mac, `%eth0` en Linux).
- `getsockname()` en IPv6 devuelve `(host, puerto, flowinfo, scope_id)`. Por eso `host, puerto = sock.getsockname()` tira `ValueError: too many values to unpack`. Lo portable es `host, puerto = addr[0], addr[1]`.

## Ejercicio 3: Servidor dual-stack (obligatorio)

**Parte A.** Con el servidor IPv4 (`0.0.0.0`), el cliente `::1` recibe `ConnectionRefusedError`: nadie escucha en el puerto de la familia IPv6. `0.0.0.0` significa "todas las IPv4", no "todas las direcciones".

**Parte B.** Con `setsockopt(IPPROTO_IPV6, IPV6_V6ONLY, 0)` y `bind(('::', 8080))` conectan las dos familias. El cliente IPv4 se ve como `::ffff:127.0.0.1`. El prefijo es `::ffff:0:0/96` y son las **direcciones IPv4 mapeadas en IPv6** (IPv4-mapped).

**Parte C.** Con `V6ONLY=1`, el cliente IPv4 recibe `ConnectionRefusedError`: el socket solo acepta IPv6. El default está en `/proc/sys/net/ipv6/bindv6only` en Linux (0) y en `sysctl net.inet6.ip6.v6only` en macOS. Conviene ponerlo explícito porque el default cambia entre sistemas (Windows y OpenBSD traen 1). El mismo código se comportaría distinto en la máquina de un compañero.

**Parte D.** `normalizar()` usa `ipaddress.ip_address(h).ipv4_mapped`. Importa porque una lista de bloqueo con `1.2.3.4` no matchea `::ffff:1.2.3.4`: el atacante entraría igual solo porque el servidor es dual-stack. Lo mismo pasa con los logs y los rate limiters por IP.

**Parte E.** `conectar()` recorre todo lo que devuelve `getaddrinfo()`. Para `localhost` suele venir primero `::1` y después `127.0.0.1`. Elegir solo la primera es un error: si no hay ruta IPv6 (lo normal en Argentina), la primera falla y hay una IPv4 que funciona justo detrás. `socket.create_connection()` hace exactamente este bucle.

## Ejercicio 4: getaddrinfo

- `'http'` funciona: el número sale de `/etc/services` (`http 80/tcp`). Ahí también están `ssh 22`, `https 443` y `smtp 25`.
- Un nombre inexistente lanza `socket.gaierror`.
- `AF_UNSPEC` es el default: pasarlo explícito no cambia nada.

## Ejercicio 5: UDP sobre IPv6

Solo cambia `AF_INET6` y la dirección `::1`. `recvfrom()` devuelve una tupla de 4 elementos en vez de 2. El checksum UDP es obligatorio en IPv6 porque IPv6 eliminó el checksum de la capa de red: sin él no habría ninguna verificación de integridad del encabezado ni del payload.

## Ejercicio 6: Diferencias del protocolo

1. Un encabezado de tamaño fijo (40 bytes) se parsea sin leer un campo de longitud: el router procesa más rápido y en hardware.
2. Se pudo eliminar el checksum porque las capas de enlace (Ethernet CRC) y de transporte (TCP/UDP, ahora obligatorio) ya verifican. Además los routers se ahorran recalcularlo en cada salto al decrementar el hop limit.
3. Si los routers no fragmentan, el emisor tiene que descubrir el MTU del camino. Para eso depende de que le lleguen los ICMPv6 *Packet Too Big*.
4. Un piso de 1280 bytes le garantiza al emisor un tamaño seguro sin fragmentar y hace viable el path MTU discovery.
5. Bloquear ICMPv6 completo rompe mucho más que en IPv4, porque IPv6 usa ICMPv6 para funciones básicas:
   - **Neighbor Discovery** (reemplazo de ARP): sin él no se resuelven direcciones en la LAN.
   - **Packet Too Big**: sin él se rompe el path MTU discovery, y las conexiones con paquetes grandes se cuelgan.
   - También dejan de andar Router Advertisement y SLAAC (autoconfiguración).
