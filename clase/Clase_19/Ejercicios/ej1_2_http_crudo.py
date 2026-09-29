#!/usr/bin/env python3
"""
Ejercicios 1 y 2: HTTP a mano y http.server.

Levanta un http.server propio (con do_DELETE agregado) y le habla por socket:
  - pedido correcto con \\r\\n
  - pedido con \\n a secas
  - HTTP/1.1 sin Host
  - DELETE (204) y PATCH, que no está implementado (501)
  - protocol_version = HTTP/1.1: dos pedidos por la misma conexión

Uso:
  python3 ej1_2_http_crudo.py
  python3 ej1_2_http_crudo.py servidor     # para probar con curl / nc
"""
import http.server
import json
import socket
import sys
import threading

recursos = {'42': {'id': 42, 'nombre': 'tarea de prueba'}}


class Handler(http.server.BaseHTTPRequestHandler):
    def _responder(self, codigo, datos=None):
        cuerpo = json.dumps(datos).encode() if datos is not None else b''
        self.send_response(codigo)
        if cuerpo:
            self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_GET(self):
        self._responder(200, {'metodo': 'GET', 'ruta': self.path})

    def do_POST(self):
        n = int(self.headers.get('Content-Length', 0))
        self._responder(201, {'metodo': 'POST', 'recibido': self.rfile.read(n).decode()})

    def do_DELETE(self):
        """204 No Content si existía; 404 si no."""
        clave = self.path.rstrip('/').rsplit('/', 1)[-1]
        if recursos.pop(clave, None) is None:
            self._responder(404, {'error': 'no existe'})
        else:
            self._responder(204)

    def log_message(self, *args):
        pass


class Handler11(Handler):
    protocol_version = 'HTTP/1.1'        # habilita keep-alive


def pedir(puerto, crudo: bytes, leer_hasta_cierre=True):
    with socket.create_connection(('localhost', puerto), timeout=2) as s:
        s.sendall(crudo)
        datos = b''
        try:
            while True:
                parte = s.recv(4096)
                if not parte:
                    break
                datos += parte
        except TimeoutError:
            pass
    return datos.decode(errors='replace')


def primera_linea(respuesta):
    return respuesta.split('\r\n', 1)[0] if respuesta else '(sin respuesta)'


def levantar(handler):
    srv = http.server.ThreadingHTTPServer(('localhost', 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def demo():
    print('Jerarquía:', ' → '.join(c.__name__ for c in http.server.BaseHTTPRequestHandler.__mro__[:4]))
    print('Mixin de ThreadingHTTPServer:', http.server.ThreadingHTTPServer.__bases__[0].__name__)
    srv, p = levantar(Handler)

    casos = [
        ('GET con \\r\\n', b'GET /hola HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n'),
        ('GET con \\n solo', b'GET /hola HTTP/1.1\nHost: x\nConnection: close\n\n'),
        ('HTTP/1.1 sin Host', b'GET /hola HTTP/1.1\r\nConnection: close\r\n\r\n'),
        ('DELETE /tareas/42', b'DELETE /tareas/42 HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n'),
        ('DELETE /tareas/42 otra vez', b'DELETE /tareas/42 HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n'),
        ('PATCH (no implementado)', b'PATCH /tareas/1 HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n'),
    ]
    print()
    for nombre, crudo in casos:
        print(f'  {nombre:<28} → {primera_linea(pedir(p, crudo))}')
    srv.shutdown()
    srv.server_close()

    print('\n=== keep-alive con protocol_version = HTTP/1.1 ===')
    srv, p = levantar(Handler11)
    dos = (b'GET /uno HTTP/1.1\r\nHost: x\r\n\r\n'
           b'GET /dos HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n')
    resp = pedir(p, dos)
    print(f'  respuestas en una sola conexión: {resp.count("HTTP/1.1 200")}')
    for bloque in resp.split('HTTP/1.1 ')[1:]:
        largo = [l for l in bloque.split('\r\n') if l.lower().startswith('content-length')][0]
        print(f'    {bloque.split(chr(13))[0]:<8} {largo}  ← así se sabe dónde termina cada una')
    srv.shutdown()
    srv.server_close()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'servidor':
        with http.server.ThreadingHTTPServer(('', 8080), Handler) as s:
            print('http://localhost:8080  (curl -X DELETE localhost:8080/tareas/42)')
            try:
                s.serve_forever()
            except KeyboardInterrupt:
                pass
    else:
        demo()
