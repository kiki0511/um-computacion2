# Clase 04 — Pipes y Redirección

Resolución de los ejercicios prácticos de la Clase 4.

## Conceptos

Un **file descriptor** es un número entero que el SO usa para referirse a un
recurso de E/S abierto (archivo, pipe, socket). Por convención: 0 = stdin,
1 = stdout, 2 = stderr.

Un **pipe** (`os.pipe()`) es un canal unidireccional en memoria con dos
extremos: lectura y escritura. Conectado con `os.dup2()` permite redirigir la
E/S de un proceso. Un **named pipe / FIFO** (`os.mkfifo()`) es un pipe con
nombre en el filesystem, útil para comunicar procesos sin parentesco.

## Scripts

| Archivo | Ejercicio | Descripción |
|---------|-----------|-------------|
| `explorar_fds.py` | 1.2 | Lista los fds del proceso vía `/proc/<pid>/fd` |
| `redireccion_dup2.py` | 2.1 | Redirige stdout a archivo con `dup`/`dup2` |
| `separar_salidas.py` | 2.2 | Diferencia entre stdout (fd 1) y stderr (fd 2) |
| `pipe_padre_hijo.py` | 3.1 | Comunicación unidireccional por pipe |
| `pipe_bidireccional.py` | 3.2 | Dos pipes para comunicación en ambos sentidos |
| `pipeline_dos.py` | 4.1 | Implementa `cmd1 \| cmd2` con fork+dup2 |
| `pipeline_tres.py` | 4.2 | Implementa `cmd1 \| cmd2 \| cmd3` |
| **`minishell_redir.py`** | **5 (OBLIGATORIO)** | Mini-shell con `>`, `>>` y `<` |
| `mayusculas.py` | 6.1 | Filtro Unix (stdin → stdout en mayúsculas) |
| `pipeline_subprocess.py` | 6.2 | Pipeline construido con `subprocess.Popen` |
| `escritor_fifo.py` | 7.1 | Escribe a un named pipe |
| `lector_fifo.py` | 7.1 | Lee de un named pipe |
| `mi_tee.py` | adicional | `tee` casero (duplica stdin a stdout y archivos) |
| `monitor.py` | adicional | Se interpone en un pipe y reporta bytes/líneas |

## Uso rápido

```bash
python3 redireccion_dup2.py
python3 pipeline_tres.py
python3 minishell_redir.py            # shell interactiva

# filtros y pipelines
echo "hola" | python3 mayusculas.py
cat archivo | python3 monitor.py | wc -l
ls -la | python3 mi_tee.py copia.txt

# named pipe (dos terminales)
python3 escritor_fifo.py     # terminal 1
python3 lector_fifo.py       # terminal 2
```

## Notas de implementación

- **Disciplina de cierre de pipes:** cada proceso cierra el extremo que no usa,
  y el padre cierra todos los extremos antes de esperar. Si no se cierra el
  extremo de escritura, el lector nunca recibe EOF y se bloquea.
- **`minishell_redir.py` usa `shlex.split()`** en lugar de `.split()` para
  respetar comillas (`echo "hola mundo"` se parsea como un solo argumento),
  comportándose como un shell real.
- Las redirecciones se configuran en el hijo, después del `fork` y antes del
  `exec`, con `os.open()` + `os.dup2()`.

## Verificación del obligatorio (`minishell_redir.py`)

- [x] Parsea `>` para redirección de salida
- [x] Crea/trunca el archivo de salida
- [x] Redirige stdout del comando al archivo
- [x] Funciona con cualquier comando
- [x] BONUS: soporta `<` (redirección de entrada)
- [x] BONUS: soporta `>>` (append)
