#!/usr/bin/env python3
"""
Ejercicio 3.1 - Fork + exec para ejecutar un comando externo (ls).

Patrón fundamental de Unix:
  1. fork()  -> duplica el proceso
  2. exec()  -> el hijo se "transforma" en otro programa (reemplaza su imagen)
  3. wait()  -> el padre recoge el resultado

Si exec tiene éxito, las líneas posteriores en el hijo NUNCA se ejecutan,
porque el proceso ya es otro programa.
"""
import os


def main():
    print(f"Padre (PID {os.getpid()}): voy a ejecutar 'ls -la /tmp'")

    pid = os.fork()

    if pid == 0:
        # HIJO: transformarse en ls
        print(f"Hijo (PID {os.getpid()}): haciendo exec...")
        os.execlp("ls", "ls", "-la", "/tmp")
        # Solo se llega aquí si exec FALLA
        print("ERROR: exec falló")
        os._exit(1)
    else:
        # PADRE: esperar
        _, status = os.wait()
        codigo = os.WEXITSTATUS(status)
        print(f"\nPadre: ls terminó con código {codigo}")


if __name__ == "__main__":
    main()
