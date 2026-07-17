# El monitor no usa ninguna librería externa (curses es stdlib), así que
# no hace falta una imagen con build tools -- slim alcanza.
FROM python:3.12-slim

# El intérprete de python:slim ya viene compilado con soporte para el
# módulo _curses, pero ese módulo igual enlaza dinámicamente contra la
# librería de ncurses del sistema operativo en tiempo de ejecución --
# hay que instalarla aparte, si no "import curses" falla al arrancar.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libncursesw6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Se copia requirements.txt primero (aunque esté vacío) para aprovechar
# el cache de capas de Docker: si más adelante se agrega una dependencia,
# esta capa se reconstruye sin tener que volver a copiar todo el código.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.json .
COPY src/ src/

CMD ["python3", "src/main.py"]
