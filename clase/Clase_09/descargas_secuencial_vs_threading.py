#!/usr/bin/env python3
"""
Ejercicio 2 - Descargas: secuencial vs threading (I/O-bound).

`simular_descarga(url, demora)` simula una descarga "durmiendo" `demora`
segundos (representa tiempo de espera de red, no de CPU).

Con 5 URLs y 1s de demora cada una:
- Secuencial: ~5s (una espera detrás de la otra)
- Con threading: ~1s (las 5 esperas ocurren en paralelo)

Threading rinde muy bien acá porque, mientras un hilo está bloqueado
esperando I/O, el GIL se libera y otro hilo puede avanzar.
"""
import threading
import time

URLS = [f"http://servidor.com/archivo_{i}.zip" for i in range(5)]
DEMORA = 1  # segundos por descarga


def simular_descarga(url, demora):
    time.sleep(demora)
    print(f"Descargado: {url}")


def main():
    # --- Secuencial ---
    inicio = time.perf_counter()
    for url in URLS:
        simular_descarga(url, DEMORA)
    tiempo_secuencial = time.perf_counter() - inicio
    print(f"\nSecuencial: {tiempo_secuencial:.2f}s")

    # --- Paralelo con threading ---
    inicio = time.perf_counter()
    hilos = [
        threading.Thread(target=simular_descarga, args=(url, DEMORA))
        for url in URLS
    ]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    tiempo_paralelo = time.perf_counter() - inicio
    print(f"Threading:  {tiempo_paralelo:.2f}s")

    print(f"Mejora:     {tiempo_secuencial / tiempo_paralelo:.1f}x")


if __name__ == "__main__":
    main()
