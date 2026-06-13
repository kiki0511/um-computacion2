#!/usr/bin/env python3
"""
Ejercicio 8 - threading.local() para contexto por hilo.

Simula un servidor donde cada hilo atiende un "request" con su propio
`usuario`, `ip` y `timestamp`. `threading.local()` crea un objeto que se
COMPORTA como global (se accede con el mismo nombre `contexto` desde
cualquier función) pero internamente guarda un valor DISTINTO por hilo: cada
hilo lee y escribe su propia copia, sin pisar la de los demás y sin
necesidad de pasar el contexto como parámetro por todas las funciones ni de
usar locks.

`get_contexto()` siempre devuelve el contexto del hilo que la está llamando.
"""
import random
import threading
import time

contexto = threading.local()


def get_contexto():
    return {
        "usuario": getattr(contexto, "usuario", None),
        "ip": getattr(contexto, "ip", None),
        "timestamp": getattr(contexto, "timestamp", None),
    }


def atender_request(request_id):
    contexto.usuario = f"user_{random.randint(1000, 9999)}"
    contexto.ip = f"192.168.{random.randint(0, 255)}.{random.randint(0, 255)}"
    contexto.timestamp = time.time()

    print(f"Request {request_id} iniciando | contexto: {get_contexto()}")
    time.sleep(random.uniform(0.1, 0.3))

    # Sigue siendo el mismo contexto que se seteó al inicio de esta función,
    # aunque otros hilos hayan corrido y modificado SU PROPIO `contexto` en
    # el medio.
    print(f"Request {request_id} finalizando | usuario: {contexto.usuario}")


def main():
    hilos = [
        threading.Thread(target=atender_request, args=(i,), name=f"Request-{i}")
        for i in range(6)
    ]

    for h in hilos:
        h.start()
    for h in hilos:
        h.join()

    print("\nTodos los requests atendidos, cada uno con su propio contexto")
    print("(sin threading.local() habría que pasar el contexto como parámetro")
    print("a cada función, o usar un dict global protegido por lock indexado")
    print("por thread id).")


if __name__ == "__main__":
    main()
