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
│   │   └── python_avanzado/   # Context managers, decoradores, generadores
│   ├── Clase_01/              # Introducción a Docker
│   ├── Clase_02/              # Docker aplicado (volúmenes, redes, compose)
│   ├── Clase_03/              # Procesos: fork, exec, wait
│   ├── Clase_04/              # Pipes y redirección
│   ├── Clase_05/              # Señales
│   ├── Clase_06/              # mmap y memoria compartida
│   ├── Clase_07/              # Multiprocessing: fundamentos
│   └── Clase_08/              # Multiprocessing avanzado (Pool, Manager)
├── tp1/                       # Trabajo Práctico 1
└── tp2/                       # Trabajo Práctico 2
```

Cada carpeta de clase incluye su propio `README.md` con la descripción de los
ejercicios, cómo ejecutarlos y las respuestas a las preguntas conceptuales.

## Estado de avance

| Unidad | Tema | Estado |
|--------|------|--------|
| Bloque 0 | argparse, filesystem, python avanzado | ✅ Completo |
| Clase 01 | Docker intro | ✅ Documentado |
| Clase 02 | Docker aplicado | ✅ Documentado |
| Clase 03 | Procesos (fork/exec/wait) | ✅ Completo |
| Clase 04 | Pipes y redirección | ✅ Completo |
| Clase 05 | Señales | ✅ Completo |
| Clase 06 | mmap y memoria compartida | ✅ Completo |
| Clase 07 | Multiprocessing fundamentos | ✅ Completo |
| Clase 08 | Multiprocessing avanzado | ✅ Completo |
| TP1 | — | ⏳ Pendiente de consigna |
| TP2 | — | ⏳ Pendiente de consigna |

## Ejercicios obligatorios destacados

- **Bloque 0:** `buscar.py` (mini-grep), `inspector.py`, `timer.py`, `retry.py`
- **Clase 03:** `paralelo.py` (ejecutor de comandos en paralelo)
- **Clase 04:** `minishell_redir.py` (mini-shell con `>`, `>>`, `<`)
- **Clase 05:** `servidor_signals.py` (servidor que responde a señales)
- **Clase 06:** `value_array.py` (Value/Array compartidos, race condition)
- **Clase 08:** `procesador_imagenes.py` (procesamiento paralelo con Pool)

## Requisitos

- Python 3.10+
- Docker y Docker Compose
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
