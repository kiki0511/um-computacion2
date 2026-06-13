#!/usr/bin/env python3
"""
Ejercicio 4 - Clase Thread personalizada.

`ContadorHilo` hereda de `threading.Thread`. Cuenta de 1 a `limite` con una
pausa de 0.1s entre cada número y guarda el resultado (los números separados
por coma) en el atributo `resultado`.

Se lanzan 3 instancias con límites distintos; al terminar se imprime el
resultado de cada una. Como `resultado` se escribe DESPUÉS del join(), no
hace falta lock: el join() garantiza que el hilo ya terminó de escribir antes
de que el main lo lea.
"""
import threading
import time


class ContadorHilo(threading.Thread):
    def __init__(self, nombre, limite):
        super().__init__(name=nombre)
        self.limite = limite
        self.resultado = ""

    def run(self):
        numeros = []
        for i in range(1, self.limite + 1):
            numeros.append(str(i))
            time.sleep(0.1)
        self.resultado = ", ".join(numeros)


def main():
    hilos = [
        ContadorHilo(f"Contador-{i}", limite)
        for i, limite in enumerate([5, 8, 3], 1)
    ]

    for h in hilos:
        h.start()
    for h in hilos:
        h.join()

    for h in hilos:
        print(f"[{h.name}] resultado: {h.resultado}")


if __name__ == "__main__":
    main()
