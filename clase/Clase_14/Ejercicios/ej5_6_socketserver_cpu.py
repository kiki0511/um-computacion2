#!/usr/bin/env python3
"""
Ejercicio 5: socketserver.ThreadingTCPServer
Ejercicio 6: servidor con carga CPU-bound real

Modos:
  servidor_echo_threading  → eco con ThreadingTCPServer
  servidor_echo_forking    → eco con ForkingTCPServer
  servidor_cpu_threads     → carga CPU con threads
  servidor_cpu_fork        → carga CPU con fork
  demo_gil                 → demuestra el efecto del GIL
  respuestas               → respuestas conceptuales de ej5 y ej6
"""
import os
import socket
import socketserver
import sys
import threading
import time

HOST = 'localhost'
PORT = 8080
LENTO = 0.5


# ─────────────────────────────────────────────
# Ejercicio 5: socketserver
# ─────────────────────────────────────────────

class EchoHandler(socketserver.StreamRequestHandler):
    """
    Handler de eco usando la interfaz StreamRequestHandler.
    self.rfile → archivo de lectura (resuelve el problema de framing por líneas)
    self.wfile → archivo de escritura
    """
    def handle(self):
        addr = self.client_address
        print(f"[socketserver] Conexión de {addr}")
        try:
            # rfile.readline() hace framing por \n automáticamente
            # (resuelve el problema de TCP como flujo de bytes)
            for linea in self.rfile:
                if not linea:
                    break
                self.wfile.write(linea)
                self.wfile.flush()
        except (ConnectionResetError, BrokenPipeError):
            pass
        print(f"[socketserver] {addr} desconectado")


class ServidorThreading(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True   # los threads mueren con el proceso principal


class ServidorForking(socketserver.ForkingTCPServer):
    allow_reuse_address = True


def servidor_echo_threading():
    print(f"[ThreadingTCPServer] Escuchando en {HOST}:{PORT}")
    with ServidorThreading((HOST, PORT), EchoHandler) as server:
        server.serve_forever()


def servidor_echo_forking():
    print(f"[ForkingTCPServer] Escuchando en {HOST}:{PORT}")
    with ServidorForking((HOST, PORT), EchoHandler) as server:
        server.serve_forever()


# ─────────────────────────────────────────────
# Ejercicio 6: carga CPU-bound
# ─────────────────────────────────────────────

def trabajo_cpu(n=2_000_000):
    """CPU-bound de verdad: no libera el GIL durante el cómputo."""
    total = 0
    for i in range(n):
        total += i * i
    return total


def demo_gil():
    """
    Demuestra el efecto del GIL en trabajo CPU-bound con threads.
    Con N threads haciendo trabajo CPU, tarda casi N veces más que 1 solo.
    """
    N = 4
    n = 1_000_000

    print(f"=== Trabajo CPU-bound ({n} iteraciones) ===\n")

    # Un solo thread (línea de base)
    t0 = time.time()
    trabajo_cpu(n)
    t_single = time.time() - t0
    print(f"  1 thread:  {t_single:.3f}s")

    # N threads en paralelo (GIL limita a 1 CPU efectivo)
    t0 = time.time()
    threads = [threading.Thread(target=trabajo_cpu, args=(n,)) for _ in range(N)]
    for t in threads: t.start()
    for t in threads: t.join()
    t_threads = time.time() - t0
    print(f"  {N} threads: {t_threads:.3f}s (speedup: {t_single*N/t_threads:.2f}x, esperado con GIL: ~1x)")

    # N procesos en paralelo (sin GIL: aprovecha múltiples núcleos)
    import multiprocessing
    t0 = time.time()
    procs = [multiprocessing.Process(target=trabajo_cpu, args=(n,)) for _ in range(N)]
    for p in procs: p.start()
    for p in procs: p.join()
    t_procs = time.time() - t0
    ncores = os.cpu_count()
    print(f"  {N} procs:  {t_procs:.3f}s (speedup: {t_single*N/t_procs:.2f}x, núcleos: {ncores})")

    print(f"\nConclusión:")
    print(f"  Threads CPU-bound: NO escalan (GIL impide paralelismo real).")
    print(f"  Procesos CPU-bound: SÍ escalan hasta el número de núcleos.")
    print(f"  Para un servidor CPU-bound: usar fork/procesos, no threads.")


def servidor_cpu_threads():
    """Servidor de threads con carga CPU: threads NO escalan bien."""
    def atender(conn, addr):
        try:
            while True:
                datos = conn.recv(4096)
                if not datos:
                    break
                resultado = trabajo_cpu()  # CPU-bound: el GIL serializa
                conn.sendall(f"resultado={resultado}\n".encode())
        except (ConnectionResetError, BrokenPipeError):
            pass
        finally:
            conn.close()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, PORT))
        srv.listen(128)
        ncores = os.cpu_count()
        print(f"[Threads+CPU] pid={os.getpid()} en {HOST}:{PORT} ({ncores} núcleos)")
        print("Con carga CPU-bound, los threads no escalan: el GIL serializa.")
        while True:
            conn, addr = srv.accept()
            threading.Thread(target=atender, args=(conn, addr), daemon=True).start()


def servidor_cpu_fork():
    """Servidor fork con carga CPU: procesos SÍ aprovechan múltiples núcleos."""
    import signal as sig
    sig.signal(sig.SIGCHLD, sig.SIG_IGN)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, PORT))
        srv.listen(128)
        ncores = os.cpu_count()
        print(f"[Fork+CPU] pid={os.getpid()} en {HOST}:{PORT} ({ncores} núcleos)")
        print("Con carga CPU-bound, fork aprovecha múltiples núcleos.")
        while True:
            try:
                conn, addr = srv.accept()
            except InterruptedError:
                continue
            pid = os.fork()
            if pid == 0:
                srv.close()
                try:
                    while True:
                        datos = conn.recv(4096)
                        if not datos:
                            break
                        resultado = trabajo_cpu()  # corre en su propio proceso/CPU
                        conn.sendall(f"resultado={resultado}\n".encode())
                except (ConnectionResetError, BrokenPipeError):
                    pass
                finally:
                    conn.close()
                    os._exit(0)
            else:
                conn.close()


RESPUESTAS = """
╔══════════════════════════════════════════════════════════════╗
║      Respuestas Ejercicios 5 y 6                            ║
╚══════════════════════════════════════════════════════════════╝

═══ EJERCICIO 5: socketserver ═══

[5.1] ThreadingTCPServer vs server_threads.py manual:
Rendimiento prácticamente idéntico para carga I/O-bound.
socketserver es una abstracción sobre el mismo mecanismo.
La diferencia es código: socketserver requiere mucho menos.

[5.2] ¿Qué problema de clase 13 resuelve self.rfile?
El framing por líneas. rfile.readline() bloquea hasta encontrar \n
y devuelve la línea completa. Resuelve automáticamente el problema
de que TCP es un flujo y puede partir/fusionar mensajes.
(Exactamente lo que implementamos a mano con el buffer en ej3_framing.py)

[5.3] ForkingTCPServer vs ThreadingTCPServer:
Para I/O-bound: similar rendimiento, ForkingTCPServer un poco más lento
por el overhead de fork() vs thread creation.
Para CPU-bound: ForkingTCPServer escala mejor (evita el GIL).
ForkingTCPServer solo funciona en Unix (no en Windows).

[5.4] ¿El bucle de accept() se parece al manual?
Sí. socketserver.BaseServer.serve_forever() llama a _handle_request_noblock()
que llama a get_request() (que es accept()) en un bucle, igual que
lo que escribimos. La abstracción oculta el boilerplate pero el
mecanismo subyacente es idéntico.

[5.5] ¿Por qué escribir las estrategias a mano si socketserver ya existe?
Para entender qué hay debajo. socketserver oculta:
  - La diferencia entre fork() y threading
  - El manejo de SIGCHLD y zombies
  - SO_REUSEADDR y por qué importa
  - Los problemas de descriptores en fork
  - Race conditions en estado compartido
Quien no entiende lo de abajo no puede debuggear cuando algo falla,
y no puede hacer decisiones informadas sobre cuándo usar cada estrategia.

═══ EJERCICIO 6: CPU-bound ═══

[6.1] server_threads.py con carga CPU y 10 clientes: ¿escala?
NO. Con el GIL, solo un thread puede ejecutar bytecodes Python a la vez.
10 threads haciendo trabajo CPU terminan en ~10x el tiempo de 1 solo.
No hay paralelismo real: el GIL serializa la ejecución.

[6.2] server_fork.py con la misma carga: ¿escala?
SÍ (hasta el número de núcleos disponibles). Cada proceso tiene su
propio intérprete Python y su propia instancia del GIL. No compiten.
Con 4 núcleos, 4 clientes simultáneos corren en paralelo real.

[6.3] ¿Por qué la diferencia?
Threads: comparten el mismo GIL → serialización del intérprete.
Procesos (fork): cada uno tiene su GIL → paralelismo real.
El GIL existe para proteger las estructuras internas del intérprete
(refcounting, etc.); los procesos no comparten esas estructuras.

[6.4] Python con GIL:
>>> import sys; print('con GIL' if sys._is_gil_enabled() else 'SIN GIL')
El build estándar tiene GIL. El free-threaded (3.14+) no.

[6.5] Con build free-threaded:
  - Los threads CPU-bound SÍ escalan (no hay GIL que serialice).
  - La diferencia threads vs fork para CPU se reduce significativamente.
  - Lo que NO cambia: el overhead de memoria de fork (copia de espacio
    de direcciones), y que los procesos no comparten estado por defecto.
    Fork sigue siendo relevante para aislamiento (un hijo que crashea
    no afecta al padre ni a otros hijos).
"""

MODOS = {
    'servidor_echo_threading': servidor_echo_threading,
    'servidor_echo_forking': servidor_echo_forking,
    'servidor_cpu_threads': servidor_cpu_threads,
    'servidor_cpu_fork': servidor_cpu_fork,
    'demo_gil': demo_gil,
    'respuestas': lambda: print(RESPUESTAS),
}

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in MODOS:
        print(f"Uso: python3 {sys.argv[0]} <modo>")
        print(f"Modos: {', '.join(MODOS)}")
        sys.exit(1)
    try:
        MODOS[sys.argv[1]]()
    except KeyboardInterrupt:
        print('\nDetenido.')
