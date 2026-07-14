#!/usr/bin/env python3
"""
senales.py - Manejo de señales del proceso principal del monitor, con el
patrón self-pipe.

Por qué self-pipe: un signal handler de Python corre en el thread
principal en el próximo "punto seguro" del intérprete -- no es tan crudo
como un handler de C, pero igual puede interrumpir el loop principal en
cualquier momento inconveniente (a mitad de una escritura al
Manager.dict, por ejemplo). La forma estándar de coordinar señales con un
loop que espera con select()/poll() es que el handler NO haga trabajo de
verdad: solo escribe un byte a un pipe (os.write es async-signal-safe).
El loop principal espera con select() sobre el extremo de lectura del
pipe además de su timeout normal de refresco; cuando hay datos, recién
ahí -- en código normal, fuera del handler -- se decide qué hacer según
qué señal llegó.
"""
import os
import signal


class ManejadorSenales:
    """
    Agrupa el pipe y el registro de handlers. Se instancia una sola vez
    en main.py, antes de arrancar el loop principal.
    """

    def __init__(self):
        self._r, self._w = os.pipe()
        os.set_blocking(self._r, False)  # el loop lo lee con select(), no bloqueante

    def fd_lectura(self):
        """FD de lectura del pipe, para pasarle a select.select()."""
        return self._r

    def _handler(self, signum, frame):
        # Único trabajo permitido dentro de un signal handler async-signal
        # -safe: escribir un byte identificando qué señal llegó. Nada de
        # tocar el Manager.dict, abrir archivos ni loguear -- eso se hace
        # afuera, en el loop principal, después de leer el pipe.
        try:
            os.write(self._w, bytes([signum]))
        except OSError:
            pass  # pipe lleno (no debería pasar con señales aisladas); se ignora

    def registrar(self, *signums):
        """Instala self._handler para cada señal en signums."""
        for signum in signums:
            signal.signal(signum, self._handler)

    def leer_pendientes(self):
        """
        Drena todo lo que haya en el pipe y devuelve el SET de señales
        recibidas desde la última lectura. Se llama después de que
        select() indica que hay datos para leer.

        Nota: si la misma señal llega dos veces antes de drenar el pipe,
        se colapsa a una sola entrada en el set -- no se pierde
        información relevante, porque las señales POSIX no-realtime
        tampoco se encolan (dos SIGUSR1 seguidas y no atendidas a tiempo
        ya se comportan como una sola a nivel del kernel).
        """
        pendientes = set()
        try:
            datos = os.read(self._r, 4096)
            pendientes.update(datos)
        except BlockingIOError:
            pass
        return pendientes
