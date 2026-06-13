#!/usr/bin/env python3
"""
Ejercicio 4 - Semáforo para pool de recursos.

Un `threading.Semaphore(n)` mantiene un contador interno que arranca en `n`.
`.acquire()` lo decrementa (y bloquea si llega a 0); `.release()` lo
incrementa. A diferencia de `Lock` (que es "1 a la vez"), un Semaphore
permite que hasta `n` hilos tengan el recurso simultáneamente — ideal para
modelar un pool de tamaño fijo (conexiones a una DB, slots de un pool de
workers, etc.).

`ConnectionPool` tiene 3 "conexiones" (slots 0, 1, 2). 10 "clientes" piden
una conexión, la usan un rato y la devuelven, 3 veces cada uno. Como hay más
clientes que conexiones, varios van a tener que ESPERAR (`acquire` bloquea
hasta que algún otro libere). Se llevan estadísticas de cuántos requests
esperaron y cuánto en promedio.

`self.lock` (un Lock normal, separado del semáforo) protege la lista
`conexiones_disponibles` y las estadísticas: el semáforo controla CUÁNTOS
hilos pueden tener una conexión a la vez, pero no protege por sí solo el
acceso a esas estructuras compartidas.
"""
import threading
import time
import random

TAMANO_POOL = 3
NUM_CLIENTES = 10
REQUESTS_POR_CLIENTE = 3


class ConnectionPool:
    def __init__(self, size):
        self.size = size
        self.semaforo = threading.Semaphore(size)
        self.conexiones_disponibles = list(range(size))
        self.lock = threading.Lock()
        self.estadisticas = {
            "total_requests": 0,
            "esperas": 0,
            "tiempo_total_espera": 0.0,
        }

    def obtener(self, timeout=None):
        inicio = time.time()
        if self.semaforo.acquire(timeout=timeout):
            tiempo_espera = time.time() - inicio
            with self.lock:
                conn_id = self.conexiones_disponibles.pop(0)
                self.estadisticas["total_requests"] += 1
                if tiempo_espera > 0.01:
                    self.estadisticas["esperas"] += 1
                    self.estadisticas["tiempo_total_espera"] += tiempo_espera
            return conn_id
        return None

    def liberar(self, conn_id):
        with self.lock:
            self.conexiones_disponibles.append(conn_id)
        self.semaforo.release()

    def mostrar_estadisticas(self):
        print("\n=== Estadísticas del pool ===")
        print(f"Total requests: {self.estadisticas['total_requests']}")
        print(f"Requests que esperaron: {self.estadisticas['esperas']}")
        if self.estadisticas["esperas"] > 0:
            prom = self.estadisticas["tiempo_total_espera"] / self.estadisticas["esperas"]
            print(f"Tiempo promedio de espera: {prom:.3f}s")


def cliente(id, pool):
    for _ in range(REQUESTS_POR_CLIENTE):
        conn = pool.obtener(timeout=5)
        if conn is not None:
            print(f"[Cliente {id}] Obtuvo conexión {conn}")
            time.sleep(random.uniform(0.1, 0.3))  # usar la conexión
            pool.liberar(conn)
            print(f"[Cliente {id}] Liberó conexión {conn}")
        else:
            print(f"[Cliente {id}] Timeout esperando conexión")
        time.sleep(random.uniform(0.02, 0.05))


def main():
    pool = ConnectionPool(TAMANO_POOL)

    hilos = [threading.Thread(target=cliente, args=(i, pool)) for i in range(NUM_CLIENTES)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()

    pool.mostrar_estadisticas()
    esperado = NUM_CLIENTES * REQUESTS_POR_CLIENTE
    print(f"\nTotal esperado: {esperado} (={NUM_CLIENTES} clientes x {REQUESTS_POR_CLIENTE} requests)")
    assert pool.estadisticas["total_requests"] == esperado
    assert len(pool.conexiones_disponibles) == TAMANO_POOL, "todas las conexiones deben quedar liberadas"
    print(f"Conexiones disponibles al final: {pool.conexiones_disponibles} (todas liberadas)")


if __name__ == "__main__":
    main()
