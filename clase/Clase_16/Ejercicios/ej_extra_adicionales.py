#!/usr/bin/env python3
"""
Ejercicios adicionales - Clase 16 (socketserver).

Modos:
  archivos   → servidor de archivos: GET <nombre> con framing por longitud
               (clase 13). Un archivo inexistente no tira el servidor.
  selector   → muestra qué selector usa serve_forever() por dentro

Uso:
  python3 ej_extra_adicionales.py archivos [directorio]   # demo automática
  python3 ej_extra_adicionales.py selector
"""
import inspect
import os
import socket
import socketserver
import struct
import sys
import threading


# ─────────────────────────────────────────────
# Servidor de archivos
# ─────────────────────────────────────────────
# Protocolo:
#   cliente → "GET <nombre>\n"
#   servidor → [1 byte estado][4 bytes longitud '!I'][cuerpo]
#              estado 0 = OK (cuerpo = contenido), 1 = error (cuerpo = mensaje)

class HandlerArchivos(socketserver.StreamRequestHandler):
    def enviar(self, estado, cuerpo):
        self.wfile.write(struct.pack('!BI', estado, len(cuerpo)) + cuerpo)

    def handle(self):
        for linea in self.rfile:
            partes = linea.decode('utf-8', 'replace').split(maxsplit=1)
            if len(partes) != 2 or partes[0].upper() != 'GET':
                self.enviar(1, b'Uso: GET <nombre>')
                continue
            nombre = os.path.basename(partes[1].strip())      # evita ../../etc/passwd
            ruta = os.path.join(self.server.raiz, nombre)
            try:
                with open(ruta, 'rb') as f:
                    self.enviar(0, f.read())
            except OSError as e:
                self.enviar(1, f'{nombre}: {e.strerror}'.encode())


class ServidorArchivos(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, direccion, raiz):
        super().__init__(direccion, HandlerArchivos)
        self.raiz = os.path.abspath(raiz)


def recibir_exacto(sock, n):
    datos = b''
    while len(datos) < n:
        parte = sock.recv(n - len(datos))
        if not parte:
            raise ConnectionError('el servidor cerró a mitad del mensaje')
        datos += parte
    return datos


def pedir_archivo(sock, nombre):
    sock.sendall(f'GET {nombre}\n'.encode())
    estado, largo = struct.unpack('!BI', recibir_exacto(sock, 5))
    return estado, recibir_exacto(sock, largo)


def demo_archivos(raiz):
    srv = ServidorArchivos(('localhost', 0), raiz)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(f'Sirviendo {srv.raiz}')
    with socket.create_connection(srv.server_address) as s:
        for nombre in (os.path.basename(__file__), 'no_existe.txt', '../../etc/passwd'):
            estado, cuerpo = pedir_archivo(s, nombre)
            if estado == 0:
                print(f'  GET {nombre:<28} OK, {len(cuerpo)} bytes')
            else:
                print(f'  GET {nombre:<28} ERROR: {cuerpo.decode()}')
    srv.shutdown()
    srv.server_close()


# ─────────────────────────────────────────────
# El selector de serve_forever
# ─────────────────────────────────────────────

def ver_selector():
    fuente = inspect.getsource(socketserver)
    for linea in fuente.splitlines():
        if '_ServerSelector' in linea and '=' in linea and 'class' not in linea:
            print(linea.strip())
    fuente = inspect.getsource(socketserver.BaseServer.serve_forever)
    for linea in fuente.splitlines():
        if 'selector' in linea:
            print('  ', linea.strip())
    print('\n→ serve_forever() usa un selector (poll o select) con timeout = poll_interval')
    print('  para vigilar el socket de escucha y chequear el pedido de shutdown.')
    print('  Es el mismo mecanismo de la clase 17, pero con un solo fd vigilado.')


if __name__ == '__main__':
    args = sys.argv[1:]
    modo = args[0] if args else ''
    if modo == 'archivos':
        demo_archivos(args[1] if len(args) > 1 else os.path.dirname(os.path.abspath(__file__)))
    elif modo == 'selector':
        ver_selector()
    else:
        print(__doc__)
        sys.exit(1)
