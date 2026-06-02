# Clase 03 — Procesos (fork, exec, wait)

Resolución de los ejercicios prácticos de la Clase 3.

## Ejercicio 1 — Exploración desde la terminal (sin código)

- **1.1 `echo $$` / `ps -p $$`**: `$$` es el PID del shell actual; `ps -p $$`
  muestra que ese PID corresponde a `bash` (o el shell en uso).
- **1.2 Jerarquía (`pstree -p`, `ps -ef`)**: siguiendo la columna PPID desde
  el shell se llega siempre a PID 1 (`init`/`systemd`), el ancestro de todos
  los procesos. El padre del shell suele ser el emulador de terminal.
- **1.3 `sleep 300 &`**: el proceso aparece con estado `S` (sleeping) y ~0% de
  CPU porque no hace trabajo, solo espera. Se mata con `kill <PID>`.
- **1.4 Zombie**: el hijo hace `_exit(0)` y el padre duerme sin hacer `wait()`,
  así que el hijo queda en estado `Z` (zombie) hasta que el padre lo recoge o
  muere. Un zombie es un proceso terminado cuyo código de salida todavía no fue
  leído por el padre.

## Scripts

| Archivo | Ejercicio | Descripción |
|---------|-----------|-------------|
| `fork_basico.py` | 2.1 | Primer `fork()`: el código corre en padre e hijo |
| `fork_wait.py` | 2.2 | `fork()` + `wait()` y lectura del código de salida |
| `multiples_hijos.py` | 2.3 | 3 hijos en paralelo; terminan por duración, no por orden |
| `fork_exec.py` | 3.1 | `fork()` + `execlp()` para correr `ls` |
| `ejecutar.py` | 3.2 | Función reutilizable `ejecutar(cmd, args)` (fork+exec+wait) |
| `minishell.py` | 4 | Mini-shell: REPL + comandos externos + `cd`/`exit` internos |
| **`paralelo.py`** | **5 (OBLIGATORIO)** | Ejecuta comandos en paralelo y reporta tiempo total |
| `paralelo_subprocess.py` | 6 | Misma idea con `subprocess` (comparación) |
| `contar_procesos.py` | 6.1 | Cuenta procesos contando `/proc/<n>` |
| `info_proceso.py` | 6.2 | Info de un PID desde `/proc/<PID>/` |
| `mi_pstree.py` | 6.3 | Árbol de procesos propio (PID → PPid) |

## Uso rápido

```bash
python3 fork_basico.py
python3 paralelo.py "sleep 2" "sleep 1" "echo test"
python3 info_proceso.py 1
python3 mi_pstree.py
```

## Preguntas conceptuales

- **2.2 — ¿`_exit(42)` vs `_exit(0)`?** Solo cambia el código de salida que el
  padre lee. Es el canal por el que el hijo le dice al padre cómo le fue.
- **4.3 — ¿Por qué `cd` es interno?** Cada proceso tiene su propio directorio
  de trabajo. Si `cd` fuera externo, correría en un hijo (fork+exec); ese hijo
  cambiaría su directorio y al morir el cambio se perdería. El shell debe llamar
  `os.chdir()` en su propio proceso.
- **6 — fork/exec vs subprocess.** `subprocess` es más simple y es lo que se usa
  en la práctica; `fork/exec` da control de bajo nivel y sirve para entender qué
  hace `subprocess` por debajo.

## Verificación del obligatorio (`paralelo.py`)

- [x] Ejecuta comandos en paralelo (no secuencial)
- [x] Muestra PID al iniciar cada comando
- [x] Muestra cuando termina cada comando
- [x] Reporta código de salida de cada comando
- [x] Tiempo total < suma de tiempos individuales
- [x] Maneja comandos que fallan
