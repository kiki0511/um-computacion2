#!/usr/bin/env python3
"""
Ejercicio 9 (OBLIGATORIO) - Descargador paralelo.

Descarga una lista de URLs usando un POOL FIJO de threads (no se crea un
thread por URL, se reutilizan N workers tomando trabajo de una
queue.Queue). Cada worker:

- saca una URL de la cola
- intenta descargarla con urllib (timeout de 10s)
- guarda en `resultados` (protegido por lock) si fue ok, cuántos bytes bajó
  y cuánto tardó, o el error si falló

Al final se muestran estadísticas: descargas exitosas, bytes totales y
tiempo total. Como la descarga es I/O-bound (esperando la red), threading
da una mejora real acá.
"""
import queue
import threading
import time
import urllib.error
import urllib.request

NUM_WORKERS = 4

URLS = [
    "https://www.python.org",
    "https://docs.python.org",
    "https://pypi.org",
    "https://www.google.com",
    "https://www.github.com",
    "https://noexiste.dominio.invalido",  # para ver el manejo de errores
]


def worker(in_q, out_list, lock):
    while True:
        url = in_q.get()
        if url is None:
            in_q.task_done()
            break

        inicio = time.time()
        try:
            response = urllib.request.urlopen(url, timeout=10)
            datos = response.read()
            with lock:
                out_list.append({
                    "url": url,
                    "ok": True,
                    "bytes": len(datos),
                    "tiempo": time.time() - inicio,
                })
        except Exception as e:
            with lock:
                out_list.append({
                    "url": url,
                    "ok": False,
                    "error": str(e),
                    "tiempo": time.time() - inicio,
                })

        in_q.task_done()


def main():
    in_q = queue.Queue()
    resultados = []
    lock = threading.Lock()

    workers = [
        threading.Thread(target=worker, args=(in_q, resultados, lock))
        for _ in range(NUM_WORKERS)
    ]
    for w in workers:
        w.start()

    inicio = time.time()
    for url in URLS:
        in_q.put(url)

    in_q.join()  # espera a que todas las URLs sean procesadas

    for _ in workers:
        in_q.put(None)  # centinelas para que cada worker termine su loop
    for w in workers:
        w.join()

    tiempo_total = time.time() - inicio

    ok = [r for r in resultados if r["ok"]]
    errores = [r for r in resultados if not r["ok"]]
    bytes_total = sum(r.get("bytes", 0) for r in ok)

    print("Resultado por URL:")
    for r in resultados:
        if r["ok"]:
            print(f"  OK   {r['url']:35s} {r['bytes']:>8} bytes  {r['tiempo']:.2f}s")
        else:
            print(f"  ERR  {r['url']:35s} {r['error']}")

    print(f"\nDescargas exitosas: {len(ok)}/{len(URLS)}")
    print(f"Bytes totales: {bytes_total:,}")
    print(f"Tiempo total: {tiempo_total:.2f}s (con {NUM_WORKERS} workers en paralelo)")


if __name__ == "__main__":
    main()
