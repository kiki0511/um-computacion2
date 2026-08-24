#!/usr/bin/env python3
"""
Ejercicio 3 (OBLIGATORIO): Los tres descuidos del fork.

Partes:
  A  → el padre que no cierra conn (filtrado de descriptores)
  A2 → demostración del filtrado cuando se guarda la referencia
  B  → zombies sin handler de SIGCHLD
  C  → cosechador sin bucle vs con bucle
  D  → SIG_IGN como alternativa

Modos:
  demo_gc         → demuestra que CPython cierra al reasignar (Parte A)
  servidor_a      → servidor con bug: padre no cierra conn
  servidor_a2     → servidor con bug: padre guarda conn en lista
  servidor_b      → servidor sin handler SIGCHLD (genera zombies)
  servidor_c_mal  → cosechador sin bucle (falla bajo carga)
  servidor_c_bien → cosechador con bucle (correcto)
  servidor_d      → SIG_IGN en lugar de handler explícito
  demo_zombies    → script de la parte C del enunciado
  respuestas      → respuestas conceptuales

Puerto por defecto: 8080
"""
import gc
import os
import signal
import socket
import subprocess
import sys
import time

HOST = '0.0.0.0'
PORT = 8080
LENTO = 2  # segundos de sleep por cliente (hace visible el problema)


# ─────────────────────────────────────────────
# Parte A: demostración del GC cerrando descriptores
# ─────────────────────────────────────────────

def demo_gc():
    """
    Demuestra que CPython cierra el fd cuando el objeto socket
    queda sin referencias (conteo de referencias llega a 0).
    """
    print("=== Demo: CPython y descriptores de archivo ===\n")

    def make_socket():
        s = socket.socket()
        fd = s.fileno()
        print(f"Socket creado: fd={fd}")
        return fd   # el socket 's' queda sin referencia al salir de la función

    fd = make_socket()
    print(f"fd={fd} después de salir de make_socket()")

    # CPython usa conteo de referencias: cuando 's' sale de scope,
    # el objeto es destruido y __del__ cierra el fd.
    gc.collect()

    try:
        os.fstat(fd)
        print(f"fd={fd} SIGUE ABIERTO (inesperado en CPython)")
    except OSError:
        print(f"fd={fd} YA ESTÁ CERRADO → CPython lo cerró al destruir el objeto")

    print("\nConclusión:")
    print("En CPython, el socket se cierra cuando su refcount llega a 0.")
    print("En el bucle while True del servidor, conn se reasigna en cada vuelta,")
    print("destruyendo el objeto anterior → CPython cierra el fd automáticamente.")
    print("\nPero esto NO es portable ni correcto por convención:")
    print("  - En C no hay GC: el fd se filtra para siempre.")
    print("  - En PyPy el GC es diferido: el fd puede quedar abierto mucho tiempo.")
    print("  - Si guardamos conn en una lista, la referencia sobrevive y el fd no se cierra.")
    print("  → Siempre cerrar explícitamente con conn.close() en el padre.")


# ─────────────────────────────────────────────
# Servidores con distintos bugs/correcciones
# ─────────────────────────────────────────────

def cosechar_con_bucle(signum, frame):
    """Handler correcto: recoge TODOS los hijos terminados."""
    while True:
        try:
            pid, _ = os.waitpid(-1, os.WNOHANG)
            if pid == 0:
                break
        except ChildProcessError:
            break


def cosechar_sin_bucle(signum, frame):
    """Handler incorrecto: solo recoge UN hijo por señal → zombies bajo carga."""
    try:
        pid, _ = os.waitpid(-1, os.WNOHANG)
        if pid > 0:
            print(f"[HANDLER] Recogido hijo {pid}", flush=True)
    except ChildProcessError:
        pass


def atender_hijo(conn):
    """Lógica del hijo: espera LENTO segundos y hace eco."""
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


def servidor_fork_base(cerrar_padre=True, guardar_conn=False,
                        handler_sigchld='bucle', label=''):
    """
    Servidor fork parametrizable para demostrar los tres descuidos.
    """
    conexiones_abiertas = []  # Para Parte A2

    if handler_sigchld == 'bucle':
        signal.signal(signal.SIGCHLD, cosechar_con_bucle)
    elif handler_sigchld == 'sin_bucle':
        signal.signal(signal.SIGCHLD, cosechar_sin_bucle)
    elif handler_sigchld == 'sig_ign':
        signal.signal(signal.SIGCHLD, signal.SIG_IGN)
    # 'ninguno' → no instalar handler → zombies garantizados

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, PORT))
        srv.listen(128)
        print(f"[{label}] pid={os.getpid()} escuchando en {HOST}:{PORT}")
        if not cerrar_padre:
            print(f"[{label}] BUG: padre NO cierra conn")
        if guardar_conn:
            print(f"[{label}] BUG: padre guarda conn en lista")
        if handler_sigchld == 'ninguno':
            print(f"[{label}] BUG: sin handler SIGCHLD → zombies")
        if handler_sigchld == 'sin_bucle':
            print(f"[{label}] BUG: handler sin bucle → posibles zombies bajo carga")

        while True:
            try:
                conn, addr = srv.accept()
            except InterruptedError:
                continue

            pid = os.fork()
            if pid == 0:
                # HIJO
                srv.close()
                atender_hijo(conn)
                os._exit(0)
            else:
                # PADRE
                if cerrar_padre:
                    conn.close()  # correcto
                elif guardar_conn:
                    conexiones_abiertas.append(conn)  # bug: referencia sobrevive
                # else: ni cierra ni guarda → CPython lo cerrará eventualmente
                print(f"[{label}] Fork hijo {pid} para {addr}, "
                      f"fds={len(os.listdir(f'/proc/{os.getpid()}/fd'))}")


def servidor_a():
    servidor_fork_base(cerrar_padre=False, label='SIN-CLOSE')

def servidor_a2():
    servidor_fork_base(cerrar_padre=False, guardar_conn=True, label='GUARDA-CONN')

def servidor_b():
    servidor_fork_base(cerrar_padre=True, handler_sigchld='ninguno', label='SIN-SIGCHLD')

def servidor_c_mal():
    servidor_fork_base(cerrar_padre=True, handler_sigchld='sin_bucle', label='HANDLER-SIN-BUCLE')

def servidor_c_bien():
    servidor_fork_base(cerrar_padre=True, handler_sigchld='bucle', label='HANDLER-CON-BUCLE')

def servidor_d():
    servidor_fork_base(cerrar_padre=True, handler_sigchld='sig_ign', label='SIG_IGN')


# ─────────────────────────────────────────────
# Demo Parte C: script de zombies simultáneos
# ─────────────────────────────────────────────

def demo_zombies():
    """
    Lanza N hijos que mueren todos al mismo tiempo.
    Con handler sin bucle: algunas señales SIGCHLD colapsan → zombies.
    Con handler con bucle: recoge todos → 0 zombies.
    """
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--bucle', action='store_true', help='Usar handler CON bucle')
    parser.add_argument('--n', type=int, default=60, help='Cantidad de hijos')
    args, _ = parser.parse_known_args()

    recogidos = [0]

    if args.bucle:
        def handler(signum, frame):
            while True:
                try:
                    pid, _ = os.waitpid(-1, os.WNOHANG)
                    if pid == 0: break
                    recogidos[0] += 1
                except ChildProcessError:
                    break
        label = "CON bucle"
    else:
        def handler(signum, frame):
            try:
                pid, _ = os.waitpid(-1, os.WNOHANG)
                if pid > 0:
                    recogidos[0] += 1
            except ChildProcessError:
                pass
        label = "SIN bucle"

    signal.signal(signal.SIGCHLD, handler)

    N = args.n
    print(f"Lanzando {N} hijos que mueren simultáneamente ({label})...")
    for _ in range(N):
        if os.fork() == 0:
            time.sleep(0.5)
            os._exit(0)

    time.sleep(2.0)

    salida = subprocess.run(
        ['ps', '--ppid', str(os.getpid()), '-o', 'stat='],
        capture_output=True, text=True
    ).stdout
    zombies = sum(1 for l in salida.splitlines() if l.strip().startswith('Z'))

    print(f"hijos={N}  recogidos={recogidos[0]}  zombies={zombies}")
    if zombies > 0:
        print("→ Hay zombies: algunas señales SIGCHLD colapsaron y el handler")
        print("  sin bucle no alcanzó a recoger todos los hijos.")
    else:
        print("→ Sin zombies: todos los hijos fueron recogidos correctamente.")


# ─────────────────────────────────────────────
# Respuestas
# ─────────────────────────────────────────────

RESPUESTAS = """
╔══════════════════════════════════════════════════════════════╗
║       Respuestas Ejercicio 3 - Los tres descuidos del fork  ║
╚══════════════════════════════════════════════════════════════╝

═══ PARTE A: El padre que no cierra ═══

[A.1] ¿Crecen los descriptores cuando el padre no cierra conn?
En CPython generalmente NO crecen. Al reasignar conn = srv.accept(),
el objeto socket anterior queda sin referencias y el GC lo destruye,
cerrando el fd automáticamente (conteo de referencias = 0 → __del__).

[A.2] ¿Quién cerró el descriptor?
El recolector de basura de CPython. Usa conteo de referencias:
cuando el refcount de un objeto llega a 0, se destruye inmediatamente.
Al salir de la función make_socket(), 's' queda sin referencias → destruido.

[A.3] En el bucle while True del servidor, ¿qué le pasa al socket anterior?
Se reasigna conn en la próxima llamada a accept(). El objeto socket
anterior pierde su referencia → CPython lo destruye → fd cerrado.

[A.4] ¿El close() del padre es innecesario?
NO. Es necesario en tres casos:
  1. Código C: no hay GC, el fd se filtra definitivamente.
  2. Si conn se guarda en una lista: la referencia sobrevive,
     CPython NO cierra el fd, y los descriptores sí crecen.
  3. PyPy: el GC es generacional y diferido, no por refcount.
     El fd puede quedar abierto minutos o hasta que el GC corra.

[A.5] Conclusión:
Aunque CPython te cubra en el caso simple, escribir conn.close() es
correcto, portable y explícito. El código no debe depender de un
detalle de implementación del intérprete. Programar "para CPython"
en lugar de "para Python" crea deuda técnica invisible.

[A2.6] Con lista: ¿ahora sí crecen los descriptores?
Sí. La lista mantiene viva la referencia al socket → refcount > 0
→ CPython no lo destruye → fd nunca se cierra → crecimiento real.

[A2.7-8] ¿Por qué el cliente no ve el cierre cuando matamos al hijo?
Después del fork(), tanto el padre como el hijo tienen una copia del fd
de conn (misma conexión TCP, dos descriptores). Cuando el hijo muere,
su copia se cierra, pero la del padre sigue abierta. El SO mantiene
la conexión TCP mientras haya al menos UN fd abierto apuntando a ella.
El cliente no recibe FIN hasta que TODAS las copias del fd se cierren.
→ Mecanismo: el fd tiene un refcount en el kernel. Solo cuando llega
a 0 se envía el FIN TCP al cliente.

═══ PARTE B: Zombies ═══

[B.4] Estado de los hijos sin handler SIGCHLD:
Estado Z (Zombie). El hijo terminó pero el padre no llamó wait(),
así que el kernel mantiene la entrada en la tabla de procesos con
el código de salida, esperando que el padre lo recoja.

[B.5-6] Se acumulan con cada corrida del benchmark.
Un servidor así corriendo semanas acumularía miles de zombies.
Aunque los zombies no consumen CPU ni memoria real, sí consumen
una entrada en la tabla de procesos. El límite es /proc/sys/kernel/pid_max
(típicamente 32768 o 4194304). Agotado ese límite, el sistema no puede
crear nuevos procesos: el servidor deja de poder hacer fork().

═══ PARTE C: El cosechador sin bucle ═══

[C.7-8] ¿Siempre da el mismo resultado?
NO. Es intermitente. Depende del timing exacto de cuándo llegan las
señales SIGCHLD respecto a cuándo el handler se ejecuta.

[C.9] Con el bucle while True:
Siempre 0 zombies. El bucle garantiza que se recogen TODOS los hijos
disponibles cada vez que el handler corre, sin importar cuántas señales
colapsaron.

[C.10] ¿Por qué el fallo es intermitente?
Las señales no se encolan en Unix: si llegan N señales SIGCHLD mientras
el handler está bloqueado o aún no corrió, el proceso solo ve 1 señal.
Con el handler sin bucle, llama a waitpid una vez y recoge 1 hijo.
Los otros N-1 quedan zombies. El resultado depende del timing del scheduler:
a veces los hijos mueren de a uno (OK), a veces todos juntos (bug).

[C.11] ¿Qué hace WNOHANG?
Hace que waitpid() retorne inmediatamente aunque no haya hijos terminados,
en lugar de bloquearse esperando. Retorna (0, 0) si no hay nada listo.
SIN WNOHANG en un handler de señal: el handler bloquearía el proceso
principal mientras espera al próximo hijo, dejando de aceptar conexiones.
En un handler de señal SIEMPRE usar WNOHANG.

[C.12] ¿Cómo encontrar un bug intermitente en producción?
  - Monitoreo de /proc: alertar si zombie count crece con el tiempo.
  - Métricas de procesos: graficar cantidad de procesos del servidor.
  - Stress testing: reproducir la carga que causa el bug (muchos clientes
    simultáneos) en staging antes de production.
  - Logging en el handler: contar señales recibidas vs hijos recogidos.

═══ PARTE D: SIG_IGN ═══

[D.10] Con SIG_IGN: ¿siguen apareciendo zombies?
NO. Cuando se ignora SIGCHLD, el kernel automáticamente descarta
el estado de salida de los hijos al morir → no se crean zombies.
Quien los "cosecha" es el propio kernel, sin necesidad de waitpid().
Es la alternativa más simple, con una limitación: el padre pierde
el código de salida de los hijos (no puede saber si murieron bien).
Para un servidor eco, eso no importa. Para un servidor que necesita
saber si el hijo procesó correctamente, usar el handler con bucle.
"""

MODOS = {
    'demo_gc': demo_gc,
    'servidor_a': servidor_a,
    'servidor_a2': servidor_a2,
    'servidor_b': servidor_b,
    'servidor_c_mal': servidor_c_mal,
    'servidor_c_bien': servidor_c_bien,
    'servidor_d': servidor_d,
    'demo_zombies': demo_zombies,
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
