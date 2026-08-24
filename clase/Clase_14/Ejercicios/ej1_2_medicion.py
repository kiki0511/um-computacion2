#!/usr/bin/env python3
"""
Ejercicios 1 y 2: Medición de las cuatro estrategias y el pool que satura.

Estos ejercicios son principalmente de observación/medición usando los
servidores del profe. Este archivo contiene:
  - Las respuestas conceptuales a todas las preguntas
  - Un mini-benchmark propio para demostrar los conceptos sin herramientas externas

Uso:
  python3 ej1_2_medicion.py respuestas
  python3 ej1_2_medicion.py mini_benchmark
"""
import socket
import threading
import time
import sys


# ─────────────────────────────────────────────
# Mini benchmark propio (no depende de benchmark.py del profe)
# ─────────────────────────────────────────────

def mini_benchmark(host='localhost', port=8080, clientes=10, mensaje=b'ping\n'):
    """
    Lanza N clientes simultáneos y mide tiempo total + latencias.
    """
    latencias = []
    errores = [0]
    lock = threading.Lock()
    barrier = threading.Barrier(clientes)

    def cliente(i):
        try:
            barrier.wait()  # todos arrancan juntos
            t0 = time.time()
            with socket.create_connection((host, port), timeout=30) as s:
                s.sendall(mensaje)
                s.recv(4096)
            latencia = time.time() - t0
            with lock:
                latencias.append(latencia)
        except Exception as e:
            with lock:
                errores[0] += 1

    threads = [threading.Thread(target=cliente, args=(i,)) for i in range(clientes)]
    t_inicio = time.time()
    for t in threads: t.start()
    for t in threads: t.join()
    t_total = time.time() - t_inicio

    if latencias:
        print(f"  Clientes:      {clientes}")
        print(f"  Tiempo total:  {t_total:.3f}s")
        print(f"  Latencia mín:  {min(latencias):.3f}s")
        print(f"  Latencia máx:  {max(latencias):.3f}s")
        print(f"  Latencia avg:  {sum(latencias)/len(latencias):.3f}s")
        print(f"  Throughput:    {len(latencias)/t_total:.1f} req/s")
        print(f"  Errores:       {errores[0]}")
    else:
        print(f"  TODOS FALLARON ({errores[0]} errores)")


def run_mini_benchmark():
    print("Mini benchmark contra servidor en localhost:8080")
    print("Asegurate de tener un servidor corriendo antes.")
    print()
    mini_benchmark(clientes=20)


RESPUESTAS = """
╔══════════════════════════════════════════════════════════════╗
║          Respuestas Ejercicios 1 y 2 - Clase 14             ║
╚══════════════════════════════════════════════════════════════╝

═══ EJERCICIO 1: Medir las cuatro estrategias ═══

[1.1.1] ¿Cuánto tardó el servidor secuencial con 20 clientes y --lento 1?
~20 segundos. El servidor atiende uno por vez: 20 clientes × 1s = 20s.
Coincide exactamente con lo esperado: es un pipeline estrictamente serial.

[1.1.2] Latencia mínima vs máxima: ¿por qué tan distintas?
  - Mínima: el primer cliente en ser atendido espera solo 1s (su propio sleep).
  - Máxima: el último cliente espera que todos los anteriores terminen.
    Con 20 clientes y 1s cada uno: latencia máxima ≈ 20s.
El servidor secuencial convierte la latencia del último cliente en
proporcional a N × tiempo_por_cliente.

[1.1.3] ¿Qué patrón detecta el benchmark como "atención en serie"?
Las conexiones completan de forma estrictamente ordenada y espaciada:
los timestamps de finalización están separados por exactamente ~1s cada uno.
En un servidor concurrente, varios finalizarían al mismo tiempo.

[1.2.4] Tabla de resultados típicos (con --lento 1 y 20 clientes):

┌─────────────┬──────────────┬──────────────┬────────────┐
│ Servidor    │ Tiempo total │ Latencia máx │ Throughput │
├─────────────┼──────────────┼──────────────┼────────────┤
│ Secuencial  │ ~20s         │ ~20s         │ 1 req/s    │
│ Threads     │ ~1s          │ ~1s          │ ~20 req/s  │
│ Fork        │ ~1s          │ ~1s          │ ~20 req/s  │
│ Pool (20)   │ ~1s          │ ~1s          │ ~20 req/s  │
└─────────────┴──────────────┴──────────────┴────────────┘
(Los valores reales varían según la máquina)

[1.2.5] ¿Por qué las tres concurrentes dan prácticamente lo mismo?
Con 20 clientes I/O-bound (solo sleep), el cuello de botella es el
tiempo de espera (1s), no la sobrecarga de crear threads/procesos.
Todas las estrategias permiten que los 20 clientes esperen en paralelo.
La diferencia entre ellas aparece con carga CPU o con miles de clientes.

[1.2.6] Sin --lento: ¿se distinguen las estrategias?
Sí. Sin sleep, el trabajo es mínimo y el overhead domina:
  - Fork: crear un proceso cuesta ~10-100x más que crear un thread.
  - Con conexiones muy rápidas, fork se nota más lento.
El parámetro --lento "oculta" la diferencia diluyendo el overhead en
un tiempo de espera largo. Es como medir coches en un atasco de tráfico.

[1.3.7-8] ¿Dónde se degrada threads vs fork?
  - Threads: el límite suele ser la memoria (cada thread usa ~8MB de stack)
    y el scheduling. Con 1000+ threads el SO empieza a thrash.
  - Fork: el límite es más duro. Cada proceso tiene su propio espacio de
    memoria (no compartida) → mucho más RAM. Con 200-500 procesos la
    máquina puede saturarse de RAM antes que threads.
  - ulimit -n limita descriptores de archivo, no directamente threads/procesos,
    pero un servidor con un fd por cliente puede chocar con ese límite.

═══ EJERCICIO 2: El pool que satura ═══

[2.1] Pool con 5 workers y 20 clientes (--lento 1):
Tiempo total ≈ 4s. Los 20 clientes se dividen en 4 rondas de 5:
  Ronda 1: clientes 1-5  → terminan a los 1s
  Ronda 2: clientes 6-10 → terminan a los 2s
  Ronda 3: clientes 11-15 → terminan a los 3s
  Ronda 4: clientes 16-20 → terminan a los 4s

[2.2] Escalones en la latencia:
Hay 4 escalones visibles: ~1s, ~2s, ~3s, ~4s.
Cada escalón corresponde a una "ronda" de workers disponibles.

[2.3] ¿Algún cliente fue rechazado?
No rechazado, sino demorado. Los clientes en exceso de workers
esperan en la cola del listen() hasta que un worker queda libre.
Rechazado = el SO tira el SYN (buffer lleno). Demorado = acepta la
conexión pero el accept() del servidor tarda (el cliente ya conectó,
el servidor tarda en atenderlo).

[2.4] Pool con --workers 1:
Idéntico al servidor secuencial: un solo worker atiende de a uno.

[2.5] ¿Para qué tipo de carga es correcto el pool?
Para carga de corta duración (request-response rápido), como APIs REST
sin conexiones persistentes. Si cada request dura ~ms, 5 workers pueden
manejar miles de requests/s con baja latencia.
Para conexiones largas (streaming, WebSockets, juegos online), el pool
no sirve: un cliente que se conecta 10 minutos ocupa un worker todo ese tiempo.
"""

MODOS = {
    'respuestas': lambda: print(RESPUESTAS),
    'mini_benchmark': run_mini_benchmark,
}

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in MODOS:
        print(f"Uso: python3 {sys.argv[0]} <modo>")
        print(f"Modos: {', '.join(MODOS)}")
        sys.exit(1)
    MODOS[sys.argv[1]]()
