#!/usr/bin/env python3
"""
Ejercicio 4: Race conditions reales en servidor de threads.

Demuestra que clientes_activos += 1 no es atómica,
y por qué fork no necesita lock.

Modos:
  servidor_con_bug    → contador sin lock (race condition)
  servidor_correcto   → contador con lock
  demo_race           → demuestra la no-atomicidad de += sin socket
  respuestas          → respuestas conceptuales
"""
import socket
import threading
import time
import sys

HOST = 'localhost'
PORT = 8080
LENTO = 0.5


# ─────────────────────────────────────────────
# Demo de race condition sin sockets
# ─────────────────────────────────────────────

def demo_race():
    """
    Demuestra directamente que += no es atómica en Python.
    Agrega un sleep entre lectura y escritura para hacer visible el bug.
    """
    print("=== Contador SIN lock (con sleep artificial entre lectura y escritura) ===")

    contador_buggy = 0
    N = 50

    def incrementar_buggy():
        nonlocal contador_buggy
        for _ in range(10):
            actual = contador_buggy         # leer
            time.sleep(0.0001)              # simula preemption entre lectura y escritura
            contador_buggy = actual + 1     # escribir

    threads = [threading.Thread(target=incrementar_buggy) for _ in range(N)]
    for t in threads: t.start()
    for t in threads: t.join()

    esperado = N * 10
    print(f"  Esperado: {esperado}, Obtenido: {contador_buggy}")
    print(f"  {'RACE CONDITION detectada' if contador_buggy != esperado else 'OK (el timing no causó bug esta vez)'}")

    print("\n=== Contador CON lock ===")

    contador_ok = 0
    lock = threading.Lock()

    def incrementar_ok():
        nonlocal contador_ok
        for _ in range(10):
            with lock:
                actual = contador_ok
                time.sleep(0.0001)
                contador_ok = actual + 1

    threads = [threading.Thread(target=incrementar_ok) for _ in range(N)]
    for t in threads: t.start()
    for t in threads: t.join()

    print(f"  Esperado: {esperado}, Obtenido: {contador_ok}")
    print(f"  {'OK - lock protege la sección crítica' if contador_ok == esperado else 'BUG'}")


# ─────────────────────────────────────────────
# Servidor con race condition
# ─────────────────────────────────────────────

def servidor_con_bug():
    """
    Servidor de threads con contador de clientes SIN lock.
    Con muchos clientes simultáneos, el contador puede quedar incorrecto.
    """
    clientes_activos = 0  # VARIABLE COMPARTIDA SIN PROTECCIÓN

    def atender(conn, addr):
        nonlocal clientes_activos
        # BUG: estas dos líneas no son atómicas
        clientes_activos = clientes_activos + 1  # leer + incrementar sin lock
        print(f"[BUG] {addr} conectó. Activos: {clientes_activos}")
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
            clientes_activos = clientes_activos - 1  # también sin lock
            print(f"[BUG] {addr} desconectó. Activos: {clientes_activos}")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, PORT))
        srv.listen(128)
        print(f"Servidor CON BUG (sin lock) en {HOST}:{PORT}")
        print("Usá muchos clientes simultáneos para ver el contador incorrecto.")
        while True:
            conn, addr = srv.accept()
            threading.Thread(target=atender, args=(conn, addr), daemon=True).start()


# ─────────────────────────────────────────────
# Servidor correcto con lock
# ─────────────────────────────────────────────

def servidor_correcto():
    """
    Servidor de threads con contador protegido por Lock.
    El contador siempre refleja el estado real.
    """
    clientes_activos = 0
    total_atendidos = 0
    lock = threading.Lock()

    def atender(conn, addr):
        nonlocal clientes_activos, total_atendidos
        with lock:
            clientes_activos += 1
            total_atendidos += 1
            print(f"[OK] {addr} conectó. Activos: {clientes_activos}, Total: {total_atendidos}")
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
            with lock:
                clientes_activos -= 1
                print(f"[OK] {addr} desconectó. Activos: {clientes_activos}")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, PORT))
        srv.listen(128)
        print(f"Servidor CORRECTO (con lock) en {HOST}:{PORT}")
        while True:
            conn, addr = srv.accept()
            threading.Thread(target=atender, args=(conn, addr), daemon=True).start()


RESPUESTAS = """
╔══════════════════════════════════════════════════════════════╗
║           Respuestas Ejercicio 4 - Race Conditions          ║
╚══════════════════════════════════════════════════════════════╝

[4.1-2] ¿El contador vuelve a cero sin lock con 200 clientes?
No necesariamente. La race condition es no determinística:
depende del scheduling del SO y del GIL. A veces parece correcto,
a veces no. Con sleep(0.0001) entre lectura y escritura el bug
se manifiesta casi siempre.

[4.3] ¿Por qué clientes_activos += 1 no es atómica?
En Python, x += 1 se descompone en bytecodes:
  LOAD_FAST x        (leer el valor actual)
  LOAD_CONST 1
  BINARY_ADD         (sumar)
  STORE_FAST x       (escribir el resultado)

El GIL puede liberarse entre cualquiera de estas instrucciones
(específicamente entre bytecodes). Si dos threads hacen:
  Thread 1: lee x=5
  Thread 2: lee x=5
  Thread 1: escribe x=6
  Thread 2: escribe x=6   ← perdió el incremento del T1

El resultado es 6 en vez de 7. Esto es exactamente lo que
vimos en la clase 11 con race conditions en variables compartidas.

[4.4] ¿Por qué fork() no necesita lock?
Porque fork() crea una copia COMPLETA del espacio de memoria del proceso.
Cada proceso hijo tiene su PROPIA copia de todas las variables.
No comparten memoria → no hay estado compartido → no puede haber
race condition. Cada hijo opera sobre sus propios datos en su
propio espacio de direcciones, sin interferir con otros hijos
ni con el padre.

Los threads sí comparten memoria (ese es su propósito y su riesgo).
Los procesos (fork) no comparten memoria por defecto.
"""

MODOS = {
    'servidor_con_bug': servidor_con_bug,
    'servidor_correcto': servidor_correcto,
    'demo_race': demo_race,
    'respuestas': lambda: print(RESPUESTAS),
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
