#!/usr/bin/env python3
"""
Ejercicios adicionales Clase 14:
  A) Servidor con límite de conexiones simultáneas
  B) Servidor con estadísticas (STATS command)

Modos:
  servidor_limite   → tope de clientes, responde "servidor ocupado" si supera
  servidor_stats    → eco + comando STATS con métricas en tiempo real
"""
import socket
import threading
import time
import sys

HOST = 'localhost'
PORT = 8080
LENTO = 0.5


# ─────────────────────────────────────────────
# A: Servidor con límite de conexiones
# ─────────────────────────────────────────────

def servidor_limite():
    """
    Servidor de threads con tope de clientes simultáneos.
    Pasado el límite responde "SERVIDOR OCUPADO" y cierra.
    """
    MAX_CLIENTES = 5
    semaforo = threading.Semaphore(MAX_CLIENTES)
    lock = threading.Lock()
    activos = [0]
    total = [0]

    def atender(conn, addr):
        try:
            time.sleep(LENTO)
            while True:
                datos = conn.recv(4096)
                if not datos:
                    break
                conn.sendall(datos)
        except (ConnectionResetError, BrokenPipeError):
            pass
        finally:
            conn.close()
            semaforo.release()
            with lock:
                activos[0] -= 1
            print(f"[límite] {addr} desconectado. Activos: {activos[0]}")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, PORT))
        srv.listen(128)
        print(f"Servidor con límite ({MAX_CLIENTES} clientes máx) en {HOST}:{PORT}")

        while True:
            conn, addr = srv.accept()

            # Intentar adquirir el semáforo sin bloquear
            if semaforo.acquire(blocking=False):
                with lock:
                    activos[0] += 1
                    total[0] += 1
                print(f"[límite] {addr} aceptado. Activos: {activos[0]}/{MAX_CLIENTES}")
                threading.Thread(
                    target=atender, args=(conn, addr), daemon=True
                ).start()
            else:
                # Servidor lleno: rechazar con mensaje y cerrar
                try:
                    conn.sendall(b"SERVIDOR OCUPADO - intentá más tarde\n")
                except OSError:
                    pass
                conn.close()
                print(f"[límite] {addr} RECHAZADO (servidor lleno)")


# ─────────────────────────────────────────────
# B: Servidor con estadísticas
# ─────────────────────────────────────────────

def servidor_stats():
    """
    Servidor eco que además responde al comando STATS con métricas.
    Cuidado con las race conditions: toda la estadística está bajo lock.
    """
    lock = threading.Lock()
    stats = {
        'activos': 0,
        'total': 0,
        'bytes_rx': 0,
        'bytes_tx': 0,
        'inicio': time.time(),
    }

    def get_stats():
        with lock:
            uptime = time.time() - stats['inicio']
            return (
                f"activos={stats['activos']} "
                f"total={stats['total']} "
                f"bytes_rx={stats['bytes_rx']} "
                f"bytes_tx={stats['bytes_tx']} "
                f"uptime={uptime:.1f}s\n"
            ).encode()

    def atender(conn, addr):
        with lock:
            stats['activos'] += 1
            stats['total'] += 1

        try:
            buffer = b''
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                with lock:
                    stats['bytes_rx'] += len(chunk)
                buffer += chunk

                # Procesar líneas completas
                while b'\n' in buffer:
                    linea, buffer = buffer.split(b'\n', 1)
                    linea_str = linea.strip().decode('utf-8', errors='replace').upper()

                    if linea_str == 'STATS':
                        respuesta = get_stats()
                    else:
                        respuesta = linea + b'\n'

                    conn.sendall(respuesta)
                    with lock:
                        stats['bytes_tx'] += len(respuesta)

        except (ConnectionResetError, BrokenPipeError):
            pass
        finally:
            conn.close()
            with lock:
                stats['activos'] -= 1
            print(f"[stats] {addr} desconectado")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, PORT))
        srv.listen(128)
        print(f"Servidor eco+stats en {HOST}:{PORT}")
        print("Conectate con: nc localhost 8080")
        print("Escribí cualquier cosa para eco, o 'STATS' para ver métricas.")

        while True:
            conn, addr = srv.accept()
            print(f"[stats] {addr} conectado")
            threading.Thread(target=atender, args=(conn, addr), daemon=True).start()


MODOS = {
    'servidor_limite': servidor_limite,
    'servidor_stats': servidor_stats,
}

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in MODOS:
        print(f"Uso: python3 {sys.argv[0]} <modo>")
        print(f"Modos: {', '.join(MODOS)}")
        sys.exit(1)
    try:
        MODOS[sys.argv[1]]()
    except KeyboardInterrupt:
        print('\nDetenido.')
