#!/usr/bin/env python3
"""
Ejercicio 7 - Productor-Consumidor con queue.Queue.

Simula un procesador de imágenes: `procesar_imagen(nombre)` tarda 0.5s.
Un pool fijo de 4 workers (threads) toma imágenes de una `queue.Queue` y las
procesa. Hay 20 imágenes (imagen_001.jpg a imagen_020.jpg).

Patrón de cierre con "centinela": por cada worker se pone un `None` en la
cola al final. Cuando un worker saca un `None`, sabe que no hay más trabajo
y termina su loop.

`cola.join()` bloquea hasta que todos los `task_done()` correspondientes a
los `put()` anteriores fueron llamados, es decir, hasta que las 20 imágenes
fueron procesadas (los centinelas se ponen DESPUÉS de ese join, por eso no
cuentan).

Como I/O-bound con threads, 4 workers procesando 20 imágenes de 0.5s cada
una deberían tardar ~2.5s en total (20 * 0.5s / 4), no 10s.
"""
import queue
import threading
import time

NUM_WORKERS = 4
NUM_IMAGENES = 20

resultados = {}
resultados_lock = threading.Lock()


def procesar_imagen(nombre):
    time.sleep(0.5)
    return f"{nombre} -> procesada"


def worker(q, worker_id):
    contador = 0
    while True:
        imagen = q.get()
        if imagen is None:
            q.task_done()
            break
        resultado = procesar_imagen(imagen)
        print(f"Worker-{worker_id}: {resultado}")
        contador += 1
        q.task_done()

    with resultados_lock:
        resultados[f"Worker-{worker_id}"] = contador


def main():
    cola = queue.Queue()

    workers = [
        threading.Thread(target=worker, args=(cola, i))
        for i in range(NUM_WORKERS)
    ]
    for w in workers:
        w.start()

    inicio = time.perf_counter()

    for i in range(1, NUM_IMAGENES + 1):
        cola.put(f"imagen_{i:03d}.jpg")

    cola.join()  # espera a que las 20 imágenes sean procesadas

    for _ in workers:
        cola.put(None)  # centinelas: uno por worker
    for w in workers:
        w.join()

    tiempo = time.perf_counter() - inicio
    print(f"\nTiempo total: {tiempo:.2f}s (esperado ≈ {NUM_IMAGENES * 0.5 / NUM_WORKERS:.1f}s)")
    print("\nImágenes por worker:")
    total = 0
    for nombre, cant in resultados.items():
        print(f"  {nombre}: {cant} imágenes")
        total += cant
    print(f"  Total: {total}")


if __name__ == "__main__":
    main()
