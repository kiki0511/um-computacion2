# Computación II — 2026
Universidad de Mendoza · Ingeniería en Informática

Repositorio personal con la resolución de las clases y trabajos prácticos de
la materia. Código en Python 3 y Docker.

## Estructura

```
um-computacion2/
├── README.md
├── clase/
│   ├── Bloque_0/              # Estudio autónomo (previo a la cursada)
│   │   ├── argparse/          # CLIs con argparse/getopt
│   │   ├── filesystem/        # Filesystem, inodos, permisos
│   │   ├── ipv6/              # IPv6: direcciones, dual-stack, getaddrinfo
│   │   └── python_avanzado/   # Context managers, decoradores, generadores
│   ├── Clase_01/              # Introducción a Docker
│   ├── Clase_02/              # Docker aplicado (volúmenes, redes, compose)
│   ├── Clase_03/              # Procesos: fork, exec, wait
│   ├── Clase_04/              # Pipes y redirección
│   ├── Clase_05/              # Señales
│   ├── Clase_06/              # mmap y memoria compartida
│   ├── Clase_07/              # Multiprocessing: fundamentos
│   ├── Clase_08/              # Multiprocessing avanzado (Pool, Manager)
│   ├── Clase_09/              # Threading (GIL, Lock, Queue, daemon threads)
│   ├── Clase_10/              # Sincronización avanzada (RLock, Semaphore, Condition, Barrier)
│   ├── Clase_11/              # Sincronización: race conditions, locks, filósofos
│   ├── Clase_12/              # Redes: fundamentos, UDP, TCP/IP, DNS
│   ├── Clase_13/              # Sockets TCP: framing, recv, errores, timeouts
│   ├── Clase_14/              # Servidores concurrentes: threads, fork, pool
│   ├── Clase_15/              # UDP: datagramas, confiabilidad, broadcast
│   ├── Clase_16/              # socketserver: mixins, estado compartido
│   ├── Clase_17/              # I/O multiplexing: select, poll, epoll, selectors
│   ├── Clase_18/              # De yield a asyncio: scheduler cooperativo
│   ├── Clase_19/              # HTTP + FastAPI
│   └── Clase_20/              # Asyncio en red: streams, gather, semáforos
├── tp1/                       # Trabajo Práctico 1
└── tp2/                       # Trabajo Práctico 2
```

Cada carpeta de clase incluye su propio `README.md` con la descripción de los
ejercicios, cómo ejecutarlos y las respuestas a las preguntas conceptuales.

## Estado de avance

| Unidad | Tema | Estado |
|--------|------|--------|
| Bloque 0 | argparse, filesystem, python avanzado, IPv6 | ✅ Completo |
| Clase 01 | Docker intro | ✅ Documentado |
| Clase 02 | Docker aplicado | ✅ Documentado |
| Clase 03 | Procesos (fork/exec/wait) | ✅ Completo |
| Clase 04 | Pipes y redirección | ✅ Completo |
| Clase 05 | Señales | ✅ Completo |
| Clase 06 | mmap y memoria compartida | ✅ Completo |
| Clase 07 | Multiprocessing fundamentos | ✅ Completo |
| Clase 08 | Multiprocessing avanzado | ✅ Completo |
| Clase 09 | Threading | ✅ Completo |
| Clase 10 | Sincronización avanzada | ✅ Completo |
| Clase 11 | Sincronización: locks, semáforos, filósofos | ✅ Completo |
| Clase 12 | Redes: fundamentos, UDP, TCP/IP | ✅ Completo |
| Clase 13 | Sockets TCP: framing, errores, timeouts | ✅ Completo |
| Clase 14 | Servidores concurrentes | ✅ Completo |
| Clase 15 | UDP | ✅ Completo |
| Clase 16 | socketserver | ✅ Completo |
| Clase 17 | I/O multiplexing | ✅ Completo |
| Clase 18 | De yield a asyncio | ✅ Completo |
| Clase 19 | HTTP + FastAPI | ✅ Completo |
| Clase 20 | Asyncio en red | ✅ Completo |
| TP1 | Monitor de procesos y threads | ✅ Aprobado |
| TP2 | — | ⏳ Pendiente de consigna |

## Ejercicios obligatorios destacados

- **Bloque 0:** `buscar.py` (mini-grep), `inspector.py`, `timer.py`, `retry.py`
- **Clase 03:** `paralelo.py` (ejecutor de comandos en paralelo)
- **Clase 04:** `minishell_redir.py` (mini-shell con `>`, `>>`, `<`)
- **Clase 05:** `servidor_signals.py` (servidor que responde a señales)
- **Clase 06:** `value_array.py` (Value/Array compartidos, race condition)
- **Clase 08:** `procesador_imagenes.py` (procesamiento paralelo con Pool)
- **Clase 09:** `descargador_paralelo.py` (pool de threads descargando URLs)
- **Clase 11:** `ej5_readers_writers.py` (Readers-Writers Lock desde cero)
- **Clase 12:** `ej6_tcp_flujo.py` (TCP como flujo vs UDP con límites de datagrama)
- **Clase 13:** `ej3_framing.py` (framing por delimitador y por prefijo de longitud)
- **Clase 14:** `ej3_descuidos_fork.py` (descriptores, zombies y cosecha de hijos)
- **Bloque 0 (IPv6):** `ej3_dual_stack.py` (servidor dual-stack y cliente con `getaddrinfo`)
- **Clase 15:** `ej3_protocolo_confiable.py` (reintentos + números de secuencia sobre UDP)
- **Clase 16:** `ej2_mixins.py` (orden de herencia, forking con `multiprocessing.Value`)
- **Clase 17:** `ej3_comparar.py` (select vs poll vs epoll/kqueue)
- **Clase 18:** `ej2_scheduler.py` (event loop cooperativo con generadores)
- **Clase 19:** `ej3_api.py` + `ej3_probar_api.py` (API de tareas con FastAPI)
- **Clase 20:** `ej3_descargas.py` (httpx asíncrono, semáforo, `return_exceptions`)

## Requisitos

- Python 3.11+ (la clase 20 usa `asyncio.timeout`)
- Docker y Docker Compose
- Clases 19 y 20: `pip install -r clase/Clase_19/requirements.txt` (fastapi, uvicorn, httpx) y `requests`
- Sistema Linux, macOS o WSL2 (varios ejercicios usan `os.fork`, señales y
  `/proc`, que son específicos de Unix)

## Cómo ejecutar

```bash
# Ejemplo: ejercicio obligatorio de la Clase 3
python3 clase/Clase_03/paralelo.py "sleep 2" "sleep 1" "echo hola"
```

Cada `README.md` de clase indica el uso específico de cada script.

---
*Computación II · Ciclo 2026*
