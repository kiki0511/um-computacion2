"""
Configuración del sistema, leída de variables de entorno.

Se configura desde docker-compose.yml sin tocar el código.
"""

import os


def _bool(nombre: str, default: bool) -> bool:
    valor = os.getenv(nombre)
    if valor is None:
        return default
    return valor.strip().lower() in ("1", "true", "si", "sí", "yes")


# Cantidad de workers (corrutinas) que consumen de la cola
N_WORKERS = int(os.getenv("N_WORKERS", "4"))

# Timeout por defecto de cada tarea, en segundos (se puede pisar por tarea)
TIMEOUT_DEFAULT = float(os.getenv("TIMEOUT_DEFAULT", "60"))

# Puerto donde escucha la API
PUERTO = int(os.getenv("PUERTO", "8000"))

# --- hashear (CPU-bound) ---
# True: el hash corre en un ProcessPoolExecutor (lo correcto).
# False: corre directo en el event loop (lo INCORRECTO, solo para la medición 2).
USAR_EXECUTOR = _bool("USAR_EXECUTOR", True)
# Procesos del pool para tareas CPU-bound
N_PROCESOS = int(os.getenv("N_PROCESOS", str(os.cpu_count() or 2)))
# Iteraciones de SHA-256 por bloque enviado al executor (ver tareas/hashear.py)
BLOQUE_HASH = int(os.getenv("BLOQUE_HASH", "200000"))
# Tope de iteraciones que se aceptan en una tarea
MAX_ITERACIONES = int(os.getenv("MAX_ITERACIONES", "100000000"))

# --- descargar (I/O-bound) ---
MAX_URLS = int(os.getenv("MAX_URLS", "100"))
# Timeout de cada request HTTP individual (el de la tarea entera es aparte)
TIMEOUT_HTTP = float(os.getenv("TIMEOUT_HTTP", "15"))

# --- apagado ordenado ---
# Segundos máximos que se espera a las tareas en curso antes de cancelarlas.
# Tiene que ser menor que stop_grace_period del compose, o Docker mata el
# proceso con SIGKILL antes de que se vuelque el estado.
TIMEOUT_APAGADO = float(os.getenv("TIMEOUT_APAGADO", "20"))
# Carpeta donde se guardan los estado_<timestamp>.json
DIR_ESTADO = os.getenv("DIR_ESTADO", "estados")
