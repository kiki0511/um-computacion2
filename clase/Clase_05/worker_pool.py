#!/usr/bin/env python3
"""
Ejercicio 6.1 - Pool de workers supervisado con señales.

Un proceso supervisor crea N workers (fork) y los vigila. Usa SIGCHLD para
enterarse cuando uno muere (y recogerlo sin zombies); si quedan menos de N,
spawnea reemplazos. SIGTERM/SIGINT propagan un shutdown ordenado a todos.
"""
import os
import signal
import time
import random


class WorkerPool:
    def __init__(self, num_workers):
        self.num_workers = num_workers
        self.workers = {}  # pid -> info
        self.ejecutando = True

        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGCHLD, self._sigchld)

    def _shutdown(self, sig, frame):
        print("\n[SUPERVISOR] Shutdown solicitado")
        self.ejecutando = False
        for pid in list(self.workers.keys()):
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

    def _sigchld(self, sig, frame):
        while True:
            try:
                pid, status = os.waitpid(-1, os.WNOHANG)
                if pid == 0:
                    break
                if pid in self.workers:
                    info = self.workers.pop(pid)
                    codigo = (os.WEXITSTATUS(status)
                              if os.WIFEXITED(status) else -1)
                    print(f"[SUPERVISOR] Worker {info['id']} (pid {pid}) "
                          f"terminó con código {codigo}")
            except ChildProcessError:
                break

    def _worker_main(self, worker_id):
        print(f"[Worker {worker_id}] Iniciado (PID {os.getpid()})")

        def worker_shutdown(sig, frame):
            print(f"[Worker {worker_id}] Recibí SIGTERM, terminando...")
            os._exit(0)

        signal.signal(signal.SIGTERM, worker_shutdown)

        for i in range(random.randint(5, 15)):
            print(f"[Worker {worker_id}] Trabajando... ({i})")
            time.sleep(0.5)

        if random.random() < 0.3:
            print(f"[Worker {worker_id}] ¡Error simulado!")
            os._exit(1)

        print(f"[Worker {worker_id}] Trabajo completado")
        os._exit(0)

    def spawn_worker(self, worker_id):
        pid = os.fork()
        if pid == 0:
            self._worker_main(worker_id)
        else:
            self.workers[pid] = {"id": worker_id, "started": time.time()}
            print(f"[SUPERVISOR] Spawned worker {worker_id} (PID {pid})")

    def run(self):
        print(f"[SUPERVISOR] PID {os.getpid()}, iniciando "
              f"{self.num_workers} workers")

        for i in range(self.num_workers):
            self.spawn_worker(i)

        next_worker_id = self.num_workers
        while self.ejecutando:
            time.sleep(1)
            if len(self.workers) < self.num_workers and self.ejecutando:
                print(f"[SUPERVISOR] Solo {len(self.workers)} workers "
                      f"activos, spawneando más")
                self.spawn_worker(next_worker_id)
                next_worker_id += 1

        while self.workers:
            time.sleep(0.1)

        print("[SUPERVISOR] Todos los workers terminados")


if __name__ == "__main__":
    WorkerPool(3).run()
