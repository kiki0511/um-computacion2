"""
Recursos compartidos que viven lo mismo que el servidor.

- cliente_http: un único httpx.AsyncClient para todas las descargas. Reusar
  el cliente reusa conexiones (keep-alive) y respeta un tope global de
  conexiones abiertas, en vez de abrir un cliente por tarea.
- executor: ProcessPoolExecutor para las tareas CPU-bound.

Se crean en el lifespan de main.py (arranque) y se cierran ahí mismo
(apagado), así ninguno queda abierto al terminar.
"""

from concurrent.futures import ProcessPoolExecutor

import httpx


class Recursos:
    def __init__(self) -> None:
        self.cliente_http: httpx.AsyncClient | None = None
        self.executor: ProcessPoolExecutor | None = None


recursos = Recursos()
