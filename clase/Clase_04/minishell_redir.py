#!/usr/bin/env python3
"""
Ejercicio 5 (OBLIGATORIO) - Mini-shell con redirección.

Extiende el mini-shell de la Clase 3 para soportar redirección de E/S:
  - >   redirección de salida (crea/trunca el archivo)
  - >>  redirección de salida en modo append            (BONUS)
  - <   redirección de entrada                            (BONUS)

Ejemplos:
    minish$ echo "hola mundo" > test.txt
    minish$ cat test.txt
    minish$ ls -la >> listado.txt
    minish$ wc -l < listado.txt
    minish$ exit

Las redirecciones se configuran en el HIJO, después del fork y antes del
exec, usando os.dup2() para apuntar fd 0 (stdin) o fd 1 (stdout) al archivo.
"""
import os
import shlex
import sys


def parsear_linea(linea):
    """
    Parsea una línea de comando.

    Retorna (comando, args, archivo_salida, modo_salida, archivo_entrada)
      - modo_salida: "w" para '>', "a" para '>>', None si no hay salida

    Ejemplos:
      "ls -la"          -> ("ls", ["-la"], None, None, None)
      "ls > out.txt"    -> ("ls", [], "out.txt", "w", None)
      "ls >> out.txt"   -> ("ls", [], "out.txt", "a", None)
      "cat < in.txt"    -> ("cat", [], None, None, "in.txt")
    """
    # shlex.split respeta comillas: echo "hola mundo" -> ['echo', 'hola mundo']
    try:
        partes = shlex.split(linea)
    except ValueError as e:
        raise ValueError(f"comillas sin cerrar: {e}")
    if not partes:
        return None, [], None, None, None

    comando = partes[0]
    args = []
    archivo_salida = None
    modo_salida = None
    archivo_entrada = None

    i = 1
    while i < len(partes):
        token = partes[i]
        if token in (">", ">>"):
            if i + 1 >= len(partes):
                raise ValueError(f"falta el archivo después de '{token}'")
            archivo_salida = partes[i + 1]
            modo_salida = "a" if token == ">>" else "w"
            i += 2
        elif token == "<":
            if i + 1 >= len(partes):
                raise ValueError("falta el archivo después de '<'")
            archivo_entrada = partes[i + 1]
            i += 2
        else:
            args.append(token)
            i += 1

    return comando, args, archivo_salida, modo_salida, archivo_entrada


def ejecutar(comando, args, archivo_salida=None, modo_salida="w",
             archivo_entrada=None):
    """Ejecuta un comando con redirección opcional."""
    pid = os.fork()

    if pid == 0:
        # --- HIJO: configurar redirecciones antes del exec ---
        if archivo_salida:
            flags = os.O_CREAT | os.O_WRONLY
            flags |= os.O_APPEND if modo_salida == "a" else os.O_TRUNC
            fd = os.open(archivo_salida, flags, 0o644)
            os.dup2(fd, 1)  # stdout -> archivo
            os.close(fd)

        if archivo_entrada:
            try:
                fd = os.open(archivo_entrada, os.O_RDONLY)
            except OSError as e:
                print(f"minish: {archivo_entrada}: {e}", file=sys.stderr)
                os._exit(1)
            os.dup2(fd, 0)  # stdin <- archivo
            os.close(fd)

        try:
            os.execvp(comando, [comando] + args)
        except OSError as e:
            print(f"minish: {comando}: {e}", file=sys.stderr)
            os._exit(127)
    else:
        # --- PADRE ---
        _, status = os.wait()
        return os.WEXITSTATUS(status)


def main():
    while True:
        try:
            linea = input("minish$ ")
        except EOFError:
            print("\nChau!")
            break

        linea = linea.strip()
        if not linea:
            continue
        if linea == "exit":
            break

        try:
            comando, args, salida, modo, entrada = parsear_linea(linea)
        except ValueError as e:
            print(f"minish: error de sintaxis: {e}", file=sys.stderr)
            continue

        if comando:
            ejecutar(comando, args, salida, modo, entrada)


if __name__ == "__main__":
    main()
