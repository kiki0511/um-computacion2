# Clase 08 — Multiprocessing Avanzado

Resolución de los ejercicios prácticos de la Clase 8.

## Conceptos

Esta clase cubre las herramientas avanzadas de `multiprocessing`:

- **Pool**: mantiene un conjunto fijo de workers reutilizables. Métodos:
  `map` / `map_async` (todos los resultados, en orden), `imap` (iterador lazy
  ordenado), `imap_unordered` (lazy, orden de finalización), `starmap`
  (múltiples argumentos), `apply_async` (una tarea, devuelve un Future).
- **Memoria compartida**: `Value`/`Array` (tipos C, memoria directa) con
  `get_lock()` para evitar race conditions; `Manager` (dict/list compartidos
  vía un proceso servidor, más flexible pero más lento).
- **Patrones**: Map-Reduce y Pipeline de procesos.

## Scripts

| Archivo | Ejercicio | Descripción |
|---------|-----------|-------------|
| `pool_metodos.py` | 1 | map / imap / imap_unordered / starmap / apply_async |
| `secuencial_vs_paralelo.py` | 2 | Speedup CPU-bound con 1/2/4/8 workers |
| `memoria_compartida.py` | 3 | `Value` con `get_lock()` + `Array` particionado |
| `manager_estructuras.py` | 4 | `Manager().dict()` y `.list()` compartidos |
| **`procesador_imagenes.py`** | **5 (OBLIGATORIO)** | Filtro blur con `Pool.map`, secuencial vs paralelo |
| `map_reduce.py` | 6 | Conteo de palabras Map-Reduce |
| `pipeline_procesos.py` | 7 | Pipeline de 3 etapas con `Queue` |
| `montecarlo_pi.py` | adicional | Estimación de π con Monte Carlo paralelo |
| `merge_sort_paralelo.py` | adicional | Merge sort con Pool + merge final |
| `procesador_archivos.py` | adicional | Procesa archivos de una carpeta en paralelo |

## El obligatorio: `procesador_imagenes.py`

```bash
python3 procesador_imagenes.py
```

Verificación:

- [x] Crea múltiples imágenes (matrices) aleatorias
- [x] Aplica el filtro blur 3x3 a cada imagen
- [x] Usa `Pool.map` para el procesamiento paralelo
- [x] Muestra tiempo secuencial vs paralelo
- [x] Calcula speedup
- [x] Usa el guard `if __name__ == "__main__"`

## Nota sobre el speedup

El beneficio del paralelismo solo se observa en máquinas con **varios núcleos
físicos**. En un equipo con 1 core disponible (por ejemplo, un contenedor
limitado), el speedup será menor a 1x porque solo hay overhead y no hay
ejecución realmente simultánea. En una notebook moderna (4–8 núcleos) los
ejercicios 2 y 5 muestran speedup > 1x. Esto se ve también en el ejercicio 2,
que tabula el tiempo según la cantidad de workers.

## Notas

- Todos los scripts terminan solos.
- `pool_metodos.py` usa duraciones aleatorias para que se note la diferencia
  entre `imap` (ordenado) e `imap_unordered` (orden de finalización).
- `procesador_archivos.py` genera archivos de ejemplo en `/tmp` si no se le
  pasa una carpeta como argumento.
