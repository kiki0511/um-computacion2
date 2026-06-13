#!/usr/bin/env python3
"""
Adicional - RLock (lock reentrante).

Un `threading.Lock` normal NO puede ser adquirido dos veces por el MISMO
hilo: si `metodo_a` toma el lock y dentro llama a `metodo_b`, que también
intenta tomar el mismo lock, el hilo se bloquea a sí mismo (deadlock).

`threading.RLock` sí lo permite: el mismo hilo puede entrar varias veces
(lleva un contador interno), y el lock se libera recién cuando ese hilo
sale de la última sección `with` anidada.

`CuentaBancaria.transferir_a()` toma `self.lock` y, dentro, llama a
`self.retirar()`, que TAMBIÉN toma `self.lock`. Con `Lock` normal esto sería
un deadlock inmediato (el propio hilo esperando un lock que él mismo tiene).
Con `RLock`, funciona porque ambas adquisiciones son del mismo hilo.
"""
import threading


class CuentaBancaria:
    def __init__(self, saldo_inicial):
        self.saldo = saldo_inicial
        self.lock = threading.RLock()

    def depositar(self, cantidad):
        with self.lock:
            self.saldo += cantidad
            print(f"Depositados {cantidad}. Saldo: {self.saldo}")

    def retirar(self, cantidad):
        with self.lock:
            if self.saldo >= cantidad:
                self.saldo -= cantidad
                print(f"Retirados {cantidad}. Saldo: {self.saldo}")
                return True
            return False

    def transferir_a(self, otra_cuenta, cantidad):
        # Toma self.lock Y llama a retirar(), que también toma self.lock.
        # Con Lock normal: deadlock. Con RLock: OK, mismo hilo.
        with self.lock:
            print(f"Transferencia: intentando mover {cantidad}...")
            if self.retirar(cantidad):
                otra_cuenta.depositar(cantidad)
                return True
            return False


def main():
    cuenta_a = CuentaBancaria(1000)
    cuenta_b = CuentaBancaria(500)

    print(f"Saldo inicial A: {cuenta_a.saldo}, B: {cuenta_b.saldo}\n")

    t = threading.Thread(target=cuenta_a.transferir_a, args=(cuenta_b, 300))
    t.start()
    t.join()

    print(f"\nSaldo final A: {cuenta_a.saldo} (esperado: 700)")
    print(f"Saldo final B: {cuenta_b.saldo} (esperado: 800)")
    assert cuenta_a.saldo == 700 and cuenta_b.saldo == 800


if __name__ == "__main__":
    main()
