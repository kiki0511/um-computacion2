# Clase 10 — Sincronización Avanzada

Resolución de los ejercicios prácticos de la Clase 11: Sincronización
Avanzada - Coordinando la Concurrencia.

## Conceptos

En la Clase 09 vimos `Lock` básico para evitar race conditions. Esta clase
profundiza en las primitivas de `threading` para coordinar hilos:

| Primitivo | Uso principal | Comportamiento |
|-----------|---------------|----------------|
| `Lock` | Exclusión mutua básica | Un thread a la vez |
| `RLock` | Exclusión mutua reentrante | El mismo thread puede readquirirlo |
| `Semaphore` | Limitar acceso concurrente | N threads simultáneos |
| `Condition` | Esperar por una condición | patrón `wait`/`notify` |
| `Event` | Señalización simple | flag compartido (`set`/`is_set`) |
| `Barrier` | Punto de sincronización | espera a que N threads lleguen |

### `RLock` (lock reentrante)

Un `Lock` normal NO puede ser readquirido por el mismo thread (se
autobloquearía). `RLock` lleva un contador interno: el mismo thread puede
entrar varias veces a secciones `with self.lock:` anidadas (por ejemplo, un
método que llama a otro método que también toma el lock), y el lock se
libera recién cuando ese thread sale de la última.

### `Condition`: esperar por una condición

`Condition` envuelve un `Lock` y agrega `wait()`/`notify()`/`notify_all()`.
Patrón estándar:

```python
with condition:
    while not condicion_se_cumple():
        condition.wait()
    # ... hacer algo ...
    condition.notify()  # o notify_all()
```

`wait()` SIEMPRE va en un `while`, no en un `if`: al despertar hay que
volver a chequear, porque otro thread puede haberse adelantado (spurious
wakeup) o la condición puede no aplicar para este thread específico.

### `Semaphore`: pool de recursos

Un `Semaphore(n)` arranca con contador `n`. `acquire()` decrementa (bloquea
si llega a 0), `release()` incrementa. A diferencia de `Lock` ("1 a la
vez"), permite que hasta `n` threads tengan el recurso simultáneamente —
ideal para pools de tamaño fijo.

### Deadlocks

Ocurren cuando dos threads toman dos locks en **orden inverso**: cada uno
queda esperando el lock que tiene el otro, para siempre. La solución
estándar es **orden consistente**: todos los threads adquieren los mismos
locks siempre en el mismo orden. Otra opción es usar un único lock que
proteja ambos recursos.

### Readers-Writers

Patrón clásico: múltiples lectores pueden leer en simultáneo, pero un
escritor necesita exclusividad total (ni lectores ni otros escritores). Se
implementa con un `Lock` + dos `Condition` sobre ese lock (una para "puedo
leer", otra para "puedo escribir") y contadores de `readers`/`writers`.

## Scripts

| Archivo | Ejercicio | Descripción |
|---------|-----------|-------------|
| `race_condition_cuenta.py` | 1 | Cuenta bancaria: insegura (pierde depósitos) vs segura (`Lock`) |
| `productor_consumidor_condition.py` | 2 | Cola acotada con `Condition` + `Event` para terminar |
| `barrier_fases.py` | 3 | 4 workers procesando en 2 fases sincronizadas con `Barrier` |
| `semaphore_pool_conexiones.py` | 4 | Pool de 3 conexiones, 10 clientes, `Semaphore` + estadísticas |
| **`readers_writers_lock.py`** | **5 (OBLIGATORIO)** | `ReadWriteLock` desde cero con `Condition` + context managers |
| `deadlock_lock_ordenado.py` | 6 | Deadlock por orden inverso de locks vs solución con orden consistente |
| `rlock_transferencia.py` | adicional | `RLock`: método que se llama a sí mismo a través de otro |
| `demo_race_condition.py` | material de cátedra | Contador compartido: mide % de incrementos perdidos sin/con `Lock` |

## Uso

```bash
python3 race_condition_cuenta.py
python3 productor_consumidor_condition.py
python3 barrier_fases.py
python3 semaphore_pool_conexiones.py
python3 readers_writers_lock.py
python3 deadlock_lock_ordenado.py
python3 rlock_transferencia.py

# demo de cátedra, con opciones:
python3 demo_race_condition.py                    # 5 corridas, sin lock
python3 demo_race_condition.py --runs 20          # más corridas
python3 demo_race_condition.py --safe             # con Lock: siempre correcto
python3 demo_race_condition.py --iter 1000000     # amplifica la race condition
```

## El obligatorio: `readers_writers_lock.py`

```bash
python3 readers_writers_lock.py
```

Verificación:

- [x] Permite múltiples lectores simultáneos (se mide y se imprime el máximo
  observado)
- [x] Bloquea escritores mientras hay lectores
- [x] Bloquea lectores mientras hay un escritor
- [x] Solo permite un escritor a la vez
- [x] Usa `Condition` para la espera (`can_read` / `can_write` sobre el
  mismo `Lock`)
- [x] Implementa `ReadLock`/`WriteLock` como context managers
- [x] Sin deadlocks: al final se verifica que `readers == 0 and writers == 0`

## Notas

- `race_condition_cuenta.py`: a diferencia del ejemplo de la cátedra (que usa
  depósitos/retiros aleatorios), aquí todos los hilos hacen la MISMA
  operación una cantidad fija de veces, así el "saldo esperado" es exacto y
  se puede comparar directamente. `demo_race_condition.py` (provisto por la
  cátedra) hace lo mismo con un contador simple, en mayor escala.
- `productor_consumidor_condition.py`: el `Event` (`terminado`) es la forma
  más simple de avisar "no va a llegar más trabajo"; sin él, los
  consumidores no tendrían forma de saber cuándo dejar de esperar.
- `deadlock_lock_ordenado.py`: la primera parte SÍ se cuelga 2 segundos a
  propósito (es el `join(timeout=2)` detectando el deadlock) — es esperado,
  no es un error.
- `semaphore_pool_conexiones.py`: con 10 clientes y un pool de 3, casi todos
  los requests van a tener que esperar; eso es lo esperado y se refleja en
  las estadísticas.
- Todos los scripts terminan solos y usan el guard `if __name__ == "__main__":`.
