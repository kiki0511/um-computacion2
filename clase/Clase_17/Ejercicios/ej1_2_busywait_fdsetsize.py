#!/usr/bin/env python3
"""
Ejercicios 1 y 2: busy-waiting contra select(), y el límite de FD_SETSIZE.

Modos:
  cpu        → 1.2/1.4: mide el CPU que consume cada servidor SIN clientes
               (busy-wait vs select), durante 2 segundos
  busywait   → el servidor con polling activo del enunciado (puerto 8080)
  fdsetsize  → 2.3: select() con UN solo socket de fd alto falla; poll() no

Uso:
  python3 ej1_2_busywait_fdsetsize.py cpu
  python3 ej1_2_busywait_fdsetsize.py fdsetsize
"""
import resource
import select
import socket
import subprocess
import sys
import time

BUSY = r'''
import socket
srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(('localhost', {puerto})); srv.listen(5)
srv.setblocking(False)
conexiones = []
while True:
    try:
        conn, _ = srv.accept()
        conn.setblocking(False)
        conexiones.append(conn)
    except BlockingIOError:
        pass
    for c in list(conexiones):
        try:
            datos = c.recv(4096)
            if datos: c.sendall(datos)
            else: conexiones.remove(c); c.close()
        except BlockingIOError:
            pass
'''

SELECT = r'''
import select, socket
srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(('localhost', {puerto})); srv.listen(5)
vigilados = [srv]
while True:
    listos, _, _ = select.select(vigilados, [], [])     # duerme hasta que haya algo
    for s in listos:
        if s is srv:
            c, _ = srv.accept(); vigilados.append(c)
        else:
            d = s.recv(4096)
            if d: s.sendall(d)
            else: vigilados.remove(s); s.close()
'''


def cpu_de(codigo, puerto, segundos=2.0):
    """Lanza el servidor, espera `segundos` sin clientes, devuelve % de CPU."""
    p = subprocess.Popen([sys.executable, '-c', codigo.format(puerto=puerto)])
    time.sleep(0.3)
    antes = cpu_hijo(p.pid)
    time.sleep(segundos)
    despues = cpu_hijo(p.pid)
    p.kill()
    p.wait()
    return (despues - antes) / segundos * 100


def cpu_hijo(pid):
    """Segundos de CPU consumidos por el proceso (Linux y macOS vía ps)."""
    salida = subprocess.run(['ps', '-o', 'time=', '-p', str(pid)],
                            capture_output=True, text=True).stdout.strip()
    # formato [[dd-]hh:]mm:ss(.cc)
    partes = salida.replace('-', ':').split(':')
    total = 0.0
    for p in partes:
        total = total * 60 + float(p)
    return total


def cpu():
    print('=== CPU con el servidor ocioso (nadie conectado), 2 segundos ===')
    print(f'  busy-wait : {cpu_de(BUSY, 8181):5.0f}% de un núcleo')
    print(f'  select()  : {cpu_de(SELECT, 8182):5.0f}% de un núcleo')
    print('  → El busy-wait pregunta sin parar "¿hay algo?" y el kernel responde "no"')
    print('    (BlockingIOError) millones de veces por segundo. select() le pide al')
    print('    kernel que lo DUERMA hasta que haya un evento: 0% de CPU esperando.')


def busywait():
    print('Servidor con polling activo en 8080. Mirá el CPU con top. Ctrl+C para cortar.')
    try:
        exec(BUSY.format(puerto=8080))
    except KeyboardInterrupt:
        pass


def fdsetsize():
    print('=== 2.3: FD_SETSIZE ===')
    blando, duro = resource.getrlimit(resource.RLIMIT_NOFILE)
    if blando < 1200:
        resource.setrlimit(resource.RLIMIT_NOFILE, (min(2048, duro), duro))
    relleno = [socket.socket() for _ in range(1100)]
    alto = relleno[-1]
    print(f'  fd del socket vigilado: {alto.fileno()}  (vigilo UNO solo)')
    try:
        select.select([alto], [], [], 0)
        print('  select(): funcionó (este sistema no aplica el límite)')
    except (ValueError, OSError) as e:
        print(f'  select(): {type(e).__name__}: {e}')
    if hasattr(select, 'poll'):
        p = select.poll()
        p.register(alto, select.POLLIN)
        print(f'  poll()  : OK, devolvió {p.poll(0)}')
    print('  → El límite de select() es el NÚMERO de fd (< 1024), no la cantidad:')
    print('    usa un bitmap de 1024 bits indexado por número de descriptor.')
    for s in relleno:
        s.close()


if __name__ == '__main__':
    modo = sys.argv[1] if len(sys.argv) > 1 else ''
    acciones = {'cpu': cpu, 'busywait': busywait, 'fdsetsize': fdsetsize}
    if modo not in acciones:
        print(__doc__)
        sys.exit(1)
    acciones[modo]()
