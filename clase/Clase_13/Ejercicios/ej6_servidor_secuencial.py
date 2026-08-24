#!/usr/bin/env python3
"""
Ejercicio 6: El límite del servidor secuencial.

Demuestra por qué un servidor sin concurrencia no escala.
Modos:
  servidor_lento   → servidor secuencial con sleep(10)
  respuestas       → respuestas conceptuales
"""
import socket
import sys
import time

HOST = 'localhost'
PORT = 8080


def servidor_lento():
    """
    Servidor secuencial que tarda 10s en atender cada conexión.
    Demostrá: conectá dos clientes al mismo tiempo y observá que
    el segundo espera a que el primero termine.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, PORT))
        srv.listen(5)
        print(f"Servidor secuencial lento en {HOST}:{PORT}")
        print("Conectá dos clientes con: nc localhost 8080")
        print("El segundo espera 10s hasta que el primero termine.")
        print()

        while True:
            conn, addr = srv.accept()
            print(f"[{time.strftime('%H:%M:%S')}] Atendiendo {addr}...")
            with conn:
                time.sleep(10)  # Simula trabajo pesado
                datos = conn.recv(4096)
                if datos:
                    conn.sendall(b'ECHO: ' + datos)
            print(f"[{time.strftime('%H:%M:%S')}] {addr} atendido.")


RESPUESTAS = """
=== Respuestas Ejercicio 6 ===

[6.1] Dos clientes simultáneos: el segundo no responde mientras
el servidor está en sleep(10) atendiendo al primero.
El servidor secuencial solo puede atender uno por vez.

[6.2] ¿Cuánto tarda el segundo cliente en ser atendido?
~10 segundos (lo que tarda el sleep del primero). Si hubiera
N clientes, el N-ésimo esperaría N×10 segundos.

[6.3] La conexión del segundo cliente aparece como ESTAB:
¿Quién completó el handshake si accept() no fue llamado aún?
EL KERNEL. El kernel completa el TCP handshake de tres vías
de forma autónoma antes de que el proceso llame a accept().
La conexión queda en la "accept queue" (cola de backlog) hasta
que el proceso esté listo para procesarla. Por eso el cliente
ve ESTABLISHED aunque el servidor no haya llamado a accept().

[6.4] Recv-Q en la línea LISTEN:
Indica cuántas conexiones completaron el handshake y están
esperando en la cola a ser accept()-adas. Si conectás 3 clientes
y el servidor está ocupado, Recv-Q sube a 2 (o 3).

[6.5] listen(1) con cuatro clientes:
Con listen(1) el backlog es 1 (la cola acepta solo 1 conexión
pendiente). El cuarto cliente recibe ConnectionRefusedError o
timeout porque el kernel descarta el SYN (la cola está llena).

[6.6] "El cliente conectó, así que el servidor lo está atendiendo":
FALSO. El cliente pudo conectarse porque el KERNEL completó el
handshake. Pero el servidor (proceso de Python) puede no haber
llamado accept() todavía. "Conexión establecida" ≠ "siendo atendido
por la lógica de la aplicación".

[6.7] Tres formas de resolver el servidor secuencial:
  1. Threading: un thread por conexión (threading.Thread)
     → simple, pero alto costo de memoria con muchas conexiones
  2. Multiprocessing: un proceso por conexión (os.fork() o Process)
     → aislamiento entre clientes, costo de fork
  3. Pool de workers: ThreadPoolExecutor o ProcessPoolExecutor
     → limita el número de workers, más predecible

  (La clase 14 muestra todas estas en detalle)
"""

MODOS = {
    'servidor_lento': servidor_lento,
    'respuestas': lambda: print(RESPUESTAS),
}

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in MODOS:
        print(f"Uso: python3 {sys.argv[0]} <modo>")
        print(f"Modos: {', '.join(MODOS)}")
        sys.exit(1)
    MODOS[sys.argv[1]]()
