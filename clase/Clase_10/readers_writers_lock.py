#!/usr/bin/env python3
"""
Ejercicio 5 (OBLIGATORIO) - Readers-Writers Lock.

Reglas a implementar:
- Múltiples lectores pueden leer simultáneamente.
- Solo un escritor puede escribir a la vez.
- Mientras hay un escritor, no puede haber lectores.
- Mientras hay lectores, no puede haber escritores.

`ReadWriteLock` usa un único `threading.Lock` interno y DOS `Condition`
sobre ese mismo lock (`can_read` y `can_write`):

- `acquire_read()`: mientras haya `writers > 0`, espera en `can_read`.
  Cuando puede, incrementa `readers`. Varios lectores pueden pasar esta
  condición sin pisarse porque incrementar `readers` está protegido por el
  lock subyacente de la Condition.
- `release_read()`: decrementa `readers`; si llega a 0, despierta a UN
  escritor en espera (`can_write.notify()`) — recién ahí un escritor puede
  intentar entrar.
- `acquire_write()`: mientras haya lectores O escritores activos, espera en
  `can_write`. Cuando puede, marca `writers = 1`.
- `release_write()`: marca `writers = 0`, despierta a TODOS los lectores en
  espera (`can_read.notify_all()`, porque todos pueden entrar juntos) y a UN
  escritor (`can_write.notify()`).

`ReadLock`/`WriteLock` son context managers (`with ReadLock(rwlock): ...`)
que envuelven `acquire_*`/`release_*` para que el código de uso sea simple y
no se olvide de liberar (incluso si hay una excepción).

Test: 5 lectores (5 lecturas cada uno) y 2 escritores (3 escrituras cada
uno), arrancados en orden mezclado.
"""
import threading
import time
import random

NUM_LECTORES = 5
LECTURAS_POR_LECTOR = 5
NUM_ESCRITORES = 2
ESCRITURAS_POR_ESCRITOR = 3


class ReadWriteLock:
    def __init__(self):
        self.readers = 0
        self.writers = 0
        self.lock = threading.Lock()
        self.can_read = threading.Condition(self.lock)
        self.can_write = threading.Condition(self.lock)

    def acquire_read(self):
        with self.lock:
            while self.writers > 0:
                self.can_read.wait()
            self.readers += 1

    def release_read(self):
        with self.lock:
            self.readers -= 1
            if self.readers == 0:
                self.can_write.notify()

    def acquire_write(self):
        with self.lock:
            while self.readers > 0 or self.writers > 0:
                self.can_write.wait()
            self.writers += 1

    def release_write(self):
        with self.lock:
            self.writers -= 1
            self.can_read.notify_all()
            self.can_write.notify()


class ReadLock:
    def __init__(self, rwlock):
        self.rwlock = rwlock

    def __enter__(self):
        self.rwlock.acquire_read()

    def __exit__(self, *args):
        self.rwlock.release_read()


class WriteLock:
    def __init__(self, rwlock):
        self.rwlock = rwlock

    def __enter__(self):
        self.rwlock.acquire_write()

    def __exit__(self, *args):
        self.rwlock.release_write()


def lector(id, rwlock, datos, max_lectores_simultaneos):
    for _ in range(LECTURAS_POR_LECTOR):
        with ReadLock(rwlock):
            with max_lectores_simultaneos["lock"]:
                max_lectores_simultaneos["actuales"] += 1
                max_lectores_simultaneos["max"] = max(
                    max_lectores_simultaneos["max"], max_lectores_simultaneos["actuales"]
                )
            valor = datos["valor"]
            datos["lecturas"] += 1
            print(f"[Lector {id}] Leyó valor={valor}")
            time.sleep(random.uniform(0.02, 0.06))
            with max_lectores_simultaneos["lock"]:
                max_lectores_simultaneos["actuales"] -= 1
        time.sleep(random.uniform(0.02, 0.05))


def escritor(id, rwlock, datos):
    for i in range(ESCRITURAS_POR_ESCRITOR):
        with WriteLock(rwlock):
            datos["valor"] = id * 100 + i
            datos["escrituras"] += 1
            print(f"[Escritor {id}] Escribió valor={datos['valor']}")
            time.sleep(random.uniform(0.05, 0.1))
        time.sleep(random.uniform(0.05, 0.1))


def main():
    rwlock = ReadWriteLock()
    datos = {"valor": 0, "lecturas": 0, "escrituras": 0}
    max_lectores_simultaneos = {"lock": threading.Lock(), "actuales": 0, "max": 0}

    hilos = []
    for i in range(NUM_LECTORES):
        hilos.append(threading.Thread(target=lector, args=(i, rwlock, datos, max_lectores_simultaneos)))
    for i in range(NUM_ESCRITORES):
        hilos.append(threading.Thread(target=escritor, args=(i, rwlock, datos)))

    random.shuffle(hilos)  # mezclar orden de arranque

    for h in hilos:
        h.start()
    for h in hilos:
        h.join()

    print("\nEstadísticas finales:")
    print(f"  Valor final: {datos['valor']}")
    print(f"  Total lecturas: {datos['lecturas']} (esperado: {NUM_LECTORES * LECTURAS_POR_LECTOR})")
    print(f"  Total escrituras: {datos['escrituras']} (esperado: {NUM_ESCRITORES * ESCRITURAS_POR_ESCRITOR})")
    print(f"  Máx. lectores simultáneos observados: {max_lectores_simultaneos['max']}")
    print(f"  (debería poder ser > 1: varios lectores SÍ pueden solaparse)")

    assert datos["lecturas"] == NUM_LECTORES * LECTURAS_POR_LECTOR
    assert datos["escrituras"] == NUM_ESCRITORES * ESCRITURAS_POR_ESCRITOR
    assert rwlock.readers == 0 and rwlock.writers == 0, "no debe quedar nadie dentro del lock"
    print("\nOK: sin deadlocks, todos los hilos terminaron y el lock quedó libre.")


if __name__ == "__main__":
    main()
