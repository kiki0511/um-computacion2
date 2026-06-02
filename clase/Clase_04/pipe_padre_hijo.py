#!/usr/bin/env python3
"""
Ejercicio 3.1 - Comunicación básica por pipe entre padre e hijo.

os.pipe() devuelve (read_fd, write_fd). El pipe debe crearse ANTES del fork
para que ambos procesos hereden los dos extremos.

Regla de oro: cada proceso cierra el extremo que NO usa. Si el padre no
cierra su write_fd, nunca verá EOF al leer (el pipe "sigue abierto para
escritura" desde su propia copia del fd).
"""
import os


def main():
    read_fd, write_fd = os.pipe()  # crear pipe antes del fork

    pid = os.fork()

    if pid == 0:
        # === HIJO: escribe ===
        os.close(read_fd)  # no lee

        mensajes = [
            "Mensaje 1 del hijo",
            "Mensaje 2 del hijo",
            "Mensaje 3 del hijo",
            "FIN",
        ]
        for msg in mensajes:
            os.write(write_fd, (msg + "\n").encode())
            print(f"[HIJO] Envié: {msg}")

        os.close(write_fd)
        os._exit(0)

    else:
        # === PADRE: lee ===
        os.close(write_fd)  # no escribe

        print("[PADRE] Esperando mensajes del hijo...\n")

        buffer = b""
        while True:
            datos = os.read(read_fd, 1024)
            if not datos:  # EOF: el hijo cerró su extremo de escritura
                break
            buffer += datos

        for msg in buffer.decode().strip().split("\n"):
            print(f"[PADRE] Recibí: {msg}")

        os.close(read_fd)
        os.wait()
        print("\n[PADRE] Hijo terminó")


if __name__ == "__main__":
    main()
