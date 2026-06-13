#!/usr/bin/env python3
"""
Ejercicio 3 - Barrier para procesamiento por fases.

`threading.Barrier(n, action=...)` bloquea a cada hilo que llama a
`.wait()` hasta que los `n` hilos llegaron a ese punto. Cuando llega el
último, se ejecuta `action` (una sola vez) y luego TODOS los hilos quedan
liberados a la vez. Es el patrón típico de algoritmos por fases: todos
terminan la fase 1 antes de que cualquiera empiece la fase 2.

4 workers procesan datos en 2 fases:
- Fase 1: cada worker calcula `dato * 2` sobre SU dato.
- Barrier: espera a que los 4 terminen la fase 1 (y muestra los resultados
  parciales con `action`).
- Fase 2: cada worker combina su resultado de fase 1 con el de su "vecino"
  (worker (id+1) % NUM_WORKERS) — por eso necesita que TODOS hayan
  terminado la fase 1 antes de poder leer el resultado del vecino.
- Barrier final: por prolijidad, para que todos terminen "a la vez".
"""
import threading
import time
import random

NUM_WORKERS = 4


def main():
    datos = [i * 10 for i in range(NUM_WORKERS)]
    resultados_fase1 = [0] * NUM_WORKERS
    resultados_fase2 = [0] * NUM_WORKERS

    def imprimir_estado():
        print(f"  >> Barrier: los {NUM_WORKERS} workers llegaron a este punto")

    barrera = threading.Barrier(NUM_WORKERS, action=imprimir_estado)

    def worker(id):
        # Fase 1: procesar datos locales
        print(f"[Worker {id}] Fase 1: procesando...")
        time.sleep(random.uniform(0.1, 0.3))
        resultados_fase1[id] = datos[id] * 2
        print(f"[Worker {id}] Fase 1: completada ({resultados_fase1[id]})")

        barrera.wait()  # nadie pasa a fase 2 hasta que TODOS terminaron fase 1

        # Fase 2: combinar con el resultado del vecino (ya disponible, gracias al Barrier)
        vecino = (id + 1) % NUM_WORKERS
        time.sleep(random.uniform(0.1, 0.2))
        resultados_fase2[id] = resultados_fase1[id] + resultados_fase1[vecino]
        print(f"[Worker {id}] Fase 2: completada ({resultados_fase2[id]})")

        barrera.wait()  # sincroniza el final

    print(f"Datos iniciales: {datos}\n")

    hilos = [threading.Thread(target=worker, args=(i,)) for i in range(NUM_WORKERS)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()

    print(f"\nResultados fase 1: {resultados_fase1}")
    print(f"Resultados fase 2 (cada uno = propio*2 + vecino*2): {resultados_fase2}")


if __name__ == "__main__":
    main()
