#!/usr/bin/env python3
"""
Ejercicios adicionales - Clase 17 (I/O multiplexing).

Un servidor eco con selectors que integra dos adicionales:

  1. Timeout de inactividad: desconecta a quien no manda nada en N segundos.
     sel.select(timeout=...) vuelve aunque no haya eventos, y en cada vuelta
     se revisa quién venció.

  2. Self-pipe para SIGINT/SIGTERM (clase 6): el handler de la señal solo
     escribe un byte en un pipe; el extremo de lectura está registrado en el
     selector, así que la señal llega como UN EVENTO MÁS del bucle y el
     cierre se hace ordenadamente desde el loop, no desde el handler.

Uso:
  python3 ej_extra_adicionales.py [puerto] [timeout]
  nc localhost 8080        # no escribas nada y esperá el timeout
  Ctrl+C                   # cierre ordenado vía self-pipe
"""
import os
import selectors
import signal
import socket
import sys
import time

PUERTO = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
TIMEOUT = float(sys.argv[2]) if len(sys.argv) > 2 else 30.0

sel = selectors.DefaultSelector()
ultima_actividad = {}           # socket -> time.monotonic() del último dato

# ── self-pipe ─────────────────────────────────
pipe_r, pipe_w = os.pipe()
os.set_blocking(pipe_r, False)
os.set_blocking(pipe_w, False)


def handler_senal(signum, _frame):
    # Async-signal-safe: solo escribir un byte. Nada de prints ni locks acá.
    try:
        os.write(pipe_w, bytes([signum]))
    except BlockingIOError:
        pass


def senal_recibida(fd):
    signum = os.read(fd, 1)[0]
    print(f'\n[loop] recibí {signal.Signals(signum).name} como evento: cierro ordenadamente')
    return 'salir'


# ── servidor ──────────────────────────────────
def aceptar(srv):
    conn, direccion = srv.accept()
    conn.setblocking(False)
    sel.register(conn, selectors.EVENT_READ, atender)
    ultima_actividad[conn] = time.monotonic()
    print(f'+ {direccion}')


def cerrar(conn, motivo):
    print(f'- {conn.getpeername() if conn.fileno() != -1 else "?"} ({motivo})')
    ultima_actividad.pop(conn, None)
    sel.unregister(conn)
    conn.close()


def atender(conn):
    try:
        datos = conn.recv(4096)
    except ConnectionResetError:
        datos = b''
    if not datos:
        cerrar(conn, 'cerró')
        return
    ultima_actividad[conn] = time.monotonic()
    conn.sendall(datos)


def revisar_timeouts():
    ahora = time.monotonic()
    for conn, t in list(ultima_actividad.items()):
        if ahora - t > TIMEOUT:
            try:
                conn.sendall(f'Desconectado por inactividad ({TIMEOUT:.0f}s)\n'.encode())
            except OSError:
                pass
            cerrar(conn, 'timeout')


def main():
    signal.signal(signal.SIGINT, handler_senal)
    signal.signal(signal.SIGTERM, handler_senal)

    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('0.0.0.0', PUERTO))
    srv.listen(128)
    srv.setblocking(False)
    sel.register(srv, selectors.EVENT_READ, aceptar)
    sel.register(pipe_r, selectors.EVENT_READ, senal_recibida)
    print(f'Eco en {PUERTO}, timeout {TIMEOUT}s, PID {os.getpid()}. Ctrl+C para salir.')

    corriendo = True
    while corriendo:
        # timeout del select = cada cuánto revisar inactivos aunque no pase nada
        for clave, _ in sel.select(timeout=min(1.0, TIMEOUT)):
            if clave.data(clave.fileobj) == 'salir':
                corriendo = False
        revisar_timeouts()

    for conn in list(ultima_actividad):
        cerrar(conn, 'servidor apagándose')
    sel.close()
    srv.close()
    print('[loop] listo, chau.')


if __name__ == '__main__':
    main()
