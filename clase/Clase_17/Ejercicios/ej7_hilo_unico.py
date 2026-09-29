#!/usr/bin/env python3
"""
Ejercicio 7: El costo del hilo único.

Dos versiones del mismo servidor con selectors. Cada pedido hace ~0.5-1 s de
CPU (sha256 iterado):

  bloqueante → el cálculo corre EN el event loop: mientras calcula, nadie más
               es atendido (ni siquiera un cliente que solo quiere un PING)
  pool       → el cálculo se manda a un ProcessPoolExecutor; el loop sigue
               atendiendo. Cuando el worker termina, avisa al loop por un
               socketpair (self-pipe) que está registrado en el selector.

Uso:
  python3 ej7_hilo_unico.py            # corre las dos y compara
"""
import hashlib
import selectors
import socket
import threading
import time
from concurrent.futures import ProcessPoolExecutor

ITERACIONES = 1_500_000        # entre 0.5 y 1 s de CPU según la máquina


def trabajo_pesado(datos: bytes) -> str:
    h = datos
    for _ in range(ITERACIONES):
        h = hashlib.sha256(h).digest()
    return h.hex()[:16]


class Servidor:
    def __init__(self, usar_pool):
        self.sel = selectors.DefaultSelector()
        self.pool = ProcessPoolExecutor(max_workers=2) if usar_pool else None
        self.srv = socket.socket()
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srv.bind(('localhost', 0))
        self.srv.listen(16)
        self.srv.setblocking(False)
        self.sel.register(self.srv, selectors.EVENT_READ, self.aceptar)
        # self-pipe: los threads del pool escriben un byte acá para despertar al loop
        self.aviso_r, self.aviso_w = socket.socketpair()
        self.aviso_r.setblocking(False)
        self.sel.register(self.aviso_r, selectors.EVENT_READ, self.resultados_listos)
        self.terminados = []                   # (conn, resultado) listos para enviar
        self.lock = threading.Lock()           # terminados lo tocan dos hilos

    def aceptar(self, srv):
        conn, _ = srv.accept()
        conn.setblocking(False)
        self.sel.register(conn, selectors.EVENT_READ, self.atender)

    def atender(self, conn):
        datos = conn.recv(4096)
        if not datos:
            self.sel.unregister(conn)
            conn.close()
            return
        if datos.strip() == b'PING':
            conn.sendall(b'PONG\n')            # pedido trivial
            return
        if self.pool is None:
            conn.sendall(trabajo_pesado(datos).encode() + b'\n')   # bloquea el loop
        else:
            futuro = self.pool.submit(trabajo_pesado, datos)
            futuro.add_done_callback(lambda f, c=conn: self.avisar(c, f.result()))

    def avisar(self, conn, resultado):
        """Corre en un thread interno del pool: NO toca el socket del cliente."""
        with self.lock:
            self.terminados.append((conn, resultado))
        self.aviso_w.send(b'!')

    def resultados_listos(self, aviso):
        aviso.recv(1024)
        with self.lock:
            listos, self.terminados = self.terminados, []
        for conn, resultado in listos:
            conn.sendall(resultado.encode() + b'\n')

    def correr(self, parar):
        while not parar.is_set():
            for clave, _ in self.sel.select(timeout=0.1):
                clave.data(clave.fileobj)

    def cerrar(self):
        if self.pool:
            self.pool.shutdown()
        self.sel.close()
        self.srv.close()


def probar(usar_pool):
    srv = Servidor(usar_pool)
    parar = threading.Event()
    hilo = threading.Thread(target=srv.correr, args=(parar,))
    hilo.start()
    direccion = srv.srv.getsockname()

    pesado = socket.create_connection(direccion)
    liviano = socket.create_connection(direccion)
    t0 = time.perf_counter()
    pesado.sendall(b'calcular esto')
    time.sleep(0.05)                                    # el pesado llega primero
    liviano.sendall(b'PING')
    liviano.recv(100)
    t_ping = time.perf_counter() - t0
    pesado.recv(100)
    t_pesado = time.perf_counter() - t0

    for s in (pesado, liviano):
        s.close()
    parar.set()
    hilo.join()
    srv.cerrar()
    nombre = 'pool de procesos' if usar_pool else 'todo en el loop  '
    print(f'  {nombre}: PING respondido a los {t_ping:.2f}s, cálculo a los {t_pesado:.2f}s')


if __name__ == '__main__':
    print('Un cliente pide ~0.5-1s de CPU; otro manda PING 50 ms después.')
    probar(usar_pool=False)
    probar(usar_pool=True)
    print('→ Regla: en un event loop NADA puede tardar sin ceder. El trabajo de CPU')
    print('  se manda a otro proceso y el loop solo espera el aviso de que terminó.')
