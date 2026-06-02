#!/usr/bin/env python3
"""
Ejercicio 4 - Pipe bidireccional (ping-pong).

multiprocessing.Pipe() devuelve dos extremos conectados (conn_a, conn_b).
A diferencia de os.pipe(), Pipe es bidireccional y serializa objetos Python
(pickle) con send()/recv(). Padre e hijo intercambian 5 mensajes alternados.
"""
import multiprocessing


def hijo(conn):
    for _ in range(5):
        msg = conn.recv()          # esperar ping del padre
        print(f"[HIJO] recibí: {msg}")
        conn.send(f"pong ({msg})")  # responder
    conn.close()


def main():
    padre_conn, hijo_conn = multiprocessing.Pipe()

    p = multiprocessing.Process(target=hijo, args=(hijo_conn,))
    p.start()

    for i in range(5):
        padre_conn.send(f"ping {i}")
        respuesta = padre_conn.recv()
        print(f"[PADRE] recibí: {respuesta}")

    padre_conn.close()
    p.join()
    print("[Main] ping-pong terminado")


if __name__ == "__main__":
    main()
