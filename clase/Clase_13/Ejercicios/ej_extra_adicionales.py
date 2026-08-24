#!/usr/bin/env python3
"""
Ejercicios adicionales Clase 13:

  servidor_comandos  → entiende TIME, ECHO <texto>, QUIT
  http_minimo        → GET request a mano sin requests/http.client

Uso:
  python3 ej_extra_adicionales.py servidor_comandos
  python3 ej_extra_adicionales.py http_minimo [host] [path]
"""
import socket
import sys
import time

HOST = 'localhost'
PORT = 8080


# ─────────────────────────────────────────────
# Servidor de comandos (extensión del framing por líneas)
# ─────────────────────────────────────────────

def recibir_lineas(sock):
    """Generador de líneas completas con buffer."""
    buffer = b''
    while True:
        pedazo = sock.recv(4096)
        if not pedazo:
            if buffer:
                yield buffer
            return
        buffer += pedazo
        while b'\n' in buffer:
            linea, buffer = buffer.split(b'\n', 1)
            yield linea


def manejar_comando(conn, linea_bytes):
    """
    Interpreta y ejecuta un comando.
    Retorna False si hay que cerrar la conexión.
    """
    linea = linea_bytes.decode('utf-8', errors='replace').strip()
    partes = linea.split(' ', 1)
    cmd = partes[0].upper()

    if cmd == 'TIME':
        respuesta = time.strftime('%Y-%m-%d %H:%M:%S') + '\n'
        conn.sendall(respuesta.encode())

    elif cmd == 'ECHO':
        texto = partes[1] if len(partes) > 1 else ''
        conn.sendall((texto + '\n').encode())

    elif cmd == 'QUIT':
        conn.sendall(b'Bye!\n')
        return False  # cerrar conexión

    elif cmd == 'HELP':
        ayuda = (
            "Comandos disponibles:\n"
            "  TIME        - hora actual del servidor\n"
            "  ECHO <txt>  - devuelve el texto\n"
            "  QUIT        - cierra la conexión\n"
            "  HELP        - esta ayuda\n"
        )
        conn.sendall(ayuda.encode())

    else:
        conn.sendall(f"ERROR: comando desconocido '{cmd}'\n".encode())

    return True  # seguir atendiendo


def servidor_comandos():
    """
    Servidor de comandos por líneas.
    Probá con: nc localhost 8080
    Escribí: TIME, ECHO hola mundo, QUIT
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, PORT))
        srv.listen(5)
        print(f"Servidor de comandos en {HOST}:{PORT}")
        print("Comandos: TIME, ECHO <texto>, QUIT, HELP")
        print("Probá con: nc localhost 8080\n")

        while True:
            conn, addr = srv.accept()
            print(f"Conexión de {addr}")
            with conn:
                conn.sendall(b"Bienvenido. Escribi HELP para ver los comandos.\n")
                for linea in recibir_lineas(conn):
                    print(f"  < {linea!r}")
                    if not manejar_comando(conn, linea):
                        break
            print(f"{addr} desconectado")


# ─────────────────────────────────────────────
# Cliente HTTP mínimo sin libraries externas
# ─────────────────────────────────────────────

def http_minimo():
    """
    GET request HTTP/1.1 a mano, parseando status y headers.
    Uso: python3 ej_extra_adicionales.py http_minimo [host] [path]
    """
    host = sys.argv[2] if len(sys.argv) > 2 else 'example.com'
    path = sys.argv[3] if len(sys.argv) > 3 else '/'

    print(f"GET {path} HTTP/1.1 → {host}:80\n")

    peticion = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        f"Connection: close\r\n"
        f"\r\n"
    ).encode('ascii')

    with socket.create_connection((host, 80), timeout=10) as s:
        s.sendall(peticion)

        # Recibir todo (Connection: close → el servidor cierra al terminar)
        respuesta = b''
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            respuesta += chunk

    # Separar headers del body en \r\n\r\n
    if b'\r\n\r\n' in respuesta:
        headers_raw, body = respuesta.split(b'\r\n\r\n', 1)
    else:
        headers_raw, body = respuesta, b''

    headers_text = headers_raw.decode('ascii', errors='replace')
    lineas = headers_text.split('\r\n')

    # Status line
    status_line = lineas[0]
    print(f"Status: {status_line}")

    # Headers
    print("\nHeaders:")
    headers = {}
    for linea in lineas[1:]:
        if ':' in linea:
            k, v = linea.split(':', 1)
            headers[k.strip().lower()] = v.strip()
            print(f"  {k.strip()}: {v.strip()}")

    # Body
    content_type = headers.get('content-type', '')
    print(f"\nBody ({len(body)} bytes, tipo: {content_type}):")
    if 'text' in content_type or not content_type:
        preview = body[:500].decode('utf-8', errors='replace')
        print(preview)
        if len(body) > 500:
            print(f"... ({len(body) - 500} bytes más)")
    else:
        print(f"(contenido binario, {len(body)} bytes)")


MODOS = {
    'servidor_comandos': servidor_comandos,
    'http_minimo': http_minimo,
}

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in MODOS:
        print(f"Uso: python3 {sys.argv[0]} <modo>")
        print(f"Modos: {', '.join(MODOS)}")
        sys.exit(1)
    MODOS[sys.argv[1]]()
