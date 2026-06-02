#!/usr/bin/env python3
"""
Ejercicio 3.2 - Comunicación bidireccional con dos pipes.

Un pipe es unidireccional. Para ida y vuelta se usan DOS:
  - p2h: padre -> hijo (el padre escribe, el hijo lee)
  - h2p: hijo -> padre (el hijo escribe, el padre lee)

El padre manda un número, el hijo devuelve su cuadrado.
"""
import os


def main():
    p2h_read, p2h_write = os.pipe()  # padre -> hijo
    h2p_read, h2p_write = os.pipe()  # hijo -> padre

    pid = os.fork()

    if pid == 0:
        # === HIJO ===
        os.close(p2h_write)  # no escribe en padre->hijo
        os.close(h2p_read)   # no lee de hijo->padre

        pregunta = os.read(p2h_read, 1024).decode().strip()
        print(f"[HIJO] Recibí pregunta: {pregunta}")

        if pregunta.isdigit():
            respuesta = str(int(pregunta) ** 2)
        else:
            respuesta = "No es un número"

        os.write(h2p_write, respuesta.encode())
        print(f"[HIJO] Envié respuesta: {respuesta}")

        os.close(p2h_read)
        os.close(h2p_write)
        os._exit(0)

    else:
        # === PADRE ===
        os.close(p2h_read)   # no lee de padre->hijo
        os.close(h2p_write)  # no escribe en hijo->padre

        numero = "42"
        print(f"[PADRE] Enviando número: {numero}")
        os.write(p2h_write, numero.encode())
        os.close(p2h_write)  # avisar al hijo que no hay más entrada (EOF)

        respuesta = os.read(h2p_read, 1024).decode()
        print(f"[PADRE] Respuesta: {numero}² = {respuesta}")

        os.close(h2p_read)
        os.wait()


if __name__ == "__main__":
    main()
