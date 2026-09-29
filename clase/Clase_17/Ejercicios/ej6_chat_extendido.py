#!/usr/bin/env python3
"""
Ejercicio 6: chat.py extendido.

Agrega sobre el chat de la clase:
  /nick <nombre>   cambia el apodo
  /lista           quién está conectado
  Framing correcto: buffer de entrada por cliente. Solo se procesan
  líneas COMPLETAS (hasta '\\n'); lo que sobra queda para el próximo recv().

Uso:
  python3 ej6_chat_extendido.py [puerto]      # y varios: nc localhost 8080
  python3 ej6_chat_extendido.py --demo        # prueba automática (incluye framing roto)
"""
import selectors
import socket
import sys
import threading
import time


class Chat:
    def __init__(self, puerto):
        self.sel = selectors.DefaultSelector()
        self.apodos = {}          # socket -> apodo
        self.entrada = {}         # socket -> bytes recibidos sin '\n' todavía
        self.salida = {}          # socket -> bytes pendientes de enviar

        self.srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srv.bind(('localhost', puerto))
        self.srv.listen(128)
        self.srv.setblocking(False)
        self.sel.register(self.srv, selectors.EVENT_READ, self.aceptar)

    # ── salida ────────────────────────────────
    def encolar(self, conn, texto):
        self.salida[conn] = self.salida.get(conn, b'') + texto.encode()
        self.sel.modify(conn, selectors.EVENT_READ | selectors.EVENT_WRITE, self.manejar)

    def difundir(self, texto, excepto=None):
        # Sin lock: un solo hilo, nadie más toca los diccionarios mientras tanto.
        for conn in self.apodos:
            if conn is not excepto:
                self.encolar(conn, texto)

    # ── conexiones ────────────────────────────
    def aceptar(self, srv, _mascara):
        conn, direccion = srv.accept()
        conn.setblocking(False)
        self.apodos[conn] = f'{direccion[0]}:{direccion[1]}'
        self.entrada[conn] = b''
        self.sel.register(conn, selectors.EVENT_READ, self.manejar)
        self.encolar(conn, 'Bienvenido. Comandos: /nick <nombre>, /lista\n')
        self.difundir(f'* se conectó {self.apodos[conn]}\n', excepto=conn)

    def desconectar(self, conn):
        apodo = self.apodos.pop(conn, '?')
        self.entrada.pop(conn, None)
        self.salida.pop(conn, None)
        self.sel.unregister(conn)
        conn.close()
        self.difundir(f'* se fue {apodo}\n')

    # ── protocolo ─────────────────────────────
    def procesar_linea(self, conn, linea):
        texto = linea.decode('utf-8', 'replace').rstrip('\r')
        if not texto:
            return
        apodo = self.apodos[conn]
        if texto.startswith('/nick '):
            nuevo = texto[6:].strip()
            if not nuevo or nuevo in self.apodos.values():
                self.encolar(conn, '! apodo inválido o en uso\n')
                return
            self.apodos[conn] = nuevo
            self.difundir(f'* {apodo} ahora es {nuevo}\n')
        elif texto == '/lista':
            nombres = ', '.join(sorted(self.apodos.values()))
            self.encolar(conn, f'* {len(self.apodos)} conectados: {nombres}\n')
        else:
            self.difundir(f'<{apodo}> {texto}\n', excepto=conn)

    def manejar(self, conn, mascara):
        if mascara & selectors.EVENT_READ:
            try:
                datos = conn.recv(4096)
            except ConnectionResetError:
                datos = b''
            if not datos:
                self.desconectar(conn)
                return
            # FRAMING: acumular y cortar por '\n'. Un recv() puede traer media
            # línea, o varias juntas; nunca asumir que trae exactamente una.
            buf = self.entrada[conn] + datos
            *lineas, resto = buf.split(b'\n')
            self.entrada[conn] = resto
            for linea in lineas:
                self.procesar_linea(conn, linea)
                if conn not in self.apodos:
                    return

        if mascara & selectors.EVENT_WRITE and conn in self.apodos:
            buf = self.salida.get(conn, b'')
            try:
                n = conn.send(buf) if buf else 0
            except (BrokenPipeError, ConnectionResetError):
                self.desconectar(conn)
                return
            self.salida[conn] = buf[n:]
            if not self.salida[conn]:
                self.sel.modify(conn, selectors.EVENT_READ, self.manejar)

    def correr(self, parar=None):
        while parar is None or not parar.is_set():
            for clave, mascara in self.sel.select(timeout=0.2):
                clave.data(clave.fileobj, mascara)


def demo():
    chat = Chat(0)
    parar = threading.Event()
    hilo = threading.Thread(target=chat.correr, args=(parar,))
    hilo.start()
    direccion = chat.srv.getsockname()

    def cliente():
        s = socket.create_connection(direccion)
        s.settimeout(1)
        return s

    def leer_todo(s):
        time.sleep(0.2)
        datos = b''
        try:
            while True:
                parte = s.recv(4096)
                if not parte:
                    break
                datos += parte
        except TimeoutError:
            pass
        return datos.decode()

    a, b = cliente(), cliente()
    leer_todo(a)
    leer_todo(b)
    a.sendall(b'/nick ana\n')
    b.sendall(b'/nick beto\n')
    leer_todo(a)
    leer_todo(b)
    a.sendall(b'/lista\n')
    print('A /lista        →', leer_todo(a).strip())

    # Framing: una línea partida en tres send() y dos líneas en un solo send()
    for pedazo in (b'ho', b'la be', b'to\nsegunda\ntercera '):
        a.sendall(pedazo)
        time.sleep(0.1)
    a.sendall(b'linea\n')
    print('B recibe        →', leer_todo(b).strip().replace('\n', ' | '))
    a.close()
    b.close()
    time.sleep(0.2)
    parar.set()
    hilo.join()


if __name__ == '__main__':
    if '--demo' in sys.argv:
        demo()
        sys.exit(0)
    puerto = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    chat = Chat(puerto)
    print(f'Chat en localhost:{puerto} ({type(chat.sel).__name__}). Ctrl+C para cortar.')
    try:
        chat.correr()
    except KeyboardInterrupt:
        print('\nChat detenido')
