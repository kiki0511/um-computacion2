#!/usr/bin/env python3
"""
Ejercicio adicional - Rate limiter con SIGALRM.

Permite como máximo N operaciones por segundo. Usa setitimer para recibir
SIGALRM cada segundo; en cada disparo resetea el contador de operaciones de
la ventana actual. Si se supera el límite dentro de una ventana, la
operación se rechaza (o se podría hacer esperar).
"""
import signal
import time


class RateLimiter:
    def __init__(self, max_por_segundo):
        self.max = max_por_segundo
        self.contador = 0

    def _reset(self, sig, frame):
        self.contador = 0

    def iniciar(self):
        signal.signal(signal.SIGALRM, self._reset)
        signal.setitimer(signal.ITIMER_REAL, 1.0, 1.0)  # cada 1 segundo

    def permitir(self):
        """Devuelve True si la operación está permitida en esta ventana."""
        if self.contador < self.max:
            self.contador += 1
            return True
        return False


def main():
    limiter = RateLimiter(max_por_segundo=5)
    limiter.iniciar()

    aceptadas = 0
    rechazadas = 0

    print("Intentando 30 operaciones lo más rápido posible "
          "(límite: 5/segundo)...")
    inicio = time.time()
    intentos = 0
    while intentos < 30:
        if limiter.permitir():
            aceptadas += 1
            print(f"  [OK] operación {aceptadas}")
            intentos += 1
        else:
            rechazadas += 1
            time.sleep(0.05)  # esperar a la próxima ventana

    print(f"\nAceptadas: {aceptadas}, rechazos: {rechazadas}, "
          f"tiempo: {time.time() - inicio:.1f}s")
    signal.setitimer(signal.ITIMER_REAL, 0)


if __name__ == "__main__":
    main()
