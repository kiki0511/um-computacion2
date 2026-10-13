FROM python:3.11-slim

WORKDIR /tp2

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/

EXPOSE 8000

# Forma exec (lista JSON): Python queda como PID 1 y recibe el SIGTERM de
# `docker compose stop` directamente. Con la forma shell, lo recibiría /bin/sh
# y no lo reenviaría, así que no habría apagado ordenado.
CMD ["python", "-m", "app.main"]
