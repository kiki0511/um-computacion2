#!/usr/bin/env python3
"""
Ejercicio 4.1 - Pipeline de dos comandos (equivalente a cmd1 | cmd2).

Idea: el stdout de cmd1 se conecta al stdin de cmd2 a través de un pipe.
  - cmd1: dup2(write_fd, 1)  -> su stdout va al pipe
  - cmd2: dup2(read_fd, 0)   -> su stdin viene del pipe

El padre DEBE cerrar ambos extremos del pipe; si no, cmd2 nunca recibe EOF
y se queda esperando para siempre.
"""
import os


def pipeline_dos_comandos(cmd1, args1, cmd2, args2):
    read_fd, write_fd = os.pipe()

    pid1 = os.fork()
    if pid1 == 0:
        os.close(read_fd)
        os.dup2(write_fd, 1)  # stdout -> pipe
        os.close(write_fd)
        os.execvp(cmd1, [cmd1] + args1)
        os._exit(127)

    pid2 = os.fork()
    if pid2 == 0:
        os.close(write_fd)
        os.dup2(read_fd, 0)  # stdin <- pipe
        os.close(read_fd)
        os.execvp(cmd2, [cmd2] + args2)
        os._exit(127)

    # Padre: cerrar ambos extremos y esperar
    os.close(read_fd)
    os.close(write_fd)
    os.waitpid(pid1, 0)
    os.waitpid(pid2, 0)


if __name__ == "__main__":
    print("=== ls -la | grep '.py' ===")
    pipeline_dos_comandos("ls", ["-la"], "grep", [".py"])
