#!/usr/bin/env python3
"""
Ejercicio 1: Race condition en cuenta bancaria y su corrección con Lock.
"""
import threading
import time
import random


class CuentaInsegura:
    def __init__(self, saldo):
        self.saldo = saldo

    def depositar(self, cantidad):
        actual = self.saldo
        time.sleep(0.001)  # Simula procesamiento
        self.saldo = actual + cantidad

    def retirar(self, cantidad):
        actual = self.saldo
        time.sleep(0.001)
        if actual >= cantidad:
            self.saldo = actual - cantidad
            return True
        return False


class CuentaSegura:
    def __init__(self, saldo):
        self.saldo = saldo
        self.lock = threading.Lock()

    def depositar(self, cantidad):
        with self.lock:
            actual = self.saldo
            time.sleep(0.001)
            self.saldo = actual + cantidad

    def retirar(self, cantidad):
        with self.lock:
            actual = self.saldo
            time.sleep(0.001)
            if actual >= cantidad:
                self.saldo = actual - cantidad
                return True
            return False


def test_cuenta(cuenta, label):
    def operaciones_aleatorias():
        for _ in range(100):
            if random.choice([True, False]):
                cuenta.depositar(10)
            else:
                cuenta.retirar(10)

    threads = [threading.Thread(target=operaciones_aleatorias) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print(f"[{label}] Saldo esperado: ~1000 | Saldo obtenido: {cuenta.saldo}")


if __name__ == "__main__":
    print("=== 1.1 Cuenta INSEGURA (con race condition) ===")
    test_cuenta(CuentaInsegura(1000), "INSEGURA")

    print("\n=== 1.2 Cuenta SEGURA (con Lock) ===")
    test_cuenta(CuentaSegura(1000), "SEGURA")
