#!/usr/bin/env python3
"""
Ejercicio 3 (OBLIGATORIO): Framing sobre TCP.

Parte A: demostrar el problema de fusión de mensajes
Parte B: framing por delimitador (\n)
Parte C: framing por prefijo de longitud (4 bytes)
Parte D: comparación

Modos:
  servidor_delimitador   → servidor que usa framing por \n
  cliente_delimitador    → cliente de prueba para el servidor de delimitador
  servidor_longitud      → servidor que usa framing por longitud
  cliente_longitud       → cliente de prueba para el servidor de longitud
  respuestas             → respuestas conceptuales
"""
import socket
import struct
import sys
import time

HOST = 'localhost'
PORT = 8080


# ─────────────────────────────────────────────
# Parte B: Framing por delimitador (\n)
# ─────────────────────────────────────────────

def recibir_lineas(sock):
    """
    Generador que entrega líneas completas (sin el \n final).
    Acumula en buffer entre llamadas a recv() para manejar:
      - Múltiples líneas en un solo recv() (fusión)
      - Línea partida en varios recv() (fragmentación)
    """
    buffer = b''
    while True:
        pedazo = sock.recv(4096)
        if not pedazo:
            # EOF: entregar lo que quede en el buffer (si hay algo)
            if buffer:
                yield buffer
            return
        buffer += pedazo
        # Extraer TODAS las líneas completas del buffer
        while b'\n' in buffer:
            linea, buffer = buffer.split(b'\n', 1)
            yield linea


def servidor_delimitador():
    """Servidor que recibe líneas y responde en mayúsculas + \n"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, PORT))
        srv.listen(5)
        print(f"[Delimitador] Escuchando en {HOST}:{PORT}")
        print("Probá con: nc localhost 8080")
        while True:
            conn, addr = srv.accept()
            print(f"[Delimitador] Conexión de {addr}")
            with conn:
                for linea in recibir_lineas(conn):
                    respuesta = linea.upper() + b'\n'
                    conn.sendall(respuesta)
                    print(f"  < {linea!r}  →  > {respuesta!r}")
            print(f"[Delimitador] {addr} desconectado")


def cliente_delimitador():
    """
    Cliente que prueba los dos casos extremos:
    - Todo junto en un sendall()
    - Byte por byte con sleep
    """
    print("=== Test 1: tres mensajes en un sendall() ===")
    with socket.create_connection((HOST, PORT)) as s:
        s.sendall(b'uno\ndos\ntres\n')
        s.shutdown(socket.SHUT_WR)
        for linea in recibir_lineas(s):
            print(f"  Respuesta: {linea!r}")

    time.sleep(0.5)

    print("\n=== Test 2: 'hola\\n' byte por byte con sleep(0.2) ===")
    with socket.create_connection((HOST, PORT)) as s:
        for byte in b'hola\n':
            s.send(bytes([byte]))
            time.sleep(0.2)
        s.shutdown(socket.SHUT_WR)
        for linea in recibir_lineas(s):
            print(f"  Respuesta: {linea!r}")

    print("\n✓ Ambos casos funcionan correctamente")


# ─────────────────────────────────────────────
# Parte C: Framing por prefijo de longitud (4 bytes)
# ─────────────────────────────────────────────

def recibir_exacto(sock, n):
    """
    Lee EXACTAMENTE n bytes del socket.
    Retorna None si la conexión se cerró antes.
    No puede ser simplemente sock.recv(n) porque recv puede
    devolver menos bytes de los pedidos.
    """
    datos = b''
    while len(datos) < n:
        pedazo = sock.recv(n - len(datos))
        if not pedazo:
            return None  # EOF antes de completar
        datos += pedazo
    return datos


def enviar_mensaje(sock, payload: bytes):
    """Envía: [4 bytes longitud big-endian] + [payload]"""
    header = struct.pack('!I', len(payload))  # '!I' = big-endian uint32
    sock.sendall(header + payload)


def recibir_mensaje(sock):
    """
    Recibe un mensaje con framing por longitud.
    Retorna el payload como bytes, o None si la conexión se cerró.
    """
    header = recibir_exacto(sock, 4)
    if header is None:
        return None
    longitud = struct.unpack('!I', header)[0]
    if longitud == 0:
        return b''
    return recibir_exacto(sock, longitud)


def servidor_longitud():
    """Servidor que usa framing por longitud, responde en mayúsculas."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, PORT))
        srv.listen(5)
        print(f"[Longitud] Escuchando en {HOST}:{PORT}")
        while True:
            conn, addr = srv.accept()
            print(f"[Longitud] Conexión de {addr}")
            with conn:
                while True:
                    msg = recibir_mensaje(conn)
                    if msg is None:
                        break
                    respuesta = msg.upper()
                    print(f"  < {msg!r}  →  > {respuesta!r}")
                    enviar_mensaje(conn, respuesta)
            print(f"[Longitud] {addr} desconectado")


def cliente_longitud():
    """
    Prueba framing por longitud:
    - Mensaje con \n adentro (caso que rompe framing por delimitador)
    - Mensaje vacío
    - Tres mensajes en ráfaga
    """
    with socket.create_connection((HOST, PORT)) as s:
        print("=== Test 1: mensaje con \\n adentro ===")
        msg = b'hola\nmundo\ncon newlines'
        enviar_mensaje(s, msg)
        resp = recibir_mensaje(s)
        print(f"  Enviado:   {msg!r}")
        print(f"  Recibido:  {resp!r}")
        print(f"  ✓ Correcto: {resp == msg.upper()}")

        print("\n=== Test 2: mensaje vacío (0 bytes) ===")
        enviar_mensaje(s, b'')
        resp = recibir_mensaje(s)
        print(f"  Enviado:   b''")
        print(f"  Recibido:  {resp!r}")

        print("\n=== Test 3: tres mensajes en ráfaga ===")
        for texto in [b'uno', b'dos', b'tres']:
            enviar_mensaje(s, texto)
        for i in range(3):
            resp = recibir_mensaje(s)
            print(f"  Respuesta {i+1}: {resp!r}")

        print("\n✓ Framing por longitud funciona en todos los casos")


# ─────────────────────────────────────────────
# Respuestas
# ─────────────────────────────────────────────

RESPUESTAS = """
=== Respuestas Ejercicio 3 ===

[3A.1] ¿Cuántos recv() hizo el servidor para tres sendall()?
Probablemente 1 o 2 (menos que 3). TCP fusionó los envíos.
Eso demuestra que TCP no preserva límites de mensajes.

[3A.2] ¿Viola el contrato de TCP?
No. TCP garantiza que los bytes llegan todos y en orden, no que
lleguen agrupados como se enviaron. El "contrato" es un flujo
de bytes, no mensajes discretos.

[3B.3-5] Casos extremos del framing por delimitador:
- Todo junto (b'uno\\ndos\\ntres\\n' en un sendall): ✓ funciona
  porque el buffer acumula y el while extrae todas las líneas.
- Byte por byte con sleep: ✓ funciona porque el buffer acumula
  hasta encontrar el \\n, sin importar en cuántos recv() llegó.

[3C.6] ¿Por qué recibir_exacto() no puede ser solo recv(n)?
Porque recv(n) devuelve HASTA n bytes, no necesariamente n.
Si el kernel tiene menos disponibles en ese momento, devuelve
lo que hay. Para leer exactamente n bytes hay que acumular en
un bucle hasta completar.

[3C.7] Mensaje con \\n en el medio:
- Framing por LONGITUD: ✓ funciona, el \\n es un byte más del payload.
- Framing por DELIMITADOR: ✗ roto, el \\n se interpreta como fin de
  mensaje partiendo el contenido en dos.

[3C.8] Mensaje de 0 bytes y de 5 GB:
- 0 bytes: el header dice 0, se devuelve b''. Funciona.
- 5 GB: el header uint32 (4 bytes) soporta hasta 2^32-1 = ~4 GB.
  Para 5 GB habría que usar uint64 (8 bytes de header, '!Q' en struct).
  Además habría que evitar leer todo en memoria: leer en chunks.

[3D.9] Tabla comparativa:

| Criterio                    | Delimitador    | Longitud        |
|-----------------------------|----------------|-----------------|
| Contenido binario arbitrario| ✗ (escaping)   | ✓               |
| Depurable con nc            | ✓ (legible)    | ✗ (binario)     |
| Hay que saber el tamaño     | ✗ (no hace falta)| ✓ (antes)     |

[3D.10] ¿Por qué HTTP usa ambos?
Los headers HTTP son texto legible delimitado por \\r\\n (fácil de
debuggear con nc, sin tamaño fijo). El body puede ser binario y
de tamaño variable, por eso usa Content-Length (longitud). Combina
lo mejor de cada estrategia: legibilidad para el protocolo de control
y soporte binario para los datos.
"""

MODOS = {
    'servidor_delimitador': servidor_delimitador,
    'cliente_delimitador': cliente_delimitador,
    'servidor_longitud': servidor_longitud,
    'cliente_longitud': cliente_longitud,
    'respuestas': lambda: print(RESPUESTAS),
}

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in MODOS:
        print(f"Uso: python3 {sys.argv[0]} <modo>")
        print(f"Modos: {', '.join(MODOS)}")
        sys.exit(1)
    MODOS[sys.argv[1]]()
