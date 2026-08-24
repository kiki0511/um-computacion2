#!/usr/bin/env python3
"""
Ejercicio 1: Primer contacto con sockets TCP.

Modos:
  cliente_nc     → cliente Python contra nc -l 8080
  servidor       → servidor Python (usar nc localhost 8080 de cliente)
  demo_reuseaddr → demuestra el problema sin/con SO_REUSEADDR

Respuestas a preguntas conceptuales al final del archivo.
"""
import socket
import sys
import time

HOST = 'localhost'
PORT = 8080


def cliente_nc():
    """
    1.1: Cliente Python que se conecta a nc -l 8080
    Antes de correr esto, levantá: nc -l 8080
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.sendall(b'hola desde Python\n')
        print(f'Recibido: {s.recv(4096)!r}')


def servidor():
    """
    1.2: Servidor Python con bucle para atender múltiples conexiones.
    Usar: nc localhost 8080
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(('0.0.0.0', PORT))
        srv.listen(5)
        print(f'Escuchando en 0.0.0.0:{PORT}...')

        # Respuesta pregunta 5: para que siga atendiendo conexiones
        # hay que envolver accept() en un while True
        while True:
            conn, direccion = srv.accept()
            with conn:
                # Respuesta pregunta 4: direccion es una tupla (IP, puerto)
                # que forma parte de la cuádrupla (IP_src, port_src, IP_dst, port_dst)
                print(f'Conexión desde {direccion}')
                datos = conn.recv(4096)
                if datos:
                    conn.sendall(b'ECHO: ' + datos)


def demo_reuseaddr():
    """
    1.3: Demuestra el efecto de SO_REUSEADDR.
    Corré sin la opción, Ctrl+C, relanzá → 'Address already in use'
    Con la opción: relanzá inmediatamente sin error.
    """
    modo = sys.argv[2] if len(sys.argv) > 2 else 'con'
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        if modo == 'con':
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            print("SO_REUSEADDR activado")
        else:
            print("SO_REUSEADDR NO activado")
        try:
            srv.bind(('0.0.0.0', PORT))
            srv.listen(5)
            print(f'Escuchando en puerto {PORT}. Ctrl+C para parar.')
            conn, dir = srv.accept()
            with conn:
                conn.recv(4096)
        except OSError as e:
            print(f'Error: {e}')
            print('(Probablemente "Address already in use" por TIME-WAIT)')
            print('Solucion: usar setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)')


RESPUESTAS = """
=== Respuestas Ejercicio 1 ===

[1.1.1] ¿Aparece el mensaje en nc?
Sí. nc actúa como servidor: recibe los bytes y los imprime en stdout.

[1.1.2] ¿Qué imprime el cliente cuando escribís en nc?
El cliente imprime lo que nc mandó (la respuesta del "servidor" manual).
recv(4096) bloquea hasta que llegan datos y devuelve lo recibido.

[1.1.3] Sin recv(), ¿nota diferencia el servidor?
No. El servidor (nc) no sabe ni le importa si el cliente lee o no.
El dato queda en el buffer del SO del cliente hasta que lo lean o
se cierre la conexión.

[1.2.4] ¿Qué imprime 'dir'?
Una tupla: ('127.0.0.1', PUERTO_EFIMERO), ej: ('127.0.0.1', 54321)
Es la mitad del cliente de la cuádrupla:
  (IP_cliente, puerto_efimero, IP_servidor, 8080)

[1.2.5] ¿Qué habría que cambiar para que siga atendiendo?
Envolver conn, dir = srv.accept() y el bloque with conn en while True.
(Ver función servidor() arriba)

[1.3.6] Sin SO_REUSEADDR: ¿qué error da al relanzar?
OSError: [Errno 98] Address already in use
El puerto queda en estado TIME-WAIT por ~60s para garantizar que
los paquetes rezagados de la conexión anterior no confundan a la nueva.

[1.3.7] ss -tan state time-wait | head
Sí, aparece el puerto 8080 en TIME-WAIT. El kernel retiene el estado
de la conexión terminada para manejar posibles retransmisiones tardías.

[1.3.8] Con SO_REUSEADDR:
Desaparece el problema. La opción le dice al kernel que permita
reutilizar un puerto en TIME-WAIT para un nuevo bind(). Es estándar
en todo servidor TCP y debe ponerse ANTES de bind().
"""


MODOS = {
    'cliente_nc': cliente_nc,
    'servidor': servidor,
    'demo_reuseaddr': demo_reuseaddr,
    'respuestas': lambda: print(RESPUESTAS),
}

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in MODOS:
        print(f"Uso: python3 {sys.argv[0]} <modo>")
        print(f"Modos: {', '.join(MODOS)}")
        sys.exit(1)
    MODOS[sys.argv[1]]()
