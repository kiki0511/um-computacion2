#!/usr/bin/env python3
"""
Ejercicio 3.2 - Transacciones con context manager.

Permite revertir cambios en un objeto si ocurre una excepción dentro
del bloque with. Similar al concepto de transacción en bases de datos.
"""


class Transaction:
    """
    Context manager que hace snapshots del estado de un objeto y lo
    restaura si ocurre una excepción.

    Funciona con cualquier objeto que tenga atributos regulares (no
    tipos especiales como slots o propiedades con side-effects).

    Uso:
        with Transaction(mi_objeto):
            mi_objeto.atributo = nuevo_valor
            # Si algo falla acá, el atributo vuelve al valor original

    Ejemplo:
        cuenta = Cuenta(saldo=1000)
        try:
            with Transaction(cuenta):
                cuenta.saldo -= 500
                raise ValueError("Fallo!")
        except ValueError:
            pass
        print(cuenta.saldo)  # 1000 — se revirtió
    """

    def __init__(self, objeto):
        """
        Args:
            objeto: el objeto cuyos atributos se van a proteger.
        """
        self._objeto = objeto
        self._snapshot = None

    def __enter__(self) -> "Transaction":
        # Guardar copia profunda de todos los atributos actuales
        self._snapshot = vars(self._objeto).copy()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is not None:
            # Hubo una excepción: restaurar el estado original
            vars(self._objeto).clear()
            vars(self._objeto).update(self._snapshot)

        # False = no suprimimos la excepción (la relanzamos hacia afuera)
        return False


if __name__ == "__main__":
    class Cuenta:
        def __init__(self, saldo: float):
            self.saldo = saldo
            self.nombre = "Sin nombre"
            self.activa = True

        def __repr__(self):
            return f"Cuenta(saldo={self.saldo}, nombre='{self.nombre}', activa={self.activa})"

    cuenta = Cuenta(1000)
    print(f"Inicial: {cuenta}")

    print("\n=== Transacción exitosa ===")
    with Transaction(cuenta):
        cuenta.saldo -= 100
        cuenta.saldo -= 200
        cuenta.nombre = "Juan"

    print(f"Después de transacción exitosa: {cuenta}")
    # saldo=700, nombre='Juan'

    print("\n=== Transacción que falla ===")
    try:
        with Transaction(cuenta):
            cuenta.saldo -= 500
            cuenta.nombre = "ERROR"
            cuenta.activa = False
            raise ValueError("Pago rechazado")
    except ValueError as e:
        print(f"Excepción capturada: {e}")

    print(f"Después de transacción fallida: {cuenta}")
    # Debe ser igual al estado antes de entrar al bloque (saldo=700, nombre='Juan')

    print("\n=== Anidado: transacción dentro de transacción ===")
    with Transaction(cuenta):
        cuenta.saldo += 1000  # depósito externo
        try:
            with Transaction(cuenta):
                cuenta.saldo -= 2000  # pago que falla
                raise ConnectionError("Banco caído")
        except ConnectionError:
            print("  Pago interno revertido")

    print(f"Estado final: {cuenta}")
    # El depósito externo persiste, el pago interno se revirtió
