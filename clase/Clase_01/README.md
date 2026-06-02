# Clase 01 — Introducción a Docker

Notas y resolución de los ejercicios prácticos de la Clase 1. Es una clase de
terminal (no hay entregables de código), así que este README documenta los
comandos ejecutados y las respuestas a las preguntas.

## Por qué Docker

Docker permite crear entornos aislados y reproducibles: si el código corre en
un contenedor, corre igual en cualquier máquina. Resuelve el clásico "funciona
en mi máquina" y es la base para que los TPs corran igual en mi equipo y en el
del docente.

## Conceptos clave

- **Imagen**: plantilla inmutable (la "receta") con el sistema de archivos,
  dependencias y configuración. No cambia.
- **Contenedor**: instancia en ejecución de una imagen. Tiene su propio estado
  (procesos, archivos modificados). De una imagen se crean muchos contenedores.
- **Contenedor vs VM**: el contenedor comparte el kernel del host (liviano,
  arranca en segundos); la VM virtualiza un equipo completo (pesada, lenta).

## Ejercicios

### Ejercicio 1 — Explorando contenedores

```bash
docker run -it ubuntu bash          # contenedor interactivo
cat /etc/os-release                 # versión de Ubuntu
whoami                              # usuario (root)
ps aux                             # procesos del contenedor
apt update && apt install -y cowsay
/usr/games/cowsay "Hola desde Docker"
exit
```

**1.2 — El contenedor es efímero.** Al volver a `docker run -it ubuntu bash`,
cowsay ya no está: cada `docker run` crea un contenedor NUEVO desde la imagen
original. Lo instalado en el contenedor anterior se perdió.

> **Pregunta:** ¿cómo lograr que cowsay esté siempre disponible? → Hay que
> construir una imagen propia (con un Dockerfile que lo instale). Se ve en la
> Clase 2.

**1.3 — Ver contenedores:**

```bash
docker ps        # contenedores corriendo
docker ps -a     # todos (incluye los detenidos)
```

Cada `docker run` dejó un contenedor distinto en la lista de `docker ps -a`.

### Ejercicio 2 — Python en Docker

```bash
docker run -it python                       # intérprete interactivo
docker run -v $(pwd):/app -w /app python python script.py   # correr un script local
```

## Comandos de referencia

| Comando | Qué hace |
|---------|----------|
| `docker run -it imagen bash` | Contenedor interactivo |
| `docker ps` / `docker ps -a` | Listar contenedores (activos / todos) |
| `docker images` | Listar imágenes locales |
| `docker rm <id>` | Eliminar un contenedor |
| `docker rmi <img>` | Eliminar una imagen |
| `docker run -v host:cont -w /app img` | Montar un directorio y fijar el workdir |

## Conclusión

Los contenedores son efímeros y se crean a partir de imágenes inmutables. Para
persistir cambios o construir entornos propios se necesitan volúmenes y
Dockerfiles, que son el tema de la Clase 2.
