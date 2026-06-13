#!/usr/bin/env python3
"""
Ejercicio 1 - Race condition en cuenta bancaria.

`CuentaInsegura.depositar` lee `self.saldo`, duerme 0.001s (simula
procesamiento) y recién ahí escribe el nuevo valor. Esa ventana entre leer y
escribir es la "ventana de vulnerabilidad".

Para que el resultado esperado sea exacto y comparable entre corridas, TODOS
los hilos hacen la MISMA operación (depositar $10), una cantidad fija de
veces:

    saldo_esperado = saldo_inicial + NUM_HILOS * OPERACIONES_POR_HILO * MONTO

- Con `CuentaInsegura`: varios depósitos "se pierden" porque dos hilos leen
  el mismo `saldo` viejo y el segundo pisa el resultado del primero. El saldo
  final queda POR DEBAJO del esperado, y varía entre corridas (no
  determinista).
- Con `CuentaSegura`: el cuerpo de `depositar` queda dentro de
  `with self.lock:`, volviendo "leer + dormir + escribir" atómico. El saldo
  final es SIEMPRE exactamente el esperado.

(El archivo `demo_race_condition.py`, provisto por la cátedra, hace una
demostración equivalente con un contador simple y mide el % de incrementos
perdidos en muchas corridas.)
"""
import threading
import time

NUM_HILOS = 10
OPERACIONES_POR_HILO = 100
SALDO_INICIAL = 1000
MONTO = 10
CORRIDAS = 5


class CuentaInsegura:
    def __init__(self, saldo):
        self.saldo = saldo

    def depositar(self, cantidad):
        actual = self.saldo
        time.sleep(0.0001)  # abre la ventana de carrera
        self.saldo = actual + cantidad


class CuentaSegura:
    def __init__(self, saldo):
        self.saldo = saldo
        self.lock = threading.Lock()

    def depositar(self, cantidad):
        with self.lock:
            actual = self.saldo
            time.sleep(0.0001)
            self.saldo = actual + cantidad


def hacer_depositos(cuenta):
    for _ in range(OPERACIONES_POR_HILO):
        cuenta.depositar(MONTO)


def correr(clase_cuenta):
    cuenta = clase_cuenta(SALDO_INICIAL)
    hilos = [threading.Thread(target=hacer_depositos, args=(cuenta,)) for _ in range(NUM_HILOS)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    return cuenta.saldo


def main():
    esperado = SALDO_INICIAL + NUM_HILOS * OPERACIONES_POR_HILO * MONTO
    print(f"Saldo inicial: {SALDO_INICIAL}")
    print(f"{NUM_HILOS} hilos x {OPERACIONES_POR_HILO} depósitos de ${MONTO} cada uno")
    print(f"Saldo esperado: {esperado}\n")

    print("=== CuentaInsegura (sin Lock) ===")
    resultados = [correr(CuentaInsegura) for _ in range(CORRIDAS)]
    for i, r in enumerate(resultados, 1):
        perdido = esperado - r
        print(f"  Corrida {i}: saldo final = {r}  (perdidos: {perdido})")
    print(f"  Resultados distintos entre corridas: {len(set(resultados))} de {CORRIDAS}")
    print("  -> Sin Lock, el resultado es <= esperado y no determinista: depende")
    print("     de cómo el scheduler intercala lecturas y escrituras.")

    print("\n=== CuentaSegura (con Lock) ===")
    resultados = [correr(CuentaSegura) for _ in range(CORRIDAS)]
    for i, r in enumerate(resultados, 1):
        print(f"  Corrida {i}: saldo final = {r}")
    assert all(r == esperado for r in resultados), "Con Lock, el saldo siempre debe ser el esperado"
    print(f"  -> Siempre da exactamente {esperado}: el Lock vuelve atómica")
    print("     la secuencia leer-modificar-escribir.")


if __name__ == "__main__":
    main()
