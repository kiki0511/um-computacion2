#!/usr/bin/env python3
"""
Ejercicio 4: comandos.py extendido.

Agrega:
  NICK <nombre>       apodo por cliente (vive en el SERVIDOR, indexado por dirección)
  BROADCAST <texto>   mensaje a todos los conectados (se guardan los wfile)
  timeout = 30        desconecta a quien no manda nada en 30 s
  Manejo de clientes que se desconectan mientras otro les escribe.

Comandos: TIME, ECHO, QUIEN, CONTADOR, NICK, BROADCAST, AYUDA, QUIT

Uso:
  python3 ej4_comandos_extendido.py [puerto] [timeout]
  nc localhost 8080
"""
import socket
import socketserver
import sys
import threading
import time

TIMEOUT_INACTIVIDAD = 30


class Handler(socketserver.StreamRequestHandler):
    # StreamRequestHandler aplica este timeout al socket en setup():
    # si readline() no recibe nada en ese tiempo, lanza TimeoutError.
    timeout = TIMEOUT_INACTIVIDAD

    def setup(self):
        super().setup()                          # crea rfile/wfile y aplica timeout
        with self.server.lock:
            self.server.conexiones += 1
            self.server.clientes[self.client_address] = self.wfile
            self.server.nicks[self.client_address] = f'{self.client_address[0]}:{self.client_address[1]}'

    def finish(self):
        with self.server.lock:
            self.server.clientes.pop(self.client_address, None)
            self.server.nicks.pop(self.client_address, None)
        try:
            super().finish()                     # flush de wfile: puede fallar si el cliente ya se fue
        except OSError:
            pass

    def responder(self, texto):
        self.wfile.write((texto + '\n').encode())

    def nombre(self):
        with self.server.lock:
            return self.server.nicks.get(self.client_address, '?')

    def handle(self):
        self.responder('Servidor de comandos. Escribí AYUDA.')
        try:
            for linea in self.rfile:
                if not self.procesar(linea):
                    return
        except TimeoutError:
            self.responder(f'Desconectado por inactividad ({self.timeout}s)')
        except ConnectionError:
            pass                                 # el cliente se fue de golpe

    def procesar(self, linea):
        """Devuelve False si hay que cerrar la conexión."""
        partes = linea.decode('utf-8', 'replace').strip().split(maxsplit=1)
        if not partes:
            return True
        cmd, resto = partes[0].upper(), (partes[1] if len(partes) > 1 else '')

        if cmd == 'TIME':
            self.responder(time.strftime('%Y-%m-%d %H:%M:%S'))
        elif cmd == 'ECHO':
            self.responder(resto)
        elif cmd == 'QUIEN':
            with self.server.lock:
                nombres = sorted(self.server.nicks.values())
            self.responder(f'{len(nombres)} conectados: ' + ', '.join(nombres))
        elif cmd == 'CONTADOR':
            with self.server.lock:
                n = self.server.conexiones
            self.responder(f'Conexiones totales desde el arranque: {n}')
        elif cmd == 'NICK':
            if not resto:
                self.responder('Uso: NICK <nombre>')
            else:
                with self.server.lock:
                    self.server.nicks[self.client_address] = resto
                self.responder(f'Ahora sos {resto}')
        elif cmd == 'BROADCAST':
            enviados = self.server.difundir(f'[{self.nombre()}] {resto}',
                                            excepto=self.client_address)
            self.responder(f'Enviado a {enviados} clientes')
        elif cmd == 'AYUDA':
            self.responder('TIME | ECHO <t> | QUIEN | CONTADOR | NICK <n> | BROADCAST <t> | QUIT')
        elif cmd == 'QUIT':
            self.responder('Chau')
            return False
        else:
            self.responder(f'Comando desconocido: {cmd}')
        return True


class Servidor(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conexiones = 0
        self.clientes = {}          # direccion -> wfile  (para BROADCAST)
        self.nicks = {}             # direccion -> apodo  (compartido: QUIEN lo lee)
        self.lock = threading.Lock()

    def difundir(self, texto, excepto=None):
        """Escribe a todos. Si un cliente se fue, se lo saca y se sigue."""
        datos = (texto + '\n').encode()
        with self.lock:
            destinos = [(d, w) for d, w in self.clientes.items() if d != excepto]
        enviados = 0
        for direccion, wfile in destinos:        # fuera del lock: escribir puede bloquear
            try:
                wfile.write(datos)
                enviados += 1
            except (OSError, ValueError):        # socket roto o wfile ya cerrado
                with self.lock:
                    self.clientes.pop(direccion, None)
        return enviados


def demo():
    """Prueba automática: dos clientes, NICK, BROADCAST, QUIEN y timeout."""
    Handler.timeout = 1
    srv = Servidor(('localhost', 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    def conectar():
        s = socket.create_connection(srv.server_address)
        f = s.makefile('rwb', buffering=0)
        f.readline()                              # bienvenida
        return s, f

    def cmd(f, texto):
        f.write((texto + '\n').encode())
        return f.readline().decode().strip()

    a, fa = conectar()
    b, fb = conectar()
    print('A: NICK ana          →', cmd(fa, 'NICK ana'))
    print('B: NICK beto         →', cmd(fb, 'NICK beto'))
    print('A: QUIEN             →', cmd(fa, 'QUIEN'))
    print('A: BROADCAST hola    →', cmd(fa, 'BROADCAST hola a todos'))
    print('B recibe             →', fb.readline().decode().strip())
    fb.close(); b.close()                         # B se va sin QUIT (makefile retiene el fd)
    time.sleep(0.2)
    print('A: BROADCAST (B cerró)→', cmd(fa, 'BROADCAST alguien?'))
    time.sleep(1.3)
    print('A tras 1s sin hablar →', fa.readline().decode().strip())
    fa.close(); a.close()
    srv.shutdown()
    srv.server_close()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'demo':
        demo()
        sys.exit(0)
    puerto = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    if len(sys.argv) > 2:
        Handler.timeout = float(sys.argv[2])
    with Servidor(('0.0.0.0', puerto), Handler) as srv:
        print(f'Escuchando en 0.0.0.0:{puerto} (timeout {Handler.timeout}s)')
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            print('\nServidor detenido')
