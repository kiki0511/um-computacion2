#!/usr/bin/env python3
"""
Adicional - Chat multi-hilo (sin sincronización avanzada).

Varios "usuarios" (threads productores) envían mensajes a una
`queue.Queue` central. Un thread "display" (consumidor) los muestra a
medida que llegan, en el orden en que fueron encolados por cada usuario
(pero entreverados entre usuarios, porque corren en paralelo).

No hace falta Lock para la cola: `queue.Queue` ya es thread-safe por diseño
(internamente usa un Lock + Condition). El centinela `None` se usa, igual
que en los ejercicios anteriores, para avisarle al display que no hay más
mensajes.
"""
import queue
import threading
import time
import random

USUARIOS = ["Ana", "Beto", "Cami"]
MENSAJES_POR_USUARIO = 4


def usuario(nombre, cola):
    for i in range(1, MENSAJES_POR_USUARIO + 1):
        time.sleep(random.uniform(0.1, 0.4))
        cola.put(f"{nombre}: mensaje {i}")
    print(f"[{nombre}] terminó de enviar sus mensajes")


def display(cola, total_esperado):
    recibidos = 0
    while recibidos < total_esperado:
        msg = cola.get()
        print(f"  >> {msg}")
        recibidos += 1


def main():
    cola = queue.Queue()
    total_mensajes = len(USUARIOS) * MENSAJES_POR_USUARIO

    hilo_display = threading.Thread(target=display, args=(cola, total_mensajes))
    hilo_display.start()

    hilos_usuarios = [
        threading.Thread(target=usuario, args=(nombre, cola))
        for nombre in USUARIOS
    ]
    for h in hilos_usuarios:
        h.start()
    for h in hilos_usuarios:
        h.join()

    hilo_display.join()
    print("\nChat finalizado")


if __name__ == "__main__":
    main()
