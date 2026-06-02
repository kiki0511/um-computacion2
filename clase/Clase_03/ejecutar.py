#!/usr/bin/env python3
"""
Ejercicio 3.2 - Función reutilizable que encapsula fork + exec + wait.

ejecutar(comando, args) corre un programa externo y devuelve su código
de salida, manejando el caso de que el comando no exista (código 127,
el mismo convenio que usa bash).
"""
import os
import sys


def ejecutar(comando, args=None):
    """
    Ejecuta un comando externo y retorna su código de salida.

    Args:
        comando: nombre del programa a ejecutar.
        args: lista de argumentos (sin incluir el nombre del comando).

    Returns:
        int: código de salida del comando (127 si no se pudo ejecutar).
    """
    if args is None:
        args = []

    pid = os.fork()

    if pid == 0:
        # HIJO
        try:
            os.execvp(comando, [comando] + args)
        except OSError as e:
            print(f"Error: {e}", file=sys.stderr)
            os._exit(127)
    else:
        # PADRE
        _, status = os.wait()
        return os.WEXITSTATUS(status)


if __name__ == "__main__":
    print("=== Ejecutando ls ===")
    codigo = ejecutar("ls", ["-la", "/tmp"])
    print(f"Código de salida: {codigo}\n")

    print("=== Ejecutando comando inexistente ===")
    codigo = ejecutar("comando_que_no_existe")
    print(f"Código de salida: {codigo}\n")

    print("=== Ejecutando echo ===")
    codigo = ejecutar("echo", ["Hola", "desde", "exec"])
    print(f"Código de salida: {codigo}")
