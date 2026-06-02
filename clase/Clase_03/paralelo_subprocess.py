#!/usr/bin/env python3
"""
Ejercicio 6 - Misma idea que paralelo.py pero usando subprocess.

Uso:
    python3 paralelo_subprocess.py "cmd1" "cmd2" ...

Reflexión (consigna):
  - subprocess es MÁS SIMPLE: no manejamos fork/exec/wait a mano, ni
    códigos de salida con macros os.W*. Popen + .wait() resuelve todo.
  - fork/exec da MÁS CONTROL de bajo nivel: manipular file descriptors,
    el entorno, señales, hacer cosas entre el fork y el exec, etc.
  - En el día a día se usa subprocess; fork/exec se usa cuando se necesita
    control fino o para entender qué hace subprocess por debajo.
"""
import subprocess
import sys
import time


def main():
    if len(sys.argv) < 2:
        print(f"Uso: {sys.argv[0]} comando1 [comando2 ...]")
        sys.exit(1)

    comandos = sys.argv[1:]
    inicio = time.time()

    # Lanzar todos los procesos (no esperar todavía -> paralelo)
    procesos = []
    for cmd in comandos:
        proc = subprocess.Popen(cmd, shell=True)
        print(f"[{proc.pid}] Iniciado: {cmd}")
        procesos.append((proc, cmd))

    # Esperar a todos
    resultados = []
    for proc, cmd in procesos:
        codigo = proc.wait()
        print(f"[{proc.pid}] Terminado: {cmd} (código: {codigo})")
        resultados.append(codigo)

    duracion = time.time() - inicio
    exitosos = sum(1 for c in resultados if c == 0)

    print("\nResumen:")
    print(f"- Comandos ejecutados: {len(comandos)}")
    print(f"- Exitosos: {exitosos}")
    print(f"- Fallidos: {len(comandos) - exitosos}")
    print(f"- Tiempo total: {duracion:.2f}s")


if __name__ == "__main__":
    main()
