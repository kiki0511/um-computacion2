#!/usr/bin/env python3
"""
Ejercicio 5 (OBLIGATORIO) - Ejecutor de comandos en paralelo.

Uso:
    python3 paralelo.py "comando1" "comando2" "comando3" ...

Ejemplo:
    python3 paralelo.py "sleep 2" "sleep 1" "echo test"

Lanza todos los comandos al mismo tiempo (un fork + exec por comando),
espera a que todos terminen y reporta:
  - PID de cada comando al iniciarlo
  - código de salida de cada comando al terminar
  - resumen final con el tiempo total

El tiempo total es ~ el del comando MÁS LARGO (se ejecutan en paralelo),
no la suma de todos.
"""
import os
import sys
import time


def main():
    if len(sys.argv) < 2:
        print(f"Uso: {sys.argv[0]} comando1 [comando2 ...]")
        sys.exit(1)

    comandos = sys.argv[1:]
    inicio = time.time()

    # pid -> comando original (para reportar al terminar)
    en_ejecucion = {}

    # Lanzar TODOS los comandos antes de esperar a ninguno (clave del paralelismo)
    for cmd in comandos:
        partes = cmd.split()
        programa, args = partes[0], partes[1:]

        pid = os.fork()
        if pid == 0:
            # HIJO: convertirse en el comando
            try:
                os.execvp(programa, [programa] + args)
            except OSError as e:
                print(f"Error: no se pudo ejecutar '{cmd}': {e}",
                      file=sys.stderr)
                os._exit(127)
        else:
            # PADRE: registrar y seguir lanzando
            en_ejecucion[pid] = cmd
            print(f"[{pid}] Iniciado: {cmd}")

    # Esperar a que terminen, en el orden en que vayan finalizando
    resultados = []
    while en_ejecucion:
        pid, status = os.wait()
        cmd = en_ejecucion.pop(pid)

        if os.WIFEXITED(status):
            codigo = os.WEXITSTATUS(status)
        elif os.WIFSIGNALED(status):
            codigo = -os.WTERMSIG(status)  # negativo = terminado por señal
        else:
            codigo = -1

        print(f"[{pid}] Terminado: {cmd} (código: {codigo})")
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
