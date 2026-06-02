#!/usr/bin/env python3
"""
Ejercicio 4 - Mini-shell.

Shell minimalista que junta los tres pasos guiados de la consigna:
  - Loop de lectura (REPL)
  - Comandos externos con fork + exec + wait
  - Comandos internos (cd, exit)

¿Por qué cd debe ser un comando interno y no un programa externo?
  Porque cada proceso tiene su propio directorio de trabajo. Si cd fuera
  un programa externo, correría en un proceso HIJO (vía fork+exec); ese
  hijo cambiaría SU directorio y al terminar moriría, dejando el directorio
  del shell padre intacto. Para que el cambio persista, el propio shell
  debe llamar a os.chdir() en su proceso, sin hacer fork.
"""
import os


def cmd_cd(args):
    """Comando interno cd: cambia el directorio del propio shell."""
    destino = args[0] if args else os.environ.get("HOME", "/")
    try:
        os.chdir(destino)
    except OSError as e:
        print(f"cd: {e}")


def main():
    internos = {
        "cd": cmd_cd,
    }

    while True:
        cwd = os.getcwd()
        try:
            linea = input(f"minish:{cwd}$ ")
        except EOFError:
            print("\nChau!")
            break

        linea = linea.strip()
        if not linea:
            continue
        if linea == "exit":
            break

        partes = linea.split()
        comando, args = partes[0], partes[1:]

        # ¿Comando interno?
        if comando in internos:
            internos[comando](args)
            continue

        # Comando externo: fork + exec + wait
        pid = os.fork()
        if pid == 0:
            try:
                os.execvp(comando, [comando] + args)
            except OSError as e:
                print(f"minish: {comando}: {e}")
                os._exit(127)
        else:
            _, status = os.wait()
            codigo = os.WEXITSTATUS(status)
            if codigo != 0:
                print(f"[código {codigo}]")


if __name__ == "__main__":
    main()
