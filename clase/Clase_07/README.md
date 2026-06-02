# Clase 07 — Multiprocessing: Fundamentos

Resolución de los ejercicios de la Clase 7.

## Conceptos

`multiprocessing` es la abstracción de alto nivel de Python para crear
procesos. Reemplaza el `os.fork()` manual de las clases anteriores por una
API portable (Linux/macOS/Windows) con `Process`, `Queue`, `Pipe`,
sincronización y manejo automático de zombies.

Por debajo, en Linux, sigue usando `fork()`; entender lo de bajo nivel ayuda
a saber qué hace y por qué a veces se rompe.

Detalle importante: el guard `if __name__ == "__main__":` es obligatorio,
porque con el método `spawn` (default en macOS/Windows) el hijo re-importa el
módulo y sin el guard crearía procesos infinitamente.

## Scripts

| Archivo | Ejercicio | Descripción |
|---------|-----------|-------------|
| `primer_process.py` | 1 | Primer `Process` vs `os.fork()`: qué pasos se ahorran |
| `cinco_workers.py` | 2 | 5 workers en paralelo + tiempo total |
| `productor_consumidor.py` | 3 | Productor/consumidor con `Queue` y centinela |
| `pipe_pingpong.py` | 4 | Ping-pong de 5 mensajes con `Pipe()` bidireccional |
| `fork_vs_spawn.py` | 5 | Benchmark: crear 100 procesos con `fork` vs `spawn` |

## Uso

```bash
python3 primer_process.py
python3 cinco_workers.py
python3 productor_consumidor.py
python3 pipe_pingpong.py
python3 fork_vs_spawn.py
```

## Resultados destacados

- **Ej 2:** el tiempo total ≈ el del worker más lento (corren en paralelo),
  no la suma de los 5.
- **Ej 5:** `fork` es órdenes de magnitud más rápido que `spawn` (en una
  corrida típica: ~0.2 s vs ~7 s para 100 procesos), porque `spawn` reinicia
  el intérprete y re-importa el módulo en cada hijo. `fork` no está
  disponible en Windows; el script lo detecta y lo omite si falta.

## Notas

- Todos los scripts terminan solos.
- `Queue` y `Pipe` serializan los objetos con pickle, por eso se pueden
  enviar strings, tuplas, dicts, etc. entre procesos.
