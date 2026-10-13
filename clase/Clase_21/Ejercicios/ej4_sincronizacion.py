#!/usr/bin/env python3
"""
Ejercicio 4: Sincronización async.

  4.1 lock       → contador sin await (no necesita lock) contra transferir
                   con un await en el medio (sí necesita), 100 concurrentes
  4.2 semaforo   → 20 descargas con concurrencia máxima 5: Semaphore contra
                   Queue + 5 workers. Un servidor HTTP local cuenta cuántos
                   pedidos tiene a la vez, así se verifica el límite de verdad
  4.3 event      → workers que esperan una inicialización; set() antes del
                   wait(); clear() para pausar y reanudar

Uso:
  pip install httpx
  python3 ej4_sincronizacion.py              # todo
  python3 ej4_sincronizacion.py semaforo     # una sección (lock, semaforo, event)
"""
import asyncio
import http.server
import sys
import threading
import time

import httpx


# ─────────────────────────────────────────────
# 4.1 Cuándo hace falta un Lock
# ─────────────────────────────────────────────

contador = 0
cuentas = {}


async def incrementar():
    global contador
    contador += 1                      # leer y escribir SIN await en el medio


async def log(monto):
    await asyncio.sleep(0)             # cualquier await: el loop puede cambiar de tarea


async def transferir_sin_lock(a, b, monto):
    saldo = cuentas[a]                 # 1. lee
    await log(monto)                   # 2. cede el control: otras leen el MISMO saldo
    cuentas[a] = saldo - monto         # 3. escribe un valor viejo -> se pisan
    cuentas[b] += monto


async def transferir_con_lock(lock, a, b, monto):
    async with lock:                   # async with: adquirir puede suspender
        saldo = cuentas[a]
        await log(monto)
        cuentas[a] = saldo - monto
        cuentas[b] += monto


async def seccion_lock():
    global contador
    print('=== 4.1 Lock ===\n')

    contador = 0
    await asyncio.gather(*(incrementar() for _ in range(100_000)))
    print(f'  incrementar() x 100.000 sin lock: contador = {contador:,}  (correcto)')

    for usar_lock in (False, True):
        cuentas.update({'a': 1000, 'b': 0})
        lock = asyncio.Lock()
        if usar_lock:
            corrs = (transferir_con_lock(lock, 'a', 'b', 1) for _ in range(100))
        else:
            corrs = (transferir_sin_lock('a', 'b', 1) for _ in range(100))
        await asyncio.gather(*corrs)
        total = cuentas['a'] + cuentas['b']
        nombre = 'con asyncio.Lock' if usar_lock else 'sin lock        '
        print(f'  100 transferencias de $1 {nombre}: a = {cuentas["a"]}, '
              f'b = {cuentas["b"]}, total = {total}  '
              f'{"(correcto)" if cuentas["a"] == 900 else "(apareció plata: se pisaron las escrituras de a)"}')
    print()


# ─────────────────────────────────────────────
# 4.2 Semáforo contra cola
# ─────────────────────────────────────────────

DEMORA = 0.2
LIMITE = 5
N_URLS = 20


class Contador:
    """Cuenta cuántos pedidos atiende el servidor A LA VEZ."""
    def __init__(self):
        self.lock = threading.Lock()   # el servidor usa threads de verdad
        self.activos = 0
        self.pico = 0

    def entrar(self):
        with self.lock:
            self.activos += 1
            self.pico = max(self.pico, self.activos)

    def salir(self):
        with self.lock:
            self.activos -= 1


cuenta_servidor = Contador()


class Lento(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def do_GET(self):
        cuenta_servidor.entrar()
        try:
            time.sleep(DEMORA)
            cuerpo = b'ok'
            self.send_response(200)
            self.send_header('Content-Length', str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)
        finally:
            cuenta_servidor.salir()

    def log_message(self, *a):
        pass


def levantar_servidor():
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Lento)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f'http://127.0.0.1:{srv.server_address[1]}'


async def con_semaforo(cliente, urls):
    sem = asyncio.Semaphore(LIMITE)

    async def una(url):
        async with sem:                # a lo sumo LIMITE adentro
            r = await cliente.get(url)
            return r.status_code

    # Se crean 20 tareas de golpe; 15 quedan esperando en el semáforo
    return await asyncio.gather(*(una(u) for u in urls))


async def con_cola(cliente, urls):
    cola = asyncio.Queue()
    resultados = {}

    async def worker():
        while True:
            i, url = await cola.get()
            try:
                r = await cliente.get(url)
                resultados[i] = r.status_code
            finally:
                cola.task_done()

    for item in enumerate(urls):
        cola.put_nowait(item)
    # Solo existen LIMITE corrutinas; las URLs son datos esperando en la cola
    workers = [asyncio.create_task(worker()) for _ in range(LIMITE)]
    await cola.join()
    for w in workers:
        w.cancel()
    await asyncio.gather(*workers, return_exceptions=True)
    return [resultados[i] for i in range(len(urls))]


async def seccion_semaforo():
    print('=== 4.2 Semáforo contra cola ===\n')
    srv, base = levantar_servidor()
    urls = [f'{base}/{i}' for i in range(N_URLS)]
    limites = httpx.Limits(max_connections=50)
    print(f'  {N_URLS} URLs de {DEMORA}s, máximo {LIMITE} a la vez '
          f'(ideal: {N_URLS // LIMITE} rondas x {DEMORA}s = {N_URLS / LIMITE * DEMORA:.1f}s)')
    async with httpx.AsyncClient(limits=limites) as cliente:
        for nombre, funcion in (('Semaphore(5)', con_semaforo),
                                ('Queue + 5 workers', con_cola)):
            cuenta_servidor.pico = 0
            t0 = time.perf_counter()
            codigos = await funcion(cliente, urls)
            dur = time.perf_counter() - t0
            print(f'  {nombre:<18} {dur:.2f}s  | {codigos.count(200)}/{N_URLS} OK  '
                  f'| pico en el servidor: {cuenta_servidor.pico}')
    srv.shutdown()
    print()


# ─────────────────────────────────────────────
# 4.3 Event
# ─────────────────────────────────────────────

async def seccion_event():
    print('=== 4.3 Event ===\n')
    t0 = time.perf_counter()

    def ts():
        return f'[{time.perf_counter() - t0:4.2f}s]'

    # Pregunta 8: workers que esperan a que termine la inicialización
    listo = asyncio.Event()

    async def inicializar():
        print(f'  {ts()} cargando configuración...')
        await asyncio.sleep(0.3)
        print(f'  {ts()} listo -> set()')
        listo.set()

    async def worker(wid):
        await listo.wait()
        print(f'  {ts()} worker {wid} arranca')

    await asyncio.gather(*(worker(i) for i in range(3)), inicializar())

    # Pregunta 9: set() ANTES de que alguien haga wait()
    ev = asyncio.Event()
    ev.set()
    t = time.perf_counter()
    await ev.wait()
    print(f'\n  set() antes de wait(): wait() volvió en '
          f'{(time.perf_counter() - t) * 1000:.3f} ms (el Event es un ESTADO, no se pierde)')

    # Pregunta 10: clear() para pausar/reanudar
    print('\n  clear() como pausa: el worker procesa mientras el Event esté en True')
    habilitado = asyncio.Event()
    habilitado.set()
    procesados = []

    async def worker_pausable():
        for i in range(8):
            await habilitado.wait()      # si está en pausa, se queda acá
            await asyncio.sleep(0.05)
            procesados.append((i, round(time.perf_counter() - t0, 2)))

    t0 = time.perf_counter()
    w = asyncio.create_task(worker_pausable())
    await asyncio.sleep(0.12)
    habilitado.clear()
    al_pausar = len(procesados)
    print(f'  {ts()} clear() -> pausa  (procesados: {al_pausar})')
    await asyncio.sleep(0.4)
    print(f'  {ts()} set()   -> sigue  (procesados: {len(procesados)}; durante la '
          f'pausa terminó {len(procesados) - al_pausar}, la que ya estaba en curso)')
    habilitado.set()
    await w
    print(f'  {ts()} terminó con {len(procesados)}')
    print()


SECCIONES = {'lock': seccion_lock, 'semaforo': seccion_semaforo, 'event': seccion_event}


async def main(elegidas):
    for nombre in elegidas:
        await SECCIONES[nombre]()


if __name__ == '__main__':
    pedidas = [a for a in sys.argv[1:] if a in SECCIONES] or list(SECCIONES)
    asyncio.run(main(pedidas))
