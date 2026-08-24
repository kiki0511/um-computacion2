#!/usr/bin/env python3
"""
Ejercicio 5: Errores y timeouts en sockets TCP.

Modos:
  conexion_rechazada  → demuestra ConnectionRefusedError
  reintentos          → cliente con backoff exponencial
  timeout_demo        → demuestra socket.timeout con settimeout()
  servidor_robusto    → servidor que sobrevive desconexiones abruptas
  respuestas          → respuestas conceptuales
"""
import socket
import sys
import time

HOST = 'localhost'
PORT = 8080


def conexion_rechazada():
    """5.1.1: Sin servidor corriendo, ¿qué excepción da?"""
    print("Intentando conectar sin servidor...")
    try:
        with socket.create_connection((HOST, PORT), timeout=2):
            pass
    except ConnectionRefusedError as e:
        print(f"ConnectionRefusedError: {e}")
        print("El SO devuelve RST porque nadie escucha en ese puerto.")
    except socket.timeout as e:
        print(f"socket.timeout: {e}")
        print("(El host existe pero no responde → firewall o host inalcanzable)")


def conectar_con_reintentos(host, puerto, intentos=5):
    """
    5.1.2: Cliente con reintentos y backoff exponencial.
    Espera creciente entre intentos para no saturar el servidor.
    """
    espera = 1
    for intento in range(1, intentos + 1):
        try:
            print(f"[Intento {intento}/{intentos}] Conectando a {host}:{puerto}...")
            conn = socket.create_connection((host, puerto), timeout=3)
            print(f"✓ Conectado en el intento {intento}")
            return conn
        except (ConnectionRefusedError, socket.timeout) as e:
            print(f"  Fallo: {e}")
            if intento < intentos:
                print(f"  Esperando {espera}s antes de reintentar...")
                time.sleep(espera)
                espera = min(espera * 2, 30)  # máximo 30s de espera
    print(f"✗ No se pudo conectar en {intentos} intentos")
    return None


def demo_reintentos():
    """Lanzá el servidor después de correr esto para ver los reintentos."""
    conn = conectar_con_reintentos(HOST, PORT, intentos=5)
    if conn:
        with conn:
            conn.sendall(b'hola\n')
            print(f"Respuesta: {conn.recv(4096)!r}")


def timeout_demo():
    """
    5.2.4-5: Demuestra socket.timeout con settimeout().
    Necesita un servidor que NO responda (nc -l 8080 sin escribir nada).
    """
    print("=== Sin timeout (bloqueante para siempre) ===")
    print("(Omitido para no colgar el demo)")

    print("\n=== Con settimeout(3) ===")
    try:
        with socket.create_connection((HOST, PORT)) as s:
            s.settimeout(3)
            print("Conectado. Esperando datos del servidor (timeout 3s)...")
            datos = s.recv(4096)
            print(f"Recibido: {datos!r}")
    except socket.timeout:
        print("socket.timeout: el servidor no respondió en 3 segundos")
        print("En producción: loggear el error y cerrar la conexión.")
    except ConnectionRefusedError:
        print("(No hay servidor en ese puerto)")

    print("\n¿Por qué un cliente sin timeout es peligroso en producción?")
    print("  Si el servidor se congela o el cable se cae, recv() bloquea")
    print("  indefinidamente. El thread/proceso queda colgado para siempre,")
    print("  consumiendo recursos y sin poder atender otras peticiones.")
    print("  Con timeout: el cliente detecta el problema y puede reintentar,")
    print("  notificar, o liberar recursos.")


def servidor_robusto():
    """
    5.3.7-8: Servidor que sobrevive desconexiones abruptas (Ctrl+C en el cliente).
    Conectate con nc localhost 8080 y mata el nc con Ctrl+C.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, PORT))
        srv.listen(5)
        print(f"Servidor robusto escuchando en {HOST}:{PORT}")
        print("Conectate con: nc localhost 8080")
        print("Mata el cliente con Ctrl+C y verificá que el servidor sigue.")

        while True:
            try:
                conn, addr = srv.accept()
                print(f"\nConexión de {addr}")
                with conn:
                    while True:
                        try:
                            datos = conn.recv(4096)
                            if not datos:
                                print(f"  {addr} cerró la conexión normalmente (EOF)")
                                break
                            print(f"  Recibido: {datos!r}")
                            conn.sendall(datos.upper())
                        except ConnectionResetError:
                            # Cliente cerró abruptamente (Ctrl+C, crash)
                            # El SO envía RST en lugar de FIN
                            print(f"  {addr} se desconectó abruptamente (RST)")
                            break
                        except OSError as e:
                            # Otros errores de I/O (broken pipe, etc.)
                            print(f"  Error con {addr}: {e}")
                            break
            except KeyboardInterrupt:
                print("\nServidor detenido.")
                break


RESPUESTAS = """
=== Respuestas Ejercicio 5 ===

[5.1.1] Sin servidor corriendo: ConnectionRefusedError
El SO del servidor devuelve un paquete TCP RST (reset) porque
no hay proceso escuchando en ese puerto. Python lo convierte en
ConnectionRefusedError.

[5.2.4] Sin timeout, recv() bloquea indefinidamente.
El thread queda en espera del kernel, sin consumir CPU pero
sin poder hacer nada más.

[5.2.5] Con settimeout(3): socket.timeout (subclase de OSError).
El kernel despierta al proceso después de 3 segundos sin datos.

[5.2.6] ¿Por qué un cliente sin timeout es peligroso?
En producción los servidores pueden colgar, los cables cortarse,
y los routers fallar silenciosamente. Sin timeout el cliente queda
bloqueado para siempre, acumulando threads/conexiones colgadas
hasta agotar recursos del sistema.

[5.3.7] ¿El servidor sobrevive a nc con Ctrl+C?
Si tiene try/except para ConnectionResetError: sí. Sin manejo
de excepciones, un RST inesperado mata el loop del servidor.

[5.3.8] Excepciones en echo_server.py:
  ConnectionResetError → cliente cerró abruptamente (Ctrl+C, crash)
  BrokenPipeError      → se intentó escribir a un socket ya cerrado
  OSError              → clase base de errores de I/O de red
Estas tres cubren los casos de desconexión inesperada. Sin ellas,
una desconexión brusca mataría el servidor entero.
"""

MODOS = {
    'conexion_rechazada': conexion_rechazada,
    'reintentos': demo_reintentos,
    'timeout_demo': timeout_demo,
    'servidor_robusto': servidor_robusto,
    'respuestas': lambda: print(RESPUESTAS),
}

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in MODOS:
        print(f"Uso: python3 {sys.argv[0]} <modo>")
        print(f"Modos: {', '.join(MODOS)}")
        sys.exit(1)
    MODOS[sys.argv[1]]()
