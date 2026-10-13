"""
Configuración del sistema, leída de variables de entorno.

Se configura desde docker-compose.yml sin tocar el código.
"""

import os

# Cantidad de workers (corrutinas) que consumen de la cola
N_WORKERS = int(os.getenv("N_WORKERS", "4"))

# Timeout por defecto de cada tarea, en segundos (se puede pisar por tarea)
TIMEOUT_DEFAULT = float(os.getenv("TIMEOUT_DEFAULT", "60"))

# Puerto donde escucha la API
PUERTO = int(os.getenv("PUERTO", "8000"))
