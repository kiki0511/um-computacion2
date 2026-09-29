#!/usr/bin/env python3
"""
Ejercicio 2 (OBLIGATORIO): Los mixins.

Partes:
  A → leer ThreadingMixIn / ForkingMixIn con inspect
  B → orden de herencia: MRO, quién provee process_request, y medición
      con clientes lentos (Bien concurre, Mal no, y ninguno da error)
  C → contador compartido con ForkingTCPServer: falla; arreglo con
      multiprocessing.Value creado en el __init__ del servidor
  D → daemon_threads: servidor con un cliente colgado que no termina

Modos:
  python3 ej2_mixins.py leer          # Parte A
  python3 ej2_mixins.py orden         # Parte B
  python3 ej2_mixins.py forking       # Parte C
  python3 ej2_mixins.py daemon        # Parte D (automático, con subprocess)
  python3 ej2_mixins.py todo
"""
import inspect
import multiprocessing
import os
import socket
import socketserver
import subprocess
import sys
import threading
import time

LENTO = 1.0        # segundos que tarda cada handler "lento"


# ─────────────────────────────────────────────
# Parte A: leer el código
# ─────────────────────────────────────────────

def parte_a():
    print('=== Parte A: qué define cada mixin ===')
    for mixin in (socketserver.ThreadingMixIn, socketserver.ForkingMixIn):
        metodos = [n for n, v in vars(mixin).items() if inspect.isfunction(v)]
        print(f'  {mixin.__name__}: {metodos}')

    print('\n  BaseServer.process_request (secuencial):')
    for linea in inspect.getsource(socketserver.BaseServer.process_request).splitlines():
        if linea.strip().startswith('self.'):
            print(f'    {linea.strip()}')
    print('\n  ThreadingMixIn.process_request (lanza un thread):')
    fuente = inspect.getsource(socketserver.ThreadingMixIn.process_request)
    for linea in fuente.splitlines():
        if 'Thread(' in linea or 'start()' in linea or 'daemon' in linea:
            print(f'    {linea.strip()}')

    print('\n  ForkingMixIn: dónde cosecha a los hijos')
    fuente = inspect.getsource(socketserver.ForkingMixIn)
    for nombre in ('collect_children', 'service_actions', 'waitpid'):
        print(f'    aparece "{nombre}": {nombre in fuente}')
    print('    → service_actions() se llama en cada vuelta de serve_forever()')
    print('      y llama a collect_children(), que hace os.waitpid(..., WNOHANG).')

    fuente = inspect.getsource(socketserver.ThreadingTCPServer)
    print(f'\n  Definición completa de ThreadingTCPServer:\n    {fuente.strip()}')
    print()


# ─────────────────────────────────────────────
# Parte B: el orden de herencia
# ─────────────────────────────────────────────

class HandlerLento(socketserver.BaseRequestHandler):
    def handle(self):
        time.sleep(LENTO)
        self.request.sendall(b'ok')


class Bien(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


class Mal(socketserver.TCPServer, socketserver.ThreadingMixIn):
    allow_reuse_address = True
    daemon_threads = True


def medir_dos_clientes(clase_servidor):
    """Levanta el servidor, conecta 2 clientes a la vez, mide el total."""
    srv = clase_servidor(('localhost', 0), HandlerLento)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    def cliente():
        with socket.create_connection(srv.server_address) as c:
            c.recv(10)

    t0 = time.perf_counter()
    hilos = [threading.Thread(target=cliente) for _ in range(2)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    total = time.perf_counter() - t0
    srv.shutdown()
    srv.server_close()
    return total


def parte_b():
    print('=== Parte B: el orden de herencia ===')
    for C in (Bien, Mal):
        mro = [k.__name__ for k in C.__mro__][:4]
        quien = next(k.__name__ for k in C.__mro__ if 'process_request' in k.__dict__)
        print(f'  {C.__name__:<5} MRO: {mro}')
        print(f'        process_request lo provee: {quien}')
    print()
    for C in (socketserver.TCPServer, Bien, Mal):
        C.allow_reuse_address = True
        t = medir_dos_clientes(C)
        print(f'  {C.__name__:<10} 2 clientes de {LENTO}s cada uno → {t:.2f}s')
    print('  → Mal no lanza ningún error: arranca, atiende, responde... pero en serie.')
    print('    Es un bug silencioso: solo se nota bajo carga.\n')


# ─────────────────────────────────────────────
# Parte C: forking y memoria
# ─────────────────────────────────────────────

class HandlerContador(socketserver.BaseRequestHandler):
    def handle(self):
        self.server.contador += 1                       # int común
        self.request.sendall(str(self.server.contador).encode())


class ServidorForkInt(socketserver.ForkingTCPServer):
    allow_reuse_address = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.contador = 0


class HandlerValue(socketserver.BaseRequestHandler):
    def handle(self):
        with self.server.contador.get_lock():           # += no es atómico
            self.server.contador.value += 1
            valor = self.server.contador.value
        self.request.sendall(str(valor).encode())


class ServidorForkValue(socketserver.ForkingTCPServer):
    allow_reuse_address = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # En el __init__ del SERVIDOR: se crea una sola vez, en el padre, ANTES
        # de cada fork, así todos los hijos heredan la MISMA memoria compartida.
        # Si se creara en el handler, cada hijo tendría su propio Value.
        self.contador = multiprocessing.Value('i', 0)


def contar(clase_servidor, handler, n=5):
    srv = clase_servidor(('localhost', 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    respuestas = []
    for _ in range(n):
        with socket.create_connection(srv.server_address) as c:
            respuestas.append(c.recv(16).decode())
    srv.shutdown()
    srv.server_close()
    return respuestas


def parte_c():
    print('=== Parte C: forking y estado compartido ===')
    if not hasattr(os, 'fork'):
        print('  (os.fork no existe en este sistema)')
        return
    print(f'  int en el servidor    : {contar(ServidorForkInt, HandlerContador)}')
    print('  → cada hijo incrementa SU copia del servidor (fork copia la memoria) y')
    print('    muere; el padre nunca ve el cambio. Siempre responde 1.')
    print(f'  multiprocessing.Value : {contar(ServidorForkValue, HandlerValue)}\n')


# ─────────────────────────────────────────────
# Parte D: daemon_threads
# ─────────────────────────────────────────────

SCRIPT_D = r'''
import socketserver, sys, time
class H(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.recv(10)          # cliente que nunca manda nada
class S(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = {daemon}
    block_on_close = False
srv = S(('localhost', {puerto}), H)
print('listo', flush=True)
try:
    srv.serve_forever()
except KeyboardInterrupt:
    srv.server_close()
    print('salgo del main', flush=True)
'''


def parte_d():
    print('=== Parte D: daemon_threads ===')
    import signal
    for daemon, puerto in ((False, 8171), (True, 8172)):
        p = subprocess.Popen([sys.executable, '-c',
                              SCRIPT_D.format(daemon=daemon, puerto=puerto)],
                             stdout=subprocess.PIPE, text=True)
        p.stdout.readline()                           # esperar 'listo'
        colgado = socket.create_connection(('localhost', puerto))
        time.sleep(0.2)
        p.send_signal(signal.SIGINT)                  # como Ctrl+C
        try:
            p.wait(timeout=2)
            estado = f'terminó (código {p.returncode})'
        except subprocess.TimeoutExpired:
            estado = 'SIGUE VIVO: el intérprete espera al thread no-daemon'
            p.kill()
            p.wait()
        colgado.close()
        print(f'  daemon_threads={daemon!s:<5} → {estado}')
    print('  → Sin daemon, al salir Python hace join() de los threads no-daemon: un')
    print('    cliente con nc abierto impide que el servidor termine.\n')


if __name__ == '__main__':
    modo = sys.argv[1] if len(sys.argv) > 1 else 'todo'
    partes = {'leer': [parte_a], 'orden': [parte_b], 'forking': [parte_c],
              'daemon': [parte_d], 'todo': [parte_a, parte_b, parte_c, parte_d]}
    if modo not in partes:
        print(__doc__)
        sys.exit(1)
    for f in partes[modo]:
        f()
