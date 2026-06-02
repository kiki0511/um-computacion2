# Clase 06 — mmap y Memoria Compartida

Resolución de los ejercicios prácticos de la Clase 6.

## Conceptos

**mmap** mapea un archivo (o memoria anónima) en el espacio de direcciones
del proceso, accesible como un `bytearray`. Evita copias kernel↔usuario y
permite compartir memoria entre procesos.

Formas de compartir memoria vistas:
- `mmap.mmap(fd, 0)` sobre un **archivo** → cambios persisten en disco.
- `mmap.mmap(-1, n)` **anónimo** → heredado por el hijo tras `fork()`.
- `multiprocessing.Value` / `Array` → objetos compartidos de tipo C.
- `multiprocessing.shared_memory.SharedMemory` / `ShareableList` → bloque con
  nombre, accesible por procesos no emparentados.

Cuando varios procesos escriben sin sincronización aparece la **race
condition**: operaciones como `x += 1` no son atómicas (leer-sumar-escribir),
así que se pierden actualizaciones. La solución (un `Lock`) se ve más adelante.

## Scripts

| Archivo | Ejercicio | Descripción |
|---------|-----------|-------------|
| `mmap_archivo.py` | 1 | mmap sobre archivo: leer, buscar, modificar + tarea de reemplazo |
| `mmap_binario.py` | 2 | `struct` sobre mmap: enteros + tarea de registros `i f 20s` |
| `mmap_anonimo.py` | 3 | mmap anónimo heredado por fork + tarea suma por rangos |
| `mmap_multiprocessing.py` | 4 | mmap respaldado por archivo con `Process` |
| **`value_array.py`** | **5 (OBLIGATORIO)** | `Value` (race condition) + `Array` (cálculo paralelo) + tarea sin() |
| `shared_memory_demo.py` | 6 | `SharedMemory` productor/consumidor + `ShareableList` |
| `banco.py` | síntesis | Banco con cuentas compartidas (race condition + log) |
| `mmap_vs_lectura.py` | adicional | mmap vs lectura secuencial sobre archivo de 10 MB |
| `chat_shared_memory.py` | adicional | Chat por turnos entre 2 procesos vía SharedMemory |
| `monitor_temperatura.py` | adicional | N sensores escriben en Array, un monitor promedia |

## El obligatorio: `value_array.py`

```bash
python3 value_array.py
```

Verificación:

- [x] Crea un `Value` compartido y demuestra la race condition
- [x] Crea un `Array` compartido y divide el trabajo entre procesos
- [x] Verifica los resultados y reporta errores
- [x] Muestra la diferencia entre el valor esperado y el obtenido

En 5.1 con 4 procesos × 100 000 incrementos el resultado obtenido es muy
inferior a 400 000 (cientos de miles de incrementos perdidos), evidenciando
la falta de atomicidad.

## Notas

- Casi todos los scripts terminan solos. `chat_shared_memory.py` y
  `monitor_temperatura.py` coordinan varios procesos pero también finalizan
  por sí mismos.
- `banco.py` usa `TRANSFERENCIAS_POR_PROCESO = 10000` para que la race
  condition sea evidente; ejecutándolo varias veces el total final varía.
- `SharedMemory` y `ShareableList` requieren `unlink()` al final para liberar
  el bloque del sistema (ya está contemplado en el código).
