# Clase 05 — Señales

Resolución de los ejercicios prácticos de la Clase 5.

## Conceptos

Una **señal** es una notificación asíncrona que el kernel entrega a un
proceso (ej: SIGINT por Ctrl+C, SIGTERM para pedir terminación, SIGCHLD
cuando muere un hijo). Con `signal.signal(SIG, handler)` se registra un
manejador; con `os.kill(pid, SIG)` se envía una señal a otro proceso.

Buenas prácticas aplicadas:
- El manejador hace lo **mínimo** (bajar una bandera, contar, imprimir). El
  trabajo real ocurre en el loop principal.
- Para esperar señales sin consumir CPU se usa `signal.pause()`.
- SIGCHLD se maneja con `os.waitpid(-1, WNOHANG)` en loop, porque varias
  señales del mismo tipo no se encolan (pueden "fundirse" en una sola).

## Scripts

| Archivo | Ejercicio | Descripción |
|---------|-----------|-------------|
| `capturar_sigint.py` | 2.1 | Intercepta Ctrl+C; sale recién a la 3ª vez |
| `shutdown_limpio.py` | 2.2 | SIGTERM/SIGINT → cierre ordenado y liberación de recursos |
| `senales_padre_hijo.py` | 3.1 | Padre comanda al hijo con SIGUSR1/SIGUSR2 |
| `sigchld.py` | 3.2 | SIGCHLD para recoger hijos sin bloquear ni dejar zombies |
| `timeout.py` | 4.1 | Decorador de timeout con SIGALRM |
| `timer_periodico.py` | 4.2 | Tarea periódica con `setitimer` |
| **`servidor_signals.py`** | **5 (OBLIGATORIO)** | Servidor que responde a HUP/USR1/USR2/TERM |
| `worker_pool.py` | 6.1 | Supervisor que reinicia workers caídos |
| `watchdog.py` | adicional | Reinicia un proceso si muere inesperadamente |
| `rate_limiter.py` | adicional | Límite de N operaciones/segundo con SIGALRM |
| `senales_como_comandos.py` | adicional | Ráfagas de SIGUSR1 como comandos (1=A, 2=B, 3=C) |

## El obligatorio: `servidor_signals.py`

Servidor de larga duración que reacciona a señales mientras procesa
"requests":

```bash
python3 servidor_signals.py      # terminal 1 (muestra su PID)

# terminal 2:
kill -USR1 <pid>   # mostrar estadísticas
kill -HUP  <pid>   # recargar configuración
kill -USR2 <pid>   # rotar logs (simulado)
kill       <pid>   # shutdown limpio
```

Verificación:

- [x] SIGTERM/SIGINT → shutdown limpio
- [x] SIGHUP → recarga configuración
- [x] SIGUSR1 → muestra estadísticas
- [x] SIGUSR2 → rota logs (simulado)
- [x] Muestra PID y comandos al inicio
- [x] Hace cleanup antes de terminar

## Notas

- `capturar_sigint.py`, `shutdown_limpio.py`, `timer_periodico.py`,
  `servidor_signals.py`, `worker_pool.py` y `senales_como_comandos.py` son
  interactivos: corren en loop hasta recibir una señal. Probalos enviándoles
  señales desde otra terminal con `kill`.
- SIGALRM y `signal.pause()` solo funcionan en el hilo principal y en Unix
  (Linux/macOS), no en Windows.
