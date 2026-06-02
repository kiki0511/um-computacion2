#!/usr/bin/env python3
"""
Ejercicio 2.2 - Shutdown limpio con SIGTERM.

Patrón clásico de aplicaciones de larga duración: el manejador de señal NO
hace el trabajo pesado, solo baja una bandera (self.ejecutando = False). El
loop principal detecta el cambio, sale ordenadamente y libera recursos en
orden inverso al que los adquirió.

Probar:
    python3 shutdown_limpio.py     # en una terminal
    kill <pid>                     # en otra -> shutdown limpio
"""
import signal
import time
import os


class Aplicacion:
    def __init__(self):
        self.ejecutando = True
        self.recursos = []

        signal.signal(signal.SIGTERM, self.shutdown)
        signal.signal(signal.SIGINT, self.shutdown)

    def shutdown(self, sig, frame):
        nombre = signal.Signals(sig).name
        print(f"\nRecibí {nombre}, cerrando...")
        self.ejecutando = False

    def adquirir_recurso(self, nombre):
        print(f"Adquiriendo recurso: {nombre}")
        self.recursos.append(nombre)

    def liberar_recursos(self):
        for recurso in reversed(self.recursos):
            print(f"Liberando recurso: {recurso}")
            time.sleep(0.3)
        self.recursos.clear()

    def run(self):
        print(f"PID: {os.getpid()}")
        print("Enviá 'kill <pid>' para terminar limpiamente")

        self.adquirir_recurso("base_de_datos")
        self.adquirir_recurso("archivo_log")
        self.adquirir_recurso("conexion_red")

        while self.ejecutando:
            print("Trabajando...")
            time.sleep(1)

        self.liberar_recursos()
        print("Aplicación terminada correctamente")


if __name__ == "__main__":
    Aplicacion().run()
