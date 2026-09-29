#!/usr/bin/env python3
"""
Ejercicio 4: servidor_select.py reescrito con selectors.

Qué desaparece respecto de la versión con select():
  - la lista `vigilados` (la mantiene el selector: register/unregister)
  - el diccionario socket -> dirección (va en el campo `data` del registro)
  - el if/elif "¿es el socket de escucha o un cliente?" (cada registro trae su callback)

Uso:
  python3 ej4_eco_selectors.py [puerto]                 # DefaultSelector
  python3 ej4_eco_selectors.py [puerto] --select        # fuerza SelectSelector
  python3 ej4_eco_selectors.py --demo                   # prueba automática
"""
import selectors
import socket
import sys
import threading
import time


def crear_servidor(puerto, forzar_select=False):
    sel = selectors.SelectSelector() if forzar_select else selectors.DefaultSelector()

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('localhost', puerto))
    srv.listen(128)
    srv.setblocking(False)

    def aceptar(s, _datos):
        conn, direccion = s.accept()
        conn.setblocking(False)
        # data = (callback, dirección): reemplaza al diccionario aparte
        sel.register(conn, selectors.EVENT_READ, (atender, direccion))
        print(f'+ {direccion}')

    def atender(conn, direccion):
        try:
            datos = conn.recv(4096)
        except ConnectionResetError:
            datos = b''
        if not datos:
            print(f'- {direccion}')
            sel.unregister(conn)          # SIEMPRE antes de close()
            conn.close()
            return
        conn.sendall(datos)               # eco simple (ver ej. 5 para send con buffer)

    sel.register(srv, selectors.EVENT_READ, (aceptar, None))
    return sel, srv


def bucle(sel, parar=None):
    while parar is None or not parar.is_set():
        for clave, _mascara in sel.select(timeout=0.2):
            callback, datos = clave.data
            callback(clave.fileobj, datos)


def demo():
    sel, srv = crear_servidor(0)
    print(f'Implementación elegida: {type(sel).__name__}')
    parar = threading.Event()
    hilo = threading.Thread(target=bucle, args=(sel, parar))
    hilo.start()
    clientes = [socket.create_connection(srv.getsockname()) for _ in range(3)]
    for i, c in enumerate(clientes):
        c.sendall(f'hola {i}'.encode())
        print(f'  cliente {i} recibió {c.recv(100)!r}')
    for c in clientes:
        c.close()
    time.sleep(0.3)
    parar.set()
    hilo.join()
    sel.close()
    srv.close()


if __name__ == '__main__':
    args = sys.argv[1:]
    if '--demo' in args:
        demo()
        sys.exit(0)
    forzar = '--select' in args
    numeros = [a for a in args if a.isdigit()]
    puerto = int(numeros[0]) if numeros else 8080
    sel, srv = crear_servidor(puerto, forzar)
    print(f'Eco en localhost:{puerto} con {type(sel).__name__}. Ctrl+C para cortar.')
    try:
        bucle(sel)
    except KeyboardInterrupt:
        print('\nChau.')
    finally:
        sel.close()
        srv.close()
