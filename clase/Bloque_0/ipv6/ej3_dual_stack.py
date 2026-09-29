#!/usr/bin/env python3
"""
Bloque 0 - IPv6 - Ejercicio 3 (OBLIGATORIO): Servidor dual-stack.

Un solo socket AF_INET6 que atiende clientes IPv4 e IPv6.

Partes:
  A  → servidor solo IPv4: un cliente ::1 no puede conectarse
  B  → servidor dual-stack (IPV6_V6ONLY = 0 explícito)
  C  → IPV6_V6ONLY = 1: el cliente IPv4 queda afuera
  D  → normalizar(): ::ffff:1.2.3.4 -> 1.2.3.4
  E  → cliente agnóstico con getaddrinfo() que prueba todas las direcciones

Modos:
  python3 ej3_dual_stack.py demo                 # corre A, B, C, D y E solo
  python3 ej3_dual_stack.py servidor [puerto]    # dual-stack
  python3 ej3_dual_stack.py servidor6 [puerto]   # V6ONLY=1
  python3 ej3_dual_stack.py servidor4 [puerto]   # solo IPv4
  python3 ej3_dual_stack.py cliente HOST [puerto]

Probar a mano (otra terminal):
  nc 127.0.0.1 8080      # cliente IPv4
  nc ::1 8080            # cliente IPv6
"""
import ipaddress
import socket
import sys
import threading
import time

PUERTO = 8080


# ─────────────────────────────────────────────
# Parte D: normalizar direcciones mapeadas
# ─────────────────────────────────────────────

def normalizar(host: str) -> str:
    """
    ::ffff:1.2.3.4 -> 1.2.3.4. Cualquier otra dirección queda igual.

    El mismo cliente IPv4 aparece como '127.0.0.1' en un servidor IPv4
    y como '::ffff:127.0.0.1' en uno dual-stack. Sin normalizar, una
    lista de bloqueo con '1.2.3.4' no matchearía nunca.
    """
    try:
        ip = ipaddress.ip_address(host.split('%')[0])   # sacar scope id
    except ValueError:
        return host
    if ip.version == 6 and ip.ipv4_mapped is not None:
        return str(ip.ipv4_mapped)
    return host


# ─────────────────────────────────────────────
# Servidores (Partes A, B y C)
# ─────────────────────────────────────────────

def crear_servidor(modo: str, puerto: int) -> socket.socket:
    """modo: 'ipv4', 'dual' o 'v6only'."""
    if modo == 'ipv4':
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', puerto))
    else:
        s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # SIEMPRE explícito: el default cambia según el SO
        # (Linux: 0 por defecto; Windows y OpenBSD: 1).
        v6only = 1 if modo == 'v6only' else 0
        s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, v6only)
        s.bind(('::', puerto))
    s.listen(5)
    return s


def atender(conn: socket.socket, direccion: tuple) -> None:
    """Responde con la familia y la dirección con la que se ve al cliente."""
    # direccion tiene 2 elementos en IPv4 y 4 en IPv6 (host, port, flowinfo, scope_id):
    # por eso se indexa en vez de desempaquetar con host, puerto = direccion
    host, puerto = direccion[0], direccion[1]
    familia = 'IPv6' if conn.family == socket.AF_INET6 else 'IPv4'
    linea = f'{familia} cruda={host} normalizada={normalizar(host)} puerto={puerto}'
    print(f'  [servidor] {linea}')
    with conn:
        conn.sendall((linea + '\n').encode())


def servir(s: socket.socket, max_clientes: int | None = None) -> None:
    atendidos = 0
    with s:
        while max_clientes is None or atendidos < max_clientes:
            conn, direccion = s.accept()
            atender(conn, direccion)
            atendidos += 1


# ─────────────────────────────────────────────
# Parte E: cliente agnóstico de familia
# ─────────────────────────────────────────────

def conectar(host: str, puerto: int, timeout: float = 5) -> socket.socket:
    """
    Prueba TODAS las direcciones que devuelve getaddrinfo, en orden.

    Quedarse con la primera es un error: el sistema puede devolver primero
    una IPv6 aunque no haya ruta IPv6 (muy común en Argentina), y la
    conexión fallaría teniendo una IPv4 perfectamente válida detrás.
    """
    ultimo_error: OSError | None = None
    for familia, tipo, proto, _, direccion in socket.getaddrinfo(
            host, puerto, type=socket.SOCK_STREAM):
        s = socket.socket(familia, tipo, proto)
        s.settimeout(timeout)
        try:
            s.connect(direccion)
            return s
        except OSError as e:
            print(f'  [cliente] {direccion[0]} falló: {e}; pruebo la siguiente')
            ultimo_error = e
            s.close()
    raise ultimo_error or OSError(f'getaddrinfo no devolvió nada para {host}')


def pedir(host: str, puerto: int) -> str:
    with conectar(host, puerto, timeout=2) as s:
        return s.recv(1024).decode().strip()


# ─────────────────────────────────────────────
# Demo completa
# ─────────────────────────────────────────────

def probar(modo: str, puerto: int, hosts: list[str]) -> None:
    srv = crear_servidor(modo, puerto)
    hilo = threading.Thread(target=servir, args=(srv,), daemon=True)
    hilo.start()
    time.sleep(0.1)
    for h in hosts:
        try:
            print(f'  [cliente {h}] -> {pedir(h, puerto)}')
        except OSError as e:
            print(f'  [cliente {h}] NO conecta: {type(e).__name__}: {e}')
    srv.close()


def demo() -> None:
    print('=== Parte A: servidor solo IPv4 ===')
    probar('ipv4', 8091, ['127.0.0.1', '::1'])

    print('\n=== Parte B: dual-stack (V6ONLY=0) ===')
    probar('dual', 8092, ['127.0.0.1', '::1'])

    print('\n=== Parte C: V6ONLY=1 ===')
    probar('v6only', 8093, ['127.0.0.1', '::1'])

    print('\n=== Parte D: normalizar ===')
    for d in ['::ffff:127.0.0.1', '::ffff:192.168.1.10', '::1',
              '2001:db8::1', '10.0.0.1', 'no-es-ip']:
        print(f'  {d:<22} -> {normalizar(d)}')

    print('\n=== Parte E: orden de getaddrinfo("localhost") ===')
    for fam, _, _, _, dir_ in socket.getaddrinfo('localhost', 8092,
                                                 type=socket.SOCK_STREAM):
        print(f'  {fam.name:<9} {dir_}')


if __name__ == '__main__':
    args = sys.argv[1:]
    modo = args[0] if args else 'demo'
    if modo == 'demo':
        demo()
    elif modo in ('servidor', 'servidor6', 'servidor4'):
        puerto = int(args[1]) if len(args) > 1 else PUERTO
        tipo = {'servidor': 'dual', 'servidor6': 'v6only', 'servidor4': 'ipv4'}[modo]
        print(f'Servidor {tipo} en puerto {puerto}. Ctrl+C para cortar.')
        try:
            servir(crear_servidor(tipo, puerto))
        except KeyboardInterrupt:
            print('\nChau.')
    elif modo == 'cliente':
        host = args[1] if len(args) > 1 else 'localhost'
        puerto = int(args[2]) if len(args) > 2 else PUERTO
        print(pedir(host, puerto))
    else:
        print(__doc__)
        sys.exit(1)
