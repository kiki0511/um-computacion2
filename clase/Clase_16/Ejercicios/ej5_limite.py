#!/usr/bin/env python3
"""
Ejercicio 5: El límite de socketserver (prepara la clase 17).

Levanta ../comandos.py en un proceso aparte, abre N conexiones que quedan
abiertas sin hacer nada, y mide threads y memoria (RSS) del servidor.

Uso:
  python3 ej5_limite.py                 # 1, 200 y 1000 conexiones
  python3 ej5_limite.py 200 1000 2000
"""
import os
import platform
import resource
import socket
import subprocess
import sys
import time

PUERTO = 8095
COMANDOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'comandos.py')


def hilos_de(pid):
    if platform.system() == 'Linux':
        return len(os.listdir(f'/proc/{pid}/task'))
    # macOS: ps -M lista un renglón por thread (más el encabezado)
    salida = subprocess.run(['ps', '-M', '-p', str(pid)], capture_output=True, text=True).stdout
    return len(salida.strip().splitlines()) - 1


def rss_mb(pid):
    salida = subprocess.run(['ps', '-o', 'rss=', '-p', str(pid)],
                            capture_output=True, text=True).stdout
    return int(salida.strip()) / 1024


def medir(n):
    srv = subprocess.Popen([sys.executable, COMANDOS, str(PUERTO)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.5)
    socks, error = [], ''
    try:
        for _ in range(n):
            socks.append(socket.create_connection(('localhost', PUERTO), timeout=3))
    except OSError as e:
        error = f'{type(e).__name__}: {e}'
    time.sleep(1.0)                                  # que el servidor cree los threads
    try:
        hilos, mem = hilos_de(srv.pid), rss_mb(srv.pid)
    except Exception as e:                           # el servidor pudo haber muerto
        hilos, mem = '-', 0
        error = error or str(e)
    for s in socks:
        s.close()
    srv.terminate()
    srv.wait()
    print(f'{n:>6} pedidas | {len(socks):>6} abiertas | {hilos!s:>6} threads | '
          f'{mem:7.1f} MB RSS {("| " + error) if error else ""}')


if __name__ == '__main__':
    blando, duro = resource.getrlimit(resource.RLIMIT_NOFILE)
    # el cliente también usa un fd por conexión: subir el límite blando si se puede
    resource.setrlimit(resource.RLIMIT_NOFILE, (min(max(blando, 4096), duro), duro))
    print(f'ulimit -n (blando del cliente): {resource.getrlimit(resource.RLIMIT_NOFILE)[0]}\n')
    cantidades = [int(x) for x in sys.argv[1:]] or [1, 200, 1000]
    for n in cantidades:
        medir(n)
