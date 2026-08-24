#!/usr/bin/env python3
"""
Ejercicio 6 (OBLIGATORIO): TCP es un flujo, no mensajes.

Partes:
  A → demostrar que TCP puede agrupar envíos (sin sleep)
  B → respuestas conceptuales impresas
  C → servidor UDP que preserva límites de datagrama
  D → cliente UDP

Uso:
  python3 ej6_tcp_flujo.py servidor_tcp   (terminal 1)
  python3 ej6_tcp_flujo.py cliente_tcp    (terminal 2, rápido sin pausa)
  python3 ej6_tcp_flujo.py cliente_tcp_sleep  (terminal 2, con pausa)
  python3 ej6_tcp_flujo.py servidor_udp   (terminal 1)
  python3 ej6_tcp_flujo.py cliente_udp    (terminal 2)
  python3 ej6_tcp_flujo.py respuestas     (solo imprime las respuestas)
"""
import socket
import sys
import time

HOST = 'localhost'
PORT = 8080


# ─────────────────────────────────────────────
# Parte A: servidor TCP que muestra cómo llegan los datos
# ─────────────────────────────────────────────

def servidor_tcp():
    """
    Servidor TCP que imprime cada recv() por separado.
    Revela si los tres envíos del cliente llegan juntos o separados.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, PORT))
        srv.listen(1)
        print(f"[TCP Server] Escuchando en {HOST}:{PORT}...")
        conn, addr = srv.accept()
        print(f"[TCP Server] Conexión de {addr}")
        with conn:
            recv_count = 0
            while True:
                data = conn.recv(4096)
                if not data:
                    break
                recv_count += 1
                print(f"[TCP Server] recv #{recv_count}: {data!r}")
        print(f"[TCP Server] Total de recv(): {recv_count}")
        print("[TCP Server] Observación: si recv_count < 3, los envíos llegaron agrupados.")


def cliente_tcp():
    """
    Envía tres mensajes SIN pausa entre ellos.
    TCP puede (y suele) agruparlos en un solo segmento.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        for msg in [b'HOLA', b'COMO', b'ESTAS']:
            s.send(msg)
            print(f"[TCP Client] Sent: {msg!r}")
    print("[TCP Client] Conexión cerrada.")


def cliente_tcp_sleep():
    """
    Envía tres mensajes CON pausa entre ellos.
    El sleep aumenta la probabilidad de que lleguen separados,
    pero NO es una solución: el comportamiento depende del SO y la red.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        for msg in [b'HOLA', b'COMO', b'ESTAS']:
            s.send(msg)
            print(f"[TCP Client] Sent: {msg!r}")
            time.sleep(1)
    print("[TCP Client] Conexión cerrada.")


# ─────────────────────────────────────────────
# Parte C: servidor y cliente UDP
# ─────────────────────────────────────────────

def servidor_udp():
    """
    Servidor UDP: cada recvfrom() recibe exactamente un datagrama.
    Los límites entre mensajes se preservan siempre.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind((HOST, PORT))
        s.settimeout(5)
        print(f"[UDP Server] Escuchando en {HOST}:{PORT} (timeout 5s)...")
        recv_count = 0
        try:
            while True:
                datos, origen = s.recvfrom(4096)
                recv_count += 1
                print(f"[UDP Server] recv #{recv_count}: {datos!r} de {origen}")
        except socket.timeout:
            print("[UDP Server] Timeout, fin.")
        print(f"[UDP Server] Total de recvfrom(): {recv_count}")
        print("[UDP Server] Observación: recv_count == cantidad de send() del cliente.")


def cliente_udp():
    """
    Envía tres datagramas UDP SIN pausa.
    A diferencia de TCP, cada uno llega como un recvfrom() separado en el servidor.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        for msg in [b'HOLA', b'COMO', b'ESTAS']:
            s.sendto(msg, (HOST, PORT))
            print(f"[UDP Client] Sent: {msg!r}")
    print("[UDP Client] Datagramas enviados.")


# ─────────────────────────────────────────────
# Parte B: respuestas conceptuales
# ─────────────────────────────────────────────

RESPUESTAS = """
═══════════════════════════════════════════════════════════
Respuestas conceptuales - Ejercicio 6
═══════════════════════════════════════════════════════════

[Pregunta 1] ¿Cómo llegaron los datos al servidor TCP sin pausa?
Los tres envíos (b'HOLA', b'COMO', b'ESTAS') pueden llegar agrupados
en un solo recv(), por ejemplo como b'HOLACOMOESTAS'. El servidor hace
menos llamadas a recv() que envíos hizo el cliente.

[Pregunta 2] Con sleep(1), ¿cambió? ¿Se puede confiar?
Con sleep aumenta la probabilidad de que lleguen separados, porque le da
tiempo al stack TCP a entregar cada segmento antes de que llegue el
siguiente. Pero NO se puede confiar: TCP no hace promesas sobre
agrupamiento. El SO puede seguir juntando segmentos (Nagle's algorithm),
y el comportamiento varía entre plataformas y cargas de red.

[Pregunta 3] ¿Es un bug de TCP?
NO. TCP garantiza que los bytes llegan todos y en orden, pero NO
garantiza que lleguen agrupados como se enviaron. Su "contrato" es
un flujo de bytes confiable y ordenado, no mensajes discretos. Los
límites entre envíos son invisibles para el receptor.

[Pregunta 4] Dos formas de delimitar mensajes sobre TCP:

  A) Delimitador especial (ej: '\\n', '\\0'):
     - El emisor agrega el carácter al final de cada mensaje.
     - El receptor lee hasta encontrar ese carácter.
     - Problema: si el mensaje CONTIENE el delimitador, hay que
       escaparlo o encodificarlo (ej: base64). De lo contrario el
       receptor interpreta un delimitador dentro del mensaje como
       el fin del mensaje → datos corruptos.

  B) Prefijo de longitud (length-prefix framing):
     - El emisor antepone N bytes que indican el tamaño del mensaje.
     - El receptor lee N bytes de header, luego lee exactamente
       esa cantidad de bytes de payload.
     - Problema: si el mensaje es de longitud variable y muy largo,
       el header de tamaño fijo puede quedarse corto (overflow).
       Requiere acordar el tamaño del header (ej: 4 bytes = hasta 4 GB).

[Pregunta 5] ¿Cuántas veces se ejecutó recvfrom() en UDP?
Exactamente 3: una por cada sendto() del cliente. UDP preserva los
límites porque cada datagrama es una unidad indivisible: llega entero
o no llega. No hay stream, no hay agrupamiento.

[Pregunta 6] ¿Por qué UDP preserva límites y TCP no?
TCP es un protocolo de flujo (stream): toma los bytes del buffer de
envío y los agrupa en segmentos según convenga al control de congestión
y al algoritmo de Nagle. El receptor no ve segmentos, ve bytes.

UDP es un protocolo de datagramas: cada send() crea un paquete IP
independiente. El receptor llama a recvfrom() y obtiene exactamente
los bytes de ese paquete, o nada.

[Pregunta 7] ¿Por qué el servidor UDP no necesita listen() ni accept()?
Porque UDP es sin conexión. No hay handshake, no hay estado de conexión,
no hay distinción entre "estar escuchando" y "estar conectado". El
servidor simplemente hace bind() al puerto y recvfrom() en bucle,
procesando cada datagrama de cualquier origen. No hay concepto de
"cliente conectado" que aceptar.

═══════════════════════════════════════════════════════════
"""


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

MODOS = {
    'servidor_tcp':      servidor_tcp,
    'cliente_tcp':       cliente_tcp,
    'cliente_tcp_sleep': cliente_tcp_sleep,
    'servidor_udp':      servidor_udp,
    'cliente_udp':       cliente_udp,
    'respuestas':        lambda: print(RESPUESTAS),
}

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in MODOS:
        print(f"Uso: python3 {sys.argv[0]} <modo>")
        print(f"Modos disponibles: {', '.join(MODOS)}")
        sys.exit(1)

    MODOS[sys.argv[1]]()
