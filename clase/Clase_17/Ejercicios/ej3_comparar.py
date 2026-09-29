#!/usr/bin/env python3
"""
Ejercicio 3 (OBLIGATORIO): Comparar select, poll y epoll (o kqueue en macOS).

Extiende ../comparar.py:
  - ACTIVOS configurable (Parte B, punto 7)
  - calcula el factor de crecimiento entre la menor y la mayor cantidad
  - en macOS usa kqueue (el equivalente de epoll en BSD), que el original no mide

Uso:
  python3 ej3_comparar.py                        # 100..5000, 3 activos
  python3 ej3_comparar.py --activos mitad        # la mitad con datos
  python3 ej3_comparar.py 10 50 100              # Parte C
  python3 ej3_comparar.py --todo                 # A, B y C seguidas
"""
import resource
import select
import socket
import sys
import time

REPETICIONES = 200


def crear_pares(n):
    pares = [socket.socketpair() for _ in range(n)]
    return [a for a, _ in pares], [b for _, b in pares]


def cronometrar(f):
    t0 = time.perf_counter()
    for _ in range(REPETICIONES):
        f()
    return (time.perf_counter() - t0) / REPETICIONES * 1e6      # µs por llamada


def medir_select(lectores):
    try:
        return cronometrar(lambda: select.select(lectores, [], [], 0))
    except (ValueError, OSError):
        return None             # algún fd >= FD_SETSIZE (1024)


def medir_poll(lectores):
    if not hasattr(select, 'poll'):
        return None
    p = select.poll()
    for s in lectores:
        p.register(s, select.POLLIN)
    # poll() recibe TODA la lista en cada llamada y el kernel la recorre: O(n)
    return cronometrar(lambda: p.poll(0))


def medir_epoll(lectores):
    if hasattr(select, 'epoll'):
        ep = select.epoll()
        for s in lectores:
            ep.register(s, select.EPOLLIN)
        # el registro vive en el kernel; epoll_wait solo devuelve los listos
        t = cronometrar(lambda: ep.poll(0))
        ep.close()
        return t, 'epoll'
    if hasattr(select, 'kqueue'):
        kq = select.kqueue()
        eventos = [select.kevent(s.fileno(), select.KQ_FILTER_READ, select.KQ_EV_ADD)
                   for s in lectores]
        kq.control(eventos, 0)                  # registrar una sola vez
        t = cronometrar(lambda: kq.control(None, len(lectores), 0))
        kq.close()
        return t, 'kqueue'
    return None, '-'


def fmt(x):
    return '   falla' if x is None else f'{x:8.1f}'


def correr(cantidades, activos_modo='3'):
    blando, duro = resource.getrlimit(resource.RLIMIT_NOFILE)
    necesarios = 2 * max(cantidades) + 100
    if blando < necesarios:
        resource.setrlimit(resource.RLIMIT_NOFILE, (min(necesarios, duro), duro))

    print(f'\nActivos: {activos_modo}. µs por llamada (promedio de {REPETICIONES}).')
    print(f'{"conexiones":>10} {"activos":>8} {"select":>9} {"poll":>9} {"epoll/kq":>9}')
    resultados = []
    nombre = '-'
    for n in cantidades:
        lectores, escritores = crear_pares(n)
        activos = n // 2 if activos_modo == 'mitad' else min(int(activos_modo), n)
        for w in escritores[:activos]:
            w.send(b'x')
        s, p = medir_select(lectores), medir_poll(lectores)
        e, nombre = medir_epoll(lectores)
        resultados.append((n, s, p, e))
        print(f'{n:>10} {activos:>8} {fmt(s)} {fmt(p)} {fmt(e)}')
        for x in lectores + escritores:
            x.close()

    (n0, _, p0, e0), (n1, _, p1, e1) = resultados[0], resultados[-1]
    print(f'  conexiones x{n1 / n0:.0f}:', end='')
    if p0 and p1:
        print(f'  poll x{p1 / p0:.1f}', end='')
    if e0 and e1:
        print(f'  {nombre} x{e1 / e0:.1f}', end='')
    print()
    return resultados


if __name__ == '__main__':
    args = sys.argv[1:]
    if '--todo' in args:
        print('=== Parte A: 3 activos ===')
        correr([100, 500, 1000, 2000, 5000])
        print('\n=== Parte B.7: la mitad activos ===')
        correr([100, 500, 1000, 2000, 5000], 'mitad')
        print('\n=== Parte C: pocas conexiones ===')
        correr([10, 50, 100])
        sys.exit(0)
    modo = '3'
    if '--activos' in args:
        i = args.index('--activos')
        modo = args[i + 1]
        del args[i:i + 2]
    cantidades = [int(a) for a in args] or [100, 500, 1000, 2000, 5000]
    correr(cantidades, modo)
