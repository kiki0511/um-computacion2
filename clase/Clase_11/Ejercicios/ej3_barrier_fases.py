#!/usr/bin/env python3
"""
Ejercicio 3: Procesamiento paralelo por fases con Barrier.
Todos los workers deben completar la fase 1 antes de que cualquiera
pueda empezar la fase 2. La Barrier actúa como punto de sincronización.
"""
import threading
import time
import random

NUM_WORKERS = 4
datos = [i * 10 for i in range(NUM_WORKERS)]
resultados_fase1 = [0] * NUM_WORKERS
resultados_fase2 = [0] * NUM_WORKERS


def imprimir_estado():
    """Callback que ejecuta la Barrier al completar cada fase."""
    print(f"  >>> Fase completada. Fase1: {resultados_fase1} | Fase2: {resultados_fase2}")


barrera = threading.Barrier(NUM_WORKERS, action=imprimir_estado)


def worker(id):
    # Fase 1: procesar datos locales
    print(f"[Worker {id}] Fase 1: procesando dato {datos[id]}...")
    time.sleep(random.uniform(0.5, 1.5))
    resultados_fase1[id] = datos[id] * 2
    print(f"[Worker {id}] Fase 1: resultado = {resultados_fase1[id]}")

    barrera.wait()  # Esperar a que todos terminen fase 1

    # Fase 2: combinar con vecino
    print(f"[Worker {id}] Fase 2: combinando con vecino...")
    time.sleep(random.uniform(0.3, 0.8))
    vecino = (id + 1) % NUM_WORKERS
    resultados_fase2[id] = resultados_fase1[id] + resultados_fase1[vecino]
    print(f"[Worker {id}] Fase 2: resultado = {resultados_fase2[id]}")

    barrera.wait()  # Esperar a que todos terminen fase 2

    print(f"[Worker {id}] Procesamiento completo!")


if __name__ == "__main__":
    print(f"Datos iniciales: {datos}\n")

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(NUM_WORKERS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print(f"\nResultados finales: {resultados_fase2}")
