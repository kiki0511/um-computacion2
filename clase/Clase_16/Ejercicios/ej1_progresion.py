#!/usr/bin/env python3
"""
Ejercicio 1: Recorrer la progresión de socketserver (pasos 1 a 6).

Cada modo es uno de los pasos, escrito desde cero:

  minimo     → 1.1  servidor de 5 líneas: type(self.request), id(self)
  concurrencia → 1.3 sleep(1) en handle: secuencial vs threading vs forking
  framing    → 1.4  BaseRequestHandler+recv vs StreamRequestHandler+rfile
  estado     → 1.5  contador en el handler (siempre 1) vs en el servidor
  errores    → 1.6  excepción en handle(): orden de setup/handle/finish/handle_error

Uso:
  python3 ej1_progresion.py minimo          # y en otra terminal: nc localhost 8080
  python3 ej1_progresion.py concurrencia|framing|estado|errores|todo
"""
import os
import socket
import socketserver
import sys
import threading
import time


def en_segundo_plano(servidor):
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    return servidor


def cerrar(servidor):
    servidor.shutdown()
    servidor.server_close()


# ─────────────────────────────────────────────
# 1.1 El mínimo
# ─────────────────────────────────────────────

class Minimo(socketserver.BaseRequestHandler):
    def handle(self):
        print(f'  type(self.request)={type(self.request).__name__}  id(self)={id(self)}')
        self.request.sendall(self.request.recv(1024).upper())


def minimo():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(('localhost', 8080), Minimo) as srv:
        print('Escuchando en 8080 (nc localhost 8080). Ctrl+C para cortar.')
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass


# ─────────────────────────────────────────────
# 1.3 Concurrencia
# ─────────────────────────────────────────────

class Lento(socketserver.BaseRequestHandler):
    def handle(self):
        time.sleep(1)
        self.request.sendall(f'pid={os.getpid()}'.encode())


def concurrencia():
    print('=== 1.3: dos clientes contra un handler de 1s ===')
    clases = [socketserver.TCPServer, socketserver.ThreadingTCPServer]
    if hasattr(os, 'fork'):
        clases.append(socketserver.ForkingTCPServer)
    for C in clases:
        C.allow_reuse_address = True
        srv = en_segundo_plano(C(('localhost', 0), Lento))
        tiempos, pids = [], []

        def cliente():
            t0 = time.perf_counter()
            with socket.create_connection(srv.server_address) as c:
                pids.append(c.recv(64).decode())
            tiempos.append(time.perf_counter() - t0)

        hilos = [threading.Thread(target=cliente) for _ in range(2)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()
        cerrar(srv)
        print(f'  {C.__name__:<18} segundo cliente: {max(tiempos):.2f}s   {sorted(set(pids))}')
    print()


# ─────────────────────────────────────────────
# 1.4 Framing
# ─────────────────────────────────────────────

class ConRecv(socketserver.BaseRequestHandler):
    def handle(self):
        self.server.log.append(('recv', self.request.recv(1024)))


class ConRfile(socketserver.StreamRequestHandler):
    def handle(self):
        for linea in self.rfile:
            self.server.log.append(('rfile', linea))


def framing():
    print("=== 1.4: mandar 'UNO\\nDOS\\n' ===")
    for handler in (ConRecv, ConRfile):
        srv = socketserver.TCPServer(('localhost', 0), handler)
        srv.log = []
        en_segundo_plano(srv)
        with socket.create_connection(srv.server_address) as c:
            c.sendall(b'UNO\nDOS\n')
        time.sleep(0.2)
        cerrar(srv)
        print(f'  {handler.__name__:<8} → {srv.log}')
    print('  → recv(1024) trae todo en un bloque; rfile itera línea por línea.\n')


# ─────────────────────────────────────────────
# 1.5 Estado
# ─────────────────────────────────────────────

class ContadorEnHandler(socketserver.BaseRequestHandler):
    contador = 0

    def handle(self):
        self.contador += 1            # crea un atributo de INSTANCIA, nuevo en cada conexión
        self.request.sendall(str(self.contador).encode())


class ContadorEnServidor(socketserver.BaseRequestHandler):
    def handle(self):
        with self.server.lock:
            self.server.contador += 1
            valor = self.server.contador
        self.request.sendall(str(valor).encode())


class ServidorConEstado(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.contador = 0
        self.lock = threading.Lock()


def estado():
    print('=== 1.5: dónde vive el contador ===')
    for handler in (ContadorEnHandler, ContadorEnServidor):
        srv = en_segundo_plano(ServidorConEstado(('localhost', 0), handler))
        resp = []
        for _ in range(4):
            with socket.create_connection(srv.server_address) as c:
                resp.append(c.recv(16).decode())
        cerrar(srv)
        print(f'  {handler.__name__:<18} → {resp}')

    srv = en_segundo_plano(ServidorConEstado(('localhost', 0), ContadorEnServidor))

    def rafaga():
        for _ in range(20):
            with socket.create_connection(srv.server_address) as c:
                c.recv(16)

    hilos = [threading.Thread(target=rafaga) for _ in range(10)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    cerrar(srv)
    print(f'  200 conexiones concurrentes con Lock → contador = {srv.contador}\n')


# ─────────────────────────────────────────────
# 1.6 Errores
# ─────────────────────────────────────────────

class Fragil(socketserver.StreamRequestHandler):
    def setup(self):
        self.server.eventos.append('setup')
        super().setup()

    def handle(self):
        self.server.eventos.append('handle')
        if self.rfile.readline().strip() == b'ROMPER':
            raise ValueError('input inválido')
        self.wfile.write(b'ok\n')

    def finish(self):
        self.server.eventos.append('finish')
        super().finish()


class ServidorFragil(socketserver.TCPServer):
    allow_reuse_address = True

    def handle_error(self, request, client_address):
        self.eventos.append('handle_error')     # el default imprime el traceback


def errores():
    print('=== 1.6: excepción en handle() ===')
    srv = ServidorFragil(('localhost', 0), Fragil)
    srv.eventos = []
    en_segundo_plano(srv)
    for msg in (b'ROMPER\n', b'hola\n'):
        with socket.create_connection(srv.server_address) as c:
            c.sendall(msg)
            respuesta = c.recv(16)
        print(f'  mandé {msg!r:<11} respuesta={respuesta!r:<8} eventos={srv.eventos}')
        srv.eventos.clear()
    cerrar(srv)
    print('  → El servidor sigue vivo. finish() se ejecuta aunque handle() falle')
    print('    (está en un finally), y handle_error() viene DESPUÉS.\n')


if __name__ == '__main__':
    modo = sys.argv[1] if len(sys.argv) > 1 else 'todo'
    modos = {'minimo': [minimo], 'concurrencia': [concurrencia], 'framing': [framing],
             'estado': [estado], 'errores': [errores],
             'todo': [concurrencia, framing, estado, errores]}
    if modo not in modos:
        print(__doc__)
        sys.exit(1)
    for f in modos[modo]:
        f()
