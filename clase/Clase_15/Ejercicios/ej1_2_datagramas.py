#!/usr/bin/env python3
"""
Ejercicios 1 y 2: primer contacto con datagramas y sus límites.

Modos:
  dos_clientes → punto 1.9: un servidor UDP sin threads atiende a dos
                 clientes que mandan a la vez
  limites      → punto 2.1: tres sendto() = tres recvfrom()
  trunca       → punto 2.2: recvfrom(10) sobre un datagrama de 100 bytes

Uso:
  python3 ej1_2_datagramas.py [dos_clientes|limites|trunca|todo]
"""
import socket
import sys
import threading
import time


def servidor_eco(sock, fin):
    """Un solo socket, un solo hilo, cualquier cantidad de clientes."""
    sock.settimeout(0.2)
    while not fin.is_set():
        try:
            datos, origen = sock.recvfrom(65535)
        except TimeoutError:
            continue
        print(f'  [servidor] {len(datos):>3} bytes de {origen}: {datos!r}')
        sock.sendto(datos.upper(), origen)


def dos_clientes():
    print('=== 1.9: dos clientes a la vez, servidor sin concurrencia ===')
    srv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    srv.bind(('localhost', 0))
    destino = srv.getsockname()
    fin = threading.Event()
    hilo = threading.Thread(target=servidor_eco, args=(srv, fin))
    hilo.start()

    def cliente(nombre):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as c:
            c.settimeout(2)
            for i in range(3):
                c.sendto(f'{nombre}-{i}'.encode(), destino)
                resp, _ = c.recvfrom(65535)
                print(f'  [{nombre}] recibió {resp!r} (puerto efímero {c.getsockname()[1]})')

    clientes = [threading.Thread(target=cliente, args=(n,)) for n in ('A', 'B')]
    for c in clientes:
        c.start()
    for c in clientes:
        c.join()
    fin.set()
    hilo.join()
    srv.close()
    print('  → Los dos fueron atendidos por el mismo hilo: no hay accept() ni un socket por')
    print('    cliente; cada datagrama trae su origen y se procesa en microsegundos.\n')


def limites():
    print('=== 2.1: los límites se preservan ===')
    r = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    r.bind(('localhost', 0))
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for msg in (b'uno', b'dos', b'tres'):
        s.sendto(msg, r.getsockname())
    r.settimeout(0.5)
    n = 0
    try:
        while True:
            datos, _ = r.recvfrom(65535)
            n += 1
            print(f'  recvfrom #{n}: {datos!r}')
    except TimeoutError:
        pass
    print(f'  → 3 sendto() = {n} recvfrom(). En TCP podían llegar pegados en uno solo.\n')
    r.close()
    s.close()


def trunca():
    print('=== 2.2: el buffer chico trunca ===')
    r = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    r.bind(('localhost', 0))
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.sendto(b'X' * 100, r.getsockname())
    time.sleep(0.05)
    datos, _ = r.recvfrom(10)
    print(f'  primer recvfrom: {len(datos)} bytes')
    r.settimeout(1.0)
    try:
        datos2, _ = r.recvfrom(65535)
        print(f'  segundo recvfrom: {len(datos2)} bytes')
    except TimeoutError:
        print('  segundo recvfrom: nada')
    print('  → Los 90 bytes restantes se DESCARTARON: el datagrama se entrega entero')
    print('    o truncado, nunca en partes. Usar siempre recvfrom(65535).\n')
    r.close()
    s.close()


if __name__ == '__main__':
    modo = sys.argv[1] if len(sys.argv) > 1 else 'todo'
    acciones = {'dos_clientes': [dos_clientes], 'limites': [limites],
                'trunca': [trunca], 'todo': [dos_clientes, limites, trunca]}
    if modo not in acciones:
        print(__doc__)
        sys.exit(1)
    for f in acciones[modo]:
        f()
