#!/usr/bin/env python3
"""
Ejercicio 7 - Pipeline de 3 etapas con Queue.

Cada etapa corre en su propio proceso y se conecta con la siguiente vía Queue:
  1. multiplicar por 2
  2. sumar 10
  3. formatear como string
El centinela None se propaga etapa por etapa para cerrar el pipeline.

Preguntas:
  - Si una etapa es mucho más lenta, se vuelve el cuello de botella: el
    throughput total queda limitado por ella (las demás esperan).
  - Para escalar la etapa lenta se replica: varios procesos consumiendo de la
    misma cola de entrada (fan-out / pool de workers en esa etapa).
"""
from multiprocessing import Process, Queue
import time


def etapa_multiplicar(in_q, out_q):
    while True:
        item = in_q.get()
        if item is None:
            out_q.put(None)
            break
        time.sleep(0.05)
        out_q.put(item * 2)


def etapa_sumar(in_q, out_q):
    while True:
        item = in_q.get()
        if item is None:
            out_q.put(None)
            break
        time.sleep(0.05)
        out_q.put(item + 10)


def etapa_formatear(in_q, out_q):
    while True:
        item = in_q.get()
        if item is None:
            out_q.put(None)
            break
        time.sleep(0.05)
        out_q.put(f"resultado_{item:03d}")


def main():
    q1, q2, q3, q4 = Queue(), Queue(), Queue(), Queue()

    p1 = Process(target=etapa_multiplicar, args=(q1, q2))
    p2 = Process(target=etapa_sumar, args=(q2, q3))
    p3 = Process(target=etapa_formatear, args=(q3, q4))
    p1.start()
    p2.start()
    p3.start()

    for i in range(10):
        q1.put(i)
    q1.put(None)  # señal de fin

    while True:
        result = q4.get()
        if result is None:
            break
        print(f"Final: {result}")

    p1.join()
    p2.join()
    p3.join()


if __name__ == "__main__":
    main()
