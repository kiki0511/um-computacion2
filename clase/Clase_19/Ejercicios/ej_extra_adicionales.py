#!/usr/bin/env python3
"""
Ejercicios adicionales - Clase 19.

Modos:
  cliente    → cliente HTTP a mano (socket): separa estado, headers y cuerpo.
               Soporta Content-Length, Transfer-Encoding: chunked, y si no hay
               ninguno de los dos lee hasta que el servidor cierra.
  middleware → @app.middleware('http') que mide cada pedido y lo devuelve en
               el header X-Tiempo; muestra el orden de ejecución.

Uso:
  python3 ej_extra_adicionales.py cliente [url]      # default: servidor local de prueba
  python3 ej_extra_adicionales.py middleware
"""
import http.server
import socket
import sys
import threading
import time
from urllib.parse import urlsplit


# ─────────────────────────────────────────────
# Cliente HTTP a mano
# ─────────────────────────────────────────────

def leer_linea(archivo):
    return archivo.readline().decode('iso-8859-1').rstrip('\r\n')


def http_get(url):
    partes = urlsplit(url)
    host, puerto = partes.hostname, partes.port or 80
    ruta = partes.path or '/'
    if partes.query:
        ruta += '?' + partes.query

    with socket.create_connection((host, puerto), timeout=10) as s:
        pedido = (f'GET {ruta} HTTP/1.1\r\n'
                  f'Host: {host}\r\n'
                  'User-Agent: cliente-a-mano/1.0\r\n'
                  'Connection: close\r\n\r\n')
        s.sendall(pedido.encode())
        f = s.makefile('rb')

        # 1) línea de estado
        version, codigo, *motivo = leer_linea(f).split(' ', 2)
        # 2) headers hasta la línea vacía (framing por delimitador)
        headers = {}
        while (linea := leer_linea(f)):
            clave, _, valor = linea.partition(':')
            headers[clave.strip().lower()] = valor.strip()
        # 3) cuerpo: tres formas de saber dónde termina
        if headers.get('transfer-encoding', '').lower() == 'chunked':
            cuerpo = b''
            while True:
                tam = int(leer_linea(f).split(';')[0], 16)   # tamaño en hexa
                if tam == 0:
                    break
                cuerpo += f.read(tam)
                f.readline()                                  # \r\n tras cada chunk
            forma = 'chunked'
        elif 'content-length' in headers:
            cuerpo = f.read(int(headers['content-length']))   # framing por longitud
            forma = 'Content-Length'
        else:
            cuerpo = f.read()                                 # hasta que cierre
            forma = 'hasta el cierre de la conexión'
    return int(codigo), ' '.join(motivo), headers, cuerpo, forma


class SinLongitud(http.server.BaseHTTPRequestHandler):
    """Responde SIN Content-Length (HTTP/1.0): el cliente lee hasta el cierre."""
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'cuerpo sin Content-Length\n')

    def log_message(self, *a):
        pass


class ConLongitud(SinLongitud):
    def do_GET(self):
        cuerpo = b'cuerpo con Content-Length\n'
        self.send_response(200)
        self.send_header('Content-Length', str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)


def demo_cliente(url=None):
    urls = [url] if url else []
    servidores = []
    if not url:
        for h in (ConLongitud, SinLongitud):
            srv = http.server.ThreadingHTTPServer(('localhost', 0), h)
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            servidores.append(srv)
            urls.append(f'http://localhost:{srv.server_address[1]}/prueba')
    for u in urls:
        codigo, motivo, headers, cuerpo, forma = http_get(u)
        print(f'GET {u}')
        print(f'  estado : {codigo} {motivo}')
        print(f'  headers: {len(headers)} ({", ".join(list(headers)[:4])}...)')
        print(f'  cuerpo : {len(cuerpo)} bytes, delimitado por {forma}')
        print(f'           {cuerpo[:60]!r}')
    for srv in servidores:
        srv.shutdown()


# ─────────────────────────────────────────────
# Middleware
# ─────────────────────────────────────────────

def demo_middleware():
    import asyncio
    from fastapi import FastAPI, Request
    from fastapi.testclient import TestClient

    app = FastAPI()
    orden = []

    @app.middleware('http')
    async def medir_tiempo(request: Request, call_next):
        orden.append('middleware: antes')
        t0 = time.perf_counter()
        respuesta = await call_next(request)      # acá corre el endpoint
        ms = (time.perf_counter() - t0) * 1000
        respuesta.headers['X-Tiempo'] = f'{ms:.1f}ms'
        orden.append('middleware: después')
        return respuesta

    @app.get('/lento')
    async def lento():
        orden.append('endpoint')
        await asyncio.sleep(0.2)
        return {'ok': True}

    r = TestClient(app).get('/lento')
    print(f'X-Tiempo: {r.headers["x-tiempo"]}')
    print(f'Orden   : {" → ".join(orden)}')
    print('→ El middleware envuelve al endpoint: lo de antes de call_next corre antes,')
    print('  y lo de después cuando la respuesta ya existe (se le pueden agregar headers).')


if __name__ == '__main__':
    args = sys.argv[1:]
    modo = args[0] if args else ''
    if modo == 'cliente':
        demo_cliente(args[1] if len(args) > 1 else None)
    elif modo == 'middleware':
        demo_middleware()
    else:
        print(__doc__)
        sys.exit(1)
