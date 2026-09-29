#!/usr/bin/env python3
"""
Ejercicios 4, 5 y 6: connect() en UDP, broadcast y fragmentación.

Modos:
  connect        → ej 4: connect()+send() vs sendto() contra un puerto vacío
  broadcast_srv  → ej 5.2: servidor que responde DISCOVER? con el hostname
  broadcast_cli  → ej 5: cliente que manda DISCOVER? a 255.255.255.255
  sin_sockopt    → ej 5.1: broadcast sin SO_BROADCAST (PermissionError)
  mtu            → ej 6: datagrama de 60000 bytes y cálculo de probabilidades

Uso:
  python3 ej4_5_6_connect_broadcast_mtu.py connect
  python3 ej4_5_6_connect_broadcast_mtu.py broadcast_srv     # terminal 1
  python3 ej4_5_6_connect_broadcast_mtu.py broadcast_cli     # terminal 2
  python3 ej4_5_6_connect_broadcast_mtu.py mtu
"""
import math
import socket
import sys

PUERTO_VACIO = 9999
PUERTO_DISCOVER = 8082


def connect_udp():
    print('=== 4.1: con connect() ===')
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(2)
    s.connect(('localhost', PUERTO_VACIO))
    s.send(b'hola')
    try:
        s.recv(4096)
    except ConnectionRefusedError:
        print('  ConnectionRefusedError  ← el kernel recibió un ICMP "port unreachable"')
    except TimeoutError:
        print('  timeout')
    s.close()

    print('=== 4.2: sin connect(), con sendto()/recvfrom() ===')
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(2)
    s.sendto(b'hola', ('localhost', PUERTO_VACIO))
    try:
        s.recvfrom(4096)
    except ConnectionRefusedError:
        print('  ConnectionRefusedError')
    except TimeoutError:
        print('  timeout  ← el ICMP llega igual, pero un socket no conectado no sabe')
        print('             a qué destino atribuirlo, así que el kernel no lo reporta')
    s.close()

    print('=== 4.4: un socket conectado filtra otros orígenes ===')
    receptor = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receptor.bind(('localhost', 0))
    socio = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socio.bind(('localhost', 0))
    intruso = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receptor.connect(socio.getsockname())
    intruso.sendto(b'soy el intruso', receptor.getsockname())
    socio.sendto(b'soy el socio', receptor.getsockname())
    receptor.settimeout(1)
    print(f'  recibido: {receptor.recv(100)!r}  (el del intruso se descartó)')
    for x in (receptor, socio, intruso):
        x.close()


def broadcast_srv():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', PUERTO_DISCOVER))       # '' = todas las interfaces, recibe broadcast
    print(f'Esperando DISCOVER? en UDP {PUERTO_DISCOVER}. Ctrl+C para cortar.')
    try:
        while True:
            datos, origen = s.recvfrom(4096)
            if datos.strip() == b'DISCOVER?':
                print(f'  DISCOVER? de {origen}')
                s.sendto(socket.gethostname().encode(), origen)
    except KeyboardInterrupt:
        print('\nChau.')


def broadcast_cli(con_sockopt=True):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if con_sockopt:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.settimeout(2.0)
    try:
        s.sendto(b'DISCOVER?', ('255.255.255.255', PUERTO_DISCOVER))
    except PermissionError as e:
        print(f'PermissionError: {e}  ← sin SO_BROADCAST el kernel no deja inundar la red')
        return
    try:
        while True:
            datos, origen = s.recvfrom(4096)
            print(f'{origen} respondió: {datos!r}')
    except TimeoutError:
        print('(fin de respuestas)')


def mtu():
    print('=== 6: fragmentación ===')
    print('  MTU Ethernet 1500 → payload UDP sin fragmentar = 1500 - 20 (IP) - 8 (UDP) = 1472')
    r = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    r.bind(('localhost', 0))
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.sendto(b'Z' * 60000, r.getsockname())
        r.settimeout(1)
        datos, _ = r.recvfrom(65535)
        print(f'  datagrama de 60000 bytes en localhost: llegaron {len(datos)} bytes')
    except OSError as e:
        # macOS limita el datagrama UDP a 9216 bytes por defecto
        # (sysctl net.inet.udp.maxdgram); Linux permite hasta ~65507.
        print(f'  sendto de 60000 bytes falló: {e}')
        print('  (en macOS: sudo sysctl -w net.inet.udp.maxdgram=65535, o correrlo en Docker)')
    print('  (loopback tiene MTU 65536 en Linux / 16384 en macOS, pero por Ethernet serían')
    print(f'   {math.ceil(60000 / 1480)} fragmentos IP de ≤1480 bytes de datos cada uno)')

    p = 0.05
    frag = math.ceil((60000 + 8) / 1480)
    print(f'\n  Con {p:.0%} de pérdida por paquete:')
    print(f'    datagrama de 1000 B  (1 fragmento):   llega el {(1 - p) * 100:.1f}%')
    print(f'    datagrama de 60000 B ({frag} fragmentos): llega el {(1 - p) ** frag * 100:.1f}%')
    print('  → Si se pierde UN fragmento se pierde el datagrama entero: la probabilidad de')
    print('    éxito es (1-p)^n, cae exponencialmente con la cantidad de fragmentos.')


if __name__ == '__main__':
    modo = sys.argv[1] if len(sys.argv) > 1 else ''
    if modo == 'connect':
        connect_udp()
    elif modo == 'broadcast_srv':
        broadcast_srv()
    elif modo == 'broadcast_cli':
        broadcast_cli()
    elif modo == 'sin_sockopt':
        broadcast_cli(con_sockopt=False)
    elif modo == 'mtu':
        mtu()
    else:
        print(__doc__)
        sys.exit(1)
