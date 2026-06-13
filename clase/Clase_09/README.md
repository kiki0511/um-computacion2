# Clase 09 — Threading

Resolución de los ejercicios prácticos de la Clase 9: Threads - Concurrencia
dentro del Proceso.

## Conceptos

Hasta ahora (Clases 03-08) usamos `multiprocessing`: procesos separados, cada
uno con su propia memoria, que se comunican por `Queue`, `Pipe` o memoria
compartida. Los **threads** (módulo `threading`) son otra forma de hacer
varias cosas "a la vez", pero dentro del **mismo proceso**: comparten memoria,
file descriptors, directorio de trabajo y handlers de señales.

| Característica    | Proceso             | Hilo               |
|--------------------|---------------------|--------------------|
| Memoria            | Separada (copia)    | Compartida         |
| Comunicación       | IPC (pipes, colas)  | Variables directas |
| Costo de creación  | Alto                | Bajo               |
| Aislamiento        | Alto                | Bajo               |
| Paralelismo real   | Sí (multi-core)     | Limitado por GIL   |

### El GIL (Global Interpreter Lock)

El GIL es un mutex global que impide que dos threads ejecuten bytecode de
Python al mismo tiempo. Por eso:

| Tipo de tarea          | ¿Threads ayudan? | Alternativa     |
|-------------------------|------------------|-----------------|
| I/O-bound (red, disco)  | Sí               | (o `asyncio`)   |
| CPU-bound (cálculos)    | No (con GIL)     | `multiprocessing` |
| Mixta                   | Depende          | Evaluar caso a caso |

Esto se ve empíricamente en `descargas_secuencial_vs_threading.py` (I/O-bound,
threading gana ~5x) vs `gil_cpu_bound.py` (CPU-bound, threading no mejora).

> **Nota sobre Python 3.13+**: con la PEP 703, CPython tiene un build
> *free-threaded* (sin GIL) experimental desde 3.13 y "soportado" desde 3.14.
> En ese build los threads SÍ escalan en CPU-bound, a costa de ~5-10% más
> lento en código single-threaded. Sigue sin ser el default. Lo que se ve en
> esta clase (GIL clásico) es el comportamiento por defecto de CPython hoy.

### Race conditions y `Lock`

Cuando varios threads leen y escriben la misma variable sin coordinación,
puede haber una "ventana de vulnerabilidad" entre leer el valor y escribirlo
de vuelta: dos threads pueden leer el mismo valor viejo y pisarse el
resultado. `threading.Lock()` (usado con `with lock:`) hace que esa sección
sea **atómica**: solo un thread a la vez puede estar dentro.

### `threading.local()`

Permite que cada thread tenga su propia copia de una variable, accedida con
el mismo nombre desde cualquier función, sin pasarla como parámetro y sin
necesidad de locks (cada thread solo ve y modifica SU copia).

### `queue.Queue`

Cola thread-safe (ya trae su propio Lock internamente). Patrón típico
productor/consumidor: N workers hacen `q.get()` en loop hasta recibir un
centinela (`None`), uno por worker, que les indica que no hay más trabajo.
`q.join()` bloquea hasta que todos los `task_done()` de los `put()`
anteriores fueron llamados.

### Daemon threads

Un thread con `daemon=True` no impide que el proceso termine: cuando el
`main` termina, los threads daemon mueren con él, sin esperar a que acaben su
trabajo. Sin `daemon=True`, Python espera a que TODOS los threads no-daemon
terminen antes de salir (si hacen un loop infinito, el programa nunca
termina solo).

## Scripts

| Archivo | Ejercicio | Descripción |
|---------|-----------|-------------|
| `primer_hilo.py` | 1 | 3 hilos imprimen números 1-5 con `join()` |
| `descargas_secuencial_vs_threading.py` | 2 | I/O-bound: secuencial vs threading (~5x mejora) |
| `gil_cpu_bound.py` | 3 | CPU-bound: secuencial vs threads vs procesos (GIL en acción) |
| `contador_hilo.py` | 4 | Clase `ContadorHilo(threading.Thread)` |
| `race_condition_lock.py` | 5 | Saldo bancario: race condition sin Lock vs corregido con Lock |
| `hilos_daemon.py` | 6 | Hilo daemon que muere con el proceso |
| `productor_consumidor_queue.py` | 7 | 4 workers + `queue.Queue`, 20 "imágenes" |
| `threading_local.py` | 8 | Contexto por hilo con `threading.local()` |
| **`descargador_paralelo.py`** | **9 (OBLIGATORIO)** | Pool de 4 threads descargando URLs con `queue.Queue` |
| `monitor_sistema_simple.py` | adicional | 3 threads daemon imprimiendo métricas a distinto ritmo |
| `chat_multihilo.py` | adicional | Varios productores + 1 consumidor sobre `queue.Queue` |

## Uso

```bash
python3 primer_hilo.py
python3 descargas_secuencial_vs_threading.py
python3 gil_cpu_bound.py
python3 contador_hilo.py
python3 race_condition_lock.py
python3 hilos_daemon.py
python3 productor_consumidor_queue.py
python3 threading_local.py
python3 descargador_paralelo.py
python3 monitor_sistema_simple.py
python3 chat_multihilo.py
```

## El obligatorio: `descargador_paralelo.py`

```bash
python3 descargador_paralelo.py
```

Verificación:

- [x] Usa un pool fijo de 4 workers (no un thread por URL)
- [x] Descarga las URLs en paralelo con `queue.Queue`
- [x] Maneja errores de red sin crashear (incluye una URL inválida a propósito)
- [x] Muestra estadísticas finales: descargas exitosas, bytes totales, tiempo total

Requiere conexión a internet (descarga páginas reales). Si se corre sin
conexión, todas las URLs van a fallar con error de red, pero el script no
debería crashear: ese es justo el caso que cubre el `except`.

## Notas

- `gil_cpu_bound.py` usa `N = 2_000_000`; en máquinas más rápidas puede no
  notarse mucha diferencia entre secuencial y threads porque ambos son
  rápidos. Lo importante es que threads **no sea sustancialmente más rápido**
  que secuencial (a diferencia de procesos, que sí debería acercarse al
  speedup esperado en una máquina con varios cores).
- `race_condition_lock.py`: la versión insegura puede o no mostrar saldo
  negativo según el scheduling del sistema operativo en esa corrida —
  por eso el script avisa ambos casos. La versión con Lock siempre da $0.
- `monitor_sistema_simple.py` y `chat_multihilo.py` terminan solos.
- Todos los scripts usan el guard `if __name__ == "__main__":`.
