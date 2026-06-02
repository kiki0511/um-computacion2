# Clase 02 — Docker Aplicado

Notas y resolución de los ejercicios prácticos de la Clase 2. Como la Clase 1,
es de terminal: este README documenta comandos, ejemplos y respuestas.

## Temas

- **Volúmenes**: persistir datos y compartir archivos con el host
- **Redes**: comunicación entre contenedores
- **Dockerfile**: construir imágenes propias
- **Docker Compose**: orquestar varios contenedores como una unidad

## Volúmenes

- **Bind mount**: conecta un directorio del host con uno del contenedor; los
  cambios se reflejan al instante. Ideal para desarrollo.
  ```bash
  docker run -v $(pwd):/app -w /app python python script.py
  ```
- **Named volume**: volumen gestionado por Docker, no atado a una ruta del host.
  Ideal para datos de bases de datos.
  ```bash
  docker volume create datos
  docker run -v datos:/var/lib/datos imagen
  docker volume inspect datos
  ```

**Ejercicio 1 (contador):** con el volumen, `contador.txt` persiste entre
ejecuciones y el contador incrementa. Si se quita el `-v` de datos, cada corrida
arranca de cero (el dato vive solo dentro del contenedor efímero). Con un named
volume el archivo no se ve directo en el host porque Docker lo guarda en su
propio área (`/var/lib/docker/volumes/...`).

## Redes

```bash
docker network create mi-red
docker run -d --name web --network mi-red imagen
docker run -it --network mi-red imagen ping web   # se resuelven por nombre
```

Los contenedores en la misma red se encuentran por su nombre de servicio
(DNS interno de Docker).

## Dockerfile

Archivo de texto con instrucciones para construir una imagen:

```dockerfile
FROM python:3.11-slim          # imagen base
WORKDIR /app                   # directorio de trabajo
COPY requirements.txt .        # copiar dependencias
RUN pip install -r requirements.txt
COPY . .                       # copiar el resto del código
CMD ["python", "app.py"]       # comando por defecto
```

```bash
docker build -t mi-app .       # construir la imagen
docker run mi-app              # correrla
```

Instrucciones principales: `FROM` (base, obligatoria y primera), `WORKDIR`,
`COPY`, `RUN` (ejecuta en build), `CMD`/`ENTRYPOINT` (comando al arrancar),
`EXPOSE` (metadata de puerto; no abre nada por sí solo, el mapeo real es `-p`).

## Docker Compose

Define múltiples servicios en un `docker-compose.yml`:

```yaml
services:
  app:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - .:/app
  db:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: secreto
```

```bash
docker compose up          # levantar todo
docker compose up -d       # en segundo plano
docker compose logs -f app # seguir logs de un servicio
docker compose down        # bajar todo
```

> Nota: el comando actual es `docker compose` (subcomando). El viejo
> `docker-compose` (con guión) está deprecado pero funciona igual.

## Comandos de referencia

| Comando | Qué hace |
|---------|----------|
| `docker build -t nombre .` | Construir imagen desde el Dockerfile |
| `docker volume create / inspect` | Crear / inspeccionar volúmenes |
| `docker network create` | Crear una red |
| `docker compose up -d` / `down` | Levantar / bajar servicios |
| `docker compose logs -f` | Seguir logs |

## Conclusión

Con volúmenes (persistencia), redes (comunicación), Dockerfile (imágenes
propias) y Compose (orquestación) ya se puede armar un entorno de desarrollo
completo en Docker, que es lo que se usa para el resto de la materia y los TPs.
