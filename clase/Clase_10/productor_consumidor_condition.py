#!/usr/bin/env python3
"""
Ejercicio 2 - Productor-Consumidor con Condition.

`ColaLimitada` es una cola acotada (tamaño máximo `maxsize`) implementada a
mano con `threading.Condition`:

- `put(item)`: si la cola está llena, espera (`condition.wait()`) hasta que
  alguien la vacíe un poco; agrega el item y notifica a quien esté esperando
  en `get`.
- `get()`: si la cola está vacía, espera hasta que alguien ponga algo; sacar
  un item y notifica a quien esté esperando en `put`.

`condition.wait()` SIEMPRE va dentro de un `while`, no de un `if`: cuando se
despierta, hay que volver a chequear la condición (puede que otro hilo se
haya adelantado y la condición ya no se cumpla — "spurious wakeup" o
simplemente que varios esperaban lo mismo).

Para terminar el programa de forma ordenada se usa un `threading.Event`
(`terminado`): los productores lo activan (`.set()`) cuando terminaron de
producir, y los consumidores salen de su loop cuando `terminado` está
activo Y la cola quedó vacía. `get(timeout=...)` evita que un consumidor se
quede esperando para siempre si ya no va a llegar nada más.

2 productores generan 5 items cada uno; 3 consumidores los procesan.
"""
import threading
import time
import random

MAXSIZE = 5
NUM_PRODUCTORES = 2
NUM_CONSUMIDORES = 3
ITEMS_POR_PRODUCTOR = 5


class ColaLimitada:
    def __init__(self, maxsize):
        self.maxsize = maxsize
        self.items = []
        self.condition = threading.Condition()

    def put(self, item, timeout=None):
        """Agrega un item. Bloquea si está llena."""
        with self.condition:
            while len(self.items) >= self.maxsize:
                if not self.condition.wait(timeout):
                    raise TimeoutError("Timeout esperando espacio")
            self.items.append(item)
            self.condition.notify()

    def get(self, timeout=None):
        """Obtiene un item. Bloquea si está vacía."""
        with self.condition:
            while len(self.items) == 0:
                if not self.condition.wait(timeout):
                    raise TimeoutError("Timeout esperando item")
            item = self.items.pop(0)
            self.condition.notify()
            return item

    def size(self):
        with self.condition:
            return len(self.items)


def productor(id, cantidad, cola):
    for i in range(cantidad):
        item = f"P{id}-{i}"
        cola.put(item)
        print(f"[Prod-{id}] Produjo {item}, cola={cola.size()}")
        time.sleep(random.uniform(0.05, 0.15))
    print(f"[Prod-{id}] Terminó")


def consumidor(id, cola, terminado, contadores, lock_contadores):
    procesados = 0
    while not (terminado.is_set() and cola.size() == 0):
        try:
            item = cola.get(timeout=0.3)
            print(f"[Cons-{id}] Consumió {item}, cola={cola.size()}")
            procesados += 1
            time.sleep(random.uniform(0.05, 0.1))
        except TimeoutError:
            pass
    with lock_contadores:
        contadores[f"Cons-{id}"] = procesados
    print(f"[Cons-{id}] Terminó ({procesados} items)")


def main():
    cola = ColaLimitada(MAXSIZE)
    terminado = threading.Event()
    contadores = {}
    lock_contadores = threading.Lock()

    productores = [
        threading.Thread(target=productor, args=(i, ITEMS_POR_PRODUCTOR, cola))
        for i in range(NUM_PRODUCTORES)
    ]
    consumidores = [
        threading.Thread(target=consumidor, args=(i, cola, terminado, contadores, lock_contadores))
        for i in range(NUM_CONSUMIDORES)
    ]

    for c in consumidores:
        c.start()
    for p in productores:
        p.start()

    for p in productores:
        p.join()

    terminado.set()  # avisa a los consumidores que no va a llegar nada más

    for c in consumidores:
        c.join()

    total = sum(contadores.values())
    print("\nItems procesados por consumidor:")
    for nombre, cant in contadores.items():
        print(f"  {nombre}: {cant}")
    print(f"  Total: {total} (esperado: {NUM_PRODUCTORES * ITEMS_POR_PRODUCTOR})")
    assert total == NUM_PRODUCTORES * ITEMS_POR_PRODUCTOR
    print("\nFin del programa")


if __name__ == "__main__":
    main()
