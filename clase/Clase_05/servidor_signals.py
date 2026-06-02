#!/usr/bin/env python3
"""
Ejercicio 5 (OBLIGATORIO) - Servidor que responde a señales.

Uso:
    python3 servidor_signals.py

Señales soportadas (enviar desde otra terminal con kill):
    kill -HUP  <pid>  -> Recargar configuración
    kill -USR1 <pid>  -> Mostrar estadísticas
    kill -USR2 <pid>  -> Rotar logs (simulado)
    kill       <pid>  -> Shutdown limpio (SIGTERM)
    Ctrl+C            -> Shutdown limpio (SIGINT)

Patrón: los manejadores hacen lo mínimo (bajar bandera / imprimir / ajustar
estado). El trabajo real ocurre en el loop run(), que sigue procesando
"requests" hasta que self.ejecutando pasa a False.
"""
import signal
import time
import os


class Servidor:
    def __init__(self):
        self.ejecutando = True
        self.config = {"max_conexiones": 100, "timeout": 30}
        self.stats = {"requests": 0, "errores": 0, "inicio": time.time()}
        self._registrar_manejadores()

    def _registrar_manejadores(self):
        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGHUP, self._reload_config)
        signal.signal(signal.SIGUSR1, self._mostrar_stats)
        signal.signal(signal.SIGUSR2, self._rotar_logs)

    def _shutdown(self, sig, frame):
        nombre = signal.Signals(sig).name
        print(f"\n[{nombre}] Iniciando shutdown...")
        self.ejecutando = False

    def _reload_config(self, sig, frame):
        print("\n[SIGHUP] Recargando configuración...")
        self.config["max_conexiones"] += 10
        self.config["recargado"] = time.ctime()
        print(f"[SIGHUP] Nueva config: {self.config}")

    def _mostrar_stats(self, sig, frame):
        uptime = time.time() - self.stats["inicio"]
        print("\n[SIGUSR1] === Estadísticas ===")
        print(f"  Uptime: {uptime:.1f}s")
        print(f"  Requests: {self.stats['requests']}")
        print(f"  Errores: {self.stats['errores']}")
        print(f"  Config: {self.config}")

    def _rotar_logs(self, sig, frame):
        print("\n[SIGUSR2] Rotando logs...")
        print(f"[SIGUSR2] Logs rotados a server.log.{int(time.time())}")

    def procesar_request(self):
        """Simula procesamiento de una request."""
        self.stats["requests"] += 1
        time.sleep(0.1)  # simular trabajo (y no quemar CPU)
        if self.stats["requests"] % 10 == 0:
            self.stats["errores"] += 1

    def run(self):
        pid = os.getpid()
        print(f"Servidor iniciado (PID {pid})")
        print("Comandos disponibles:")
        print(f"  kill -HUP {pid}   -> Recargar config")
        print(f"  kill -USR1 {pid}  -> Ver stats")
        print(f"  kill -USR2 {pid}  -> Rotar logs")
        print(f"  kill {pid}        -> Shutdown")
        print()

        while self.ejecutando:
            self.procesar_request()

        print("Realizando cleanup...")
        time.sleep(0.5)
        print(f"Servidor terminado. Requests procesadas: "
              f"{self.stats['requests']}")


if __name__ == "__main__":
    Servidor().run()
