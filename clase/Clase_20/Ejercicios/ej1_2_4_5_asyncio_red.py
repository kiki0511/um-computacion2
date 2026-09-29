#!/usr/bin/env python3
"""
Ejercicios 1, 2, 4 y 5 de la clase 20.

Modos:
  lento    → 1.2: eco con demora de 1s. asyncio.sleep vs time.sleep, dos clientes
  leer     → 2.2: read / readline / readexactly / readuntil sobre 'hola\\nmundo\\n'
  drain    → 2.1: cliente que manda 100 MB sin leer; memoria del servidor con y sin drain
  locks    → 4:   contador sin lock (ok), transferencias con await en el medio (mal),
                  arreglado con asyncio.Lock
  timeouts → 5:   asyncio.timeout vs wait_for, cancelación de una corrutina que no
                  cede, y qué pasa si se traga el CancelledError

Uso:
  python3 ej1_2_4_5_asyncio_red.py [lento|leer|drain|locks|timeouts|todo]
"""
import asyncio
import sys
import threading
import time


# ─────────────────────────────────────────────
# 1.2 El servidor no se bloquea
# ─────────────────────────────────────────────

async def lento():
    print('=== 1.2: eco con demora de 1s, dos clientes a la vez ===')
    for nombre in ('await asyncio.sleep', 'time.sleep'):
        bloqueante = nombre == 'time.sleep'

        async def manejar(reader, writer):
            datos = await reader.readline()
            if bloqueante:
                time.sleep(1)                   # congela el loop entero
            else:
                await asyncio.sleep(1)          # cede el control
            writer.write(datos)
            await writer.drain()
            writer.close()

        srv = await asyncio.start_server(manejar, '127.0.0.1', 0)
        puerto = srv.sockets[0].getsockname()[1]

        async def cliente(i):
            r, w = await asyncio.open_connection('127.0.0.1', puerto)
            w.write(f'hola {i}\n'.encode())
            await w.drain()
            await r.readline()
            w.close()

        t0 = time.perf_counter()
        await asyncio.gather(cliente(1), cliente(2))
        print(f'  {nombre:<20}: dos clientes en {time.perf_counter() - t0:.2f}s')
        srv.close()
        await srv.wait_closed()
    print()


# ─────────────────────────────────────────────
# 2.2 Las formas de leer
# ─────────────────────────────────────────────

async def leer():
    print("=== 2.2: el cliente manda b'hola\\nmundo\\n' y cierra ===")
    resultados = {}
    listo = asyncio.Event()
    metodo_actual = {}

    async def manejar(reader, writer):
        m = metodo_actual['m']
        try:
            resultados[m] = await metodo_actual['f'](reader)
        except Exception as e:
            resultados[m] = f'{type(e).__name__}: {e}'
        writer.close()
        listo.set()

    srv = await asyncio.start_server(manejar, '127.0.0.1', 0)
    puerto = srv.sockets[0].getsockname()[1]
    pruebas = [
        ('read(100)', lambda r: r.read(100)),
        ('readline()', lambda r: r.readline()),
        ('readexactly(4)', lambda r: r.readexactly(4)),
        ("readuntil(b'\\n')", lambda r: r.readuntil(b'\n')),
        ('readexactly(100)', lambda r: r.readexactly(100)),
        ('read() tras EOF', lambda r: _leer_dos_veces(r)),
    ]
    for m, f in pruebas:
        metodo_actual.update(m=m, f=f)
        listo.clear()
        _, w = await asyncio.open_connection('127.0.0.1', puerto)
        w.write(b'hola\nmundo\n')
        await w.drain()
        w.close()                       # cierra: el servidor ve EOF después de los datos
        await listo.wait()
        print(f'  {m:<18} → {resultados[m]!r}')
    srv.close()
    await srv.wait_closed()
    print()


async def _leer_dos_veces(r):
    await r.read()                      # todo hasta EOF
    return await r.read(100)            # ya no queda nada: b''


# ─────────────────────────────────────────────
# 2.1 write y drain
# ─────────────────────────────────────────────

async def drain():
    print('=== 2.1: servidor eco, cliente que manda 100 MB y NUNCA lee ===')
    for usar_drain in (False, True):
        terminado = asyncio.Event()
        pico = {'buffer': 0}

        async def manejar(reader, writer):
            try:
                while datos := await reader.read(65536):
                    writer.write(datos)                    # eco: al buffer de salida
                    pico['buffer'] = max(pico['buffer'],
                                         writer.transport.get_write_buffer_size())
                    if usar_drain:
                        # si el buffer pasó el límite alto, espera a que se vacíe;
                        # mientras espera NO lee más → el cliente se frena (backpressure)
                        await asyncio.wait_for(writer.drain(), 3)
            except (asyncio.TimeoutError, ConnectionError):
                pass
            writer.transport.abort()
            terminado.set()

        srv = await asyncio.start_server(manejar, '127.0.0.1', 0)
        puerto = srv.sockets[0].getsockname()[1]
        mandar_100mb_sin_leer(puerto)
        try:
            await asyncio.wait_for(terminado.wait(), 30)
        except asyncio.TimeoutError:
            pass
        print(f'  drain={"SÍ" if usar_drain else "NO"}: pico del buffer de salida en el servidor '
              f'{pico["buffer"] / 1e6:6.1f} MB')
        srv.close()
    print('  → sin drain, todo lo que el cliente no lee se acumula en la memoria del servidor.')
    print()


def mandar_100mb_sin_leer(puerto):
    """Cliente en un thread con socket bloqueante: escribe hasta que no puede más."""
    import socket

    def cliente():
        s = socket.create_connection(('127.0.0.1', puerto))
        s.settimeout(3)
        bloque = b'x' * 1_000_000
        try:
            for _ in range(100):
                s.sendall(bloque)
        except (TimeoutError, OSError):
            pass                          # se llenó todo: el servidor dejó de leer
        s.close()
    threading.Thread(target=cliente, daemon=True).start()


# ─────────────────────────────────────────────
# 4 Locks, o su ausencia
# ─────────────────────────────────────────────

async def locks():
    print('=== 4.1: 1000 tareas hacen contador += 1 ===')
    estado = {'contador': 0}

    async def sumar():
        estado['contador'] += 1          # sin await: nadie puede interrumpir
    await asyncio.gather(*(sumar() for _ in range(1000)))
    print(f'  contador = {estado["contador"]}')

    print('=== 4.2: 100 transferencias de $1 con un await en el medio ===')
    for usar_lock in (False, True):
        cuentas = {'origen': 1000, 'destino': 0}
        lock = asyncio.Lock()

        async def transferir(monto):
            async def cuerpo():
                saldo = cuentas['origen']
                await asyncio.sleep(0)       # punto de suspensión: otra tarea lee el MISMO saldo
                cuentas['origen'] = saldo - monto
                cuentas['destino'] += monto
            if usar_lock:
                async with lock:             # async with: esperar el lock también cede
                    await cuerpo()
            else:
                await cuerpo()

        await asyncio.gather(*(transferir(1) for _ in range(100)))
        total = cuentas['origen'] + cuentas['destino']
        print(f'  {"con asyncio.Lock" if usar_lock else "sin lock        "}: '
              f'origen={cuentas["origen"]:4}  destino={cuentas["destino"]:3}  '
              f'total={total} {"✓" if total == 1000 else "✗ inconsistente: se perdieron débitos"}')
    print()


# ─────────────────────────────────────────────
# 5 Timeouts y cancelación
# ─────────────────────────────────────────────

async def timeouts():
    print('=== 5.1: timeout ===')
    estado = {}

    async def operacion_lenta():
        try:
            await asyncio.sleep(5)
        except asyncio.CancelledError:
            estado['cancelada'] = True
            raise

    try:
        async with asyncio.timeout(0.5):          # Python 3.11+
            await operacion_lenta()
    except TimeoutError as e:
        print(f'  asyncio.timeout → {type(e).__name__}; la operación fue cancelada: '
              f'{estado.get("cancelada", False)}')
    estado.clear()
    try:
        await asyncio.wait_for(operacion_lenta(), 0.5)
    except asyncio.TimeoutError as e:
        print(f'  wait_for        → {type(e).__name__}; cancelada: {estado.get("cancelada", False)}')

    print('=== 5.2: cancelar una corrutina que calcula sin await ===')

    async def calcular(segundos):
        fin = time.perf_counter() + segundos
        while time.perf_counter() < fin:
            pass                                   # nunca cede
        return 'terminé igual'

    t0 = time.perf_counter()
    tarea = asyncio.create_task(calcular(2))
    await asyncio.sleep(0)                         # la tarea arranca y no suelta hasta terminar
    tarea.cancel()
    try:
        r = await tarea
        print(f'  cancel() no la frenó: {r!r} a los {time.perf_counter() - t0:.1f}s')
    except asyncio.CancelledError:
        print(f'  cancelada a los {time.perf_counter() - t0:.1f}s')

    print('=== 5.2.7: tragarse el CancelledError ===')

    async def testaruda():
        try:
            await asyncio.sleep(5)
        except asyncio.CancelledError:
            pass                                   # MAL: no se relanza
        return 'sigo viva'

    tarea = asyncio.create_task(testaruda())
    await asyncio.sleep(0.1)
    tarea.cancel()
    r = await tarea
    print(f'  resultado: {r!r}  cancelled()={tarea.cancelled()}  ← quien canceló cree que no pasó nada')
    print()


if __name__ == '__main__':
    modo = sys.argv[1] if len(sys.argv) > 1 else 'todo'
    modos = {'lento': [lento], 'leer': [leer], 'drain': [drain], 'locks': [locks],
             'timeouts': [timeouts], 'todo': [lento, leer, locks, timeouts, drain]}
    if modo not in modos:
        print(__doc__)
        sys.exit(1)
    for m in modos[modo]:
        asyncio.run(m())
