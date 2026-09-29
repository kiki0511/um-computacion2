#!/usr/bin/env python3
"""
Ejercicio 3 (OBLIGATORIO): Concurrencia de clientes.

Descargas HTTP con httpx.AsyncClient:
  B → secuencial vs gather (10 descargas); requests adentro de la corrutina
  C → Semaphore(3); 200 URLs sin acotar con un ulimit bajo
  D → una URL inválida: gather normal vs return_exceptions=True

Por defecto usa un servidor HTTP LOCAL que tarda DEMORA segundos por pedido
(así los números no dependen de tu conexión). Con --real usa https://example.com.

Uso:
  pip install httpx requests
  python3 ej3_descargas.py            # servidor local
  python3 ej3_descargas.py --real     # Internet de verdad
"""
import asyncio
import http.server
import multiprocessing
import resource
import socket
import sys
import time

import httpx

DEMORA = 0.3                    # segundos que tarda el servidor local por pedido
N = 10


# ─────────────────────────────────────────────
# Servidor local de prueba (threads: atiende en paralelo)
# ─────────────────────────────────────────────

class Lento(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def do_GET(self):
        time.sleep(DEMORA)
        cuerpo = b'x' * 1024
        self.send_response(200)
        self.send_header('Content-Length', str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def log_message(self, *a):
        pass


class ServidorSilencioso(http.server.ThreadingHTTPServer):
    request_queue_size = 512
    daemon_threads = True

    def handle_error(self, request, client_address):
        pass            # clientes que cortan a mitad (Parte C): no ensuciar la salida


def _servir(puerto):
    with ServidorSilencioso(('127.0.0.1', puerto), Lento) as srv:
        srv.serve_forever()


def servidor_local():
    """En OTRO proceso: así bajar el ulimit del cliente (Parte C) no lo afecta."""
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        puerto = s.getsockname()[1]
    multiprocessing.Process(target=_servir, args=(puerto,), daemon=True).start()
    for _ in range(50):
        try:
            socket.create_connection(('127.0.0.1', puerto), timeout=1).close()
            break
        except OSError:
            time.sleep(0.1)
    return f'http://127.0.0.1:{puerto}/'


# ─────────────────────────────────────────────
# Descargas
# ─────────────────────────────────────────────

async def bajar(cliente, url):
    r = await cliente.get(url)
    return url, r.status_code, len(r.content)


async def bajar_con_requests(url):
    import requests
    r = requests.get(url, timeout=10)          # BLOQUEANTE dentro de una corrutina
    return url, r.status_code, len(r.content)


async def bajar_acotado(sem, cliente, url):
    async with sem:                            # como mucho N a la vez
        return await bajar(cliente, url)


async def secuencial(urls):
    async with httpx.AsyncClient(timeout=10) as c:
        return [await bajar(c, u) for u in urls]


async def concurrente(urls, **kw_gather):
    # UN cliente para todas: reutiliza conexiones (keep-alive, pool)
    async with httpx.AsyncClient(timeout=10) as c:
        return await asyncio.gather(*(bajar(c, u) for u in urls), **kw_gather)


async def con_semaforo(urls, limite):
    sem = asyncio.Semaphore(limite)
    async with httpx.AsyncClient(timeout=10) as c:
        return await asyncio.gather(*(bajar_acotado(sem, c, u) for u in urls))


async def con_requests(urls):
    return await asyncio.gather(*(bajar_con_requests(u) for u in urls))


def cronometrar(corutina):
    t0 = time.perf_counter()
    resultado = asyncio.run(corutina)
    return time.perf_counter() - t0, resultado


# ─────────────────────────────────────────────
# Partes
# ─────────────────────────────────────────────

def parte_b(url):
    print('=== Parte B: 10 descargas ===')
    urls = [url] * N
    t_sec, _ = cronometrar(secuencial(urls))
    t_con, res = cronometrar(concurrente(urls))
    t_req, _ = cronometrar(con_requests(urls))
    print(f'  secuencial              {t_sec:5.2f}s')
    print(f'  gather (AsyncClient)    {t_con:5.2f}s   → x{t_sec / t_con:.1f} más rápido')
    print(f'  gather con requests     {t_req:5.2f}s   ← requests bloquea el loop: vuelve a ser secuencial')
    print(f'  ejemplo de resultado: {res[0]}\n')


def parte_c(url):
    print('=== Parte C: acotar ===')
    urls = [url] * N
    t, _ = cronometrar(con_semaforo(urls, 3))
    print(f'  10 descargas con Semaphore(3): {t:.2f}s  (≈ ceil(10/3) = 4 tandas)')

    print('\n  200 URLs sin semáforo, con límite de pool desactivado y ulimit -n 64:')
    blando, duro = resource.getrlimit(resource.RLIMIT_NOFILE)
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, duro))

    async def sin_limite():
        limites = httpx.Limits(max_connections=None, max_keepalive_connections=None)
        async with httpx.AsyncClient(timeout=10, limits=limites) as c:
            return await asyncio.gather(*(bajar(c, url) for _ in range(200)),
                                        return_exceptions=True)
    try:
        _, res = cronometrar(sin_limite())
        errores = [r for r in res if isinstance(r, Exception)]
        print(f'    ok: {len(res) - len(errores)}   errores: {len(errores)}')
        if errores:
            e = errores[0]
            causa = e
            while causa.__cause__ or causa.__context__:
                causa = causa.__cause__ or causa.__context__
            print(f'    primer error: {type(e).__name__}: {e}')
            print(f'    causa de fondo: {type(causa).__name__}: {causa}')
    except OSError as e:
        print(f'    {type(e).__name__}: {e}')
    finally:
        resource.setrlimit(resource.RLIMIT_NOFILE, (blando, duro))

    async def con_limite():
        sem = asyncio.Semaphore(20)
        async with httpx.AsyncClient(timeout=10) as c:
            return await asyncio.gather(*(bajar_acotado(sem, c, url) for _ in range(200)))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, duro))
    try:
        t, res = cronometrar(con_limite())
        print(f'  200 URLs con Semaphore(20) y el mismo ulimit: {len(res)} ok en {t:.2f}s')
    except Exception as e:
        print(f'  con Semaphore(20): {type(e).__name__}: {e}')
    finally:
        resource.setrlimit(resource.RLIMIT_NOFILE, (blando, duro))
    print('  (httpx por defecto ya acota a 100 conexiones: Limits(max_connections=100))\n')


def parte_d(url):
    print('=== Parte D: fallos ===')
    urls = [url] * 4 + ['http://no-existe.invalid/'] + [url] * 4
    try:
        asyncio.run(concurrente(urls))
    except Exception as e:
        print(f'  gather normal: explota con {type(e).__name__} y se pierden los 8 resultados buenos')
    res = asyncio.run(concurrente(urls, return_exceptions=True))
    ok = [r for r in res if not isinstance(r, Exception)]
    malos = [r for r in res if isinstance(r, Exception)]
    print(f'  return_exceptions=True: {len(ok)} ok, {len(malos)} excepción devuelta como valor '
          f'({type(malos[0]).__name__})\n')


if __name__ == '__main__':
    real = '--real' in sys.argv
    url = 'https://example.com/' if real else servidor_local()
    print(f'URL: {url}' + ('' if real else f'  (servidor local, {DEMORA}s por pedido)') + '\n')
    parte_b(url)
    parte_c(url)
    parte_d(url)
