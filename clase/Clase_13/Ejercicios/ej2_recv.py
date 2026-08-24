#!/usr/bin/env python3
"""
Ejercicio 2: Entender recv().

Modos:
  lectura_parcial    → demuestra lecturas con distintos tamaños de buffer
  senal_cierre       → demuestra qué pasa sin chequeo de EOF
  send_vs_sendall    → demuestra diferencia entre send() y sendall()
  respuestas         → respuestas conceptuales

Necesita echo_server.py del profe corriendo en otra terminal.
"""
import socket
import sys
import time

HOST = 'localhost'
PORT = 8080


def lectura_parcial():
    """
    2.1: Demuestra lecturas parciales con distintos buffers.
    """
    mensaje = b'HolaComoEstas'  # 13 bytes

    for bufsize in [4, 1, 65536]:
        print(f"\n--- recv({bufsize}) ---")
        try:
            with socket.create_connection((HOST, PORT)) as s:
                s.sendall(mensaje)
                # Cerrar escritura para que el servidor haga echo y cierre
                s.shutdown(socket.SHUT_WR)
                recibido = b''
                count = 0
                while True:
                    chunk = s.recv(bufsize)
                    if not chunk:
                        break
                    count += 1
                    print(f"  recv #{count}: {chunk!r}")
                    recibido += chunk
                print(f"  Total recibido: {recibido!r} ({len(recibido)} bytes)")
                print(f"  Llamadas a recv(): {count}")
                assert recibido == mensaje, "¡Se perdieron bytes!"
                print(f"  ✓ Sin pérdida de bytes")
        except ConnectionRefusedError:
            print(f"  (No hay servidor en {HOST}:{PORT})")


def senal_cierre():
    """
    2.2: Demuestra la señal de cierre y el bug de while True sin chequeo.
    """
    print("Versión CON chequeo de cierre (correcta):")
    try:
        with socket.create_connection((HOST, PORT)) as s:
            s.sendall(b'test\n')
            while True:
                datos = s.recv(4096)
                print(f'recv devolvió: {datos!r}')
                if not datos:   # ← ESTE es el chequeo que falta
                    print('Conexión cerrada por el servidor (EOF)')
                    break
    except ConnectionRefusedError:
        print(f"(No hay servidor en {HOST}:{PORT})")

    print("\nNota: sin 'if not datos: break', cuando el servidor cierra,")
    print("recv() devuelve b'' en un loop infinito → 100% de CPU.")


def send_vs_sendall():
    """
    2.3: Diferencia entre send() y sendall() con datos grandes.
    """
    datos = b'X' * (10 * 1024 * 1024)  # 10 MB
    print(f"Intentando enviar {len(datos):,} bytes con send()...")

    try:
        with socket.create_connection((HOST, PORT)) as s:
            enviados = s.send(datos)
            print(f"send() devolvió: {enviados:,} bytes")
            print(f"¿Mandó todo? {'Sí' if enviados == len(datos) else 'NO - solo parcial'}")
            print(f"Diferencia: {len(datos) - enviados:,} bytes NO enviados")
    except ConnectionRefusedError:
        # Simulación sin servidor para mostrar el concepto
        print("(Sin servidor: simulando resultado típico)")
        print("send() con 10MB típicamente devuelve ~2-4MB (el buffer del kernel)")
        print("sendall() garantiza que todo llegue, o lanza excepción")

    print("\nsend()    → devuelve cuánto mandó (puede ser menos)")
    print("sendall() → manda todo o lanza excepción. Usar siempre esto.")
    print("Excepción: si necesitás I/O no bloqueante y manejar envíos parciales vos.")


RESPUESTAS = """
=== Respuestas Ejercicio 2 ===

[2.1.1] ¿Cuántas veces se ejecutó recv(4)? ¿Se perdió algún byte?
Con un mensaje de 13 bytes y recv(4): se necesitan 4 llamadas
(4+4+4+1). No se pierde ningún byte: TCP garantiza entrega completa
y en orden. El buffer solo limita cuánto se toma por vez.

[2.1.2] recv(1) → una llamada por byte. recv(65536) → probablemente 1 llamada
(si el mensaje cabe en el buffer). Pero recv(65536) no garantiza
recibir todo de una: si el otro lado mandó los datos en segmentos
separados, puede devolver solo el primer segmento.

[2.1.3] ¿Por qué recv(65536) no devuelve todo de una vez?
Porque recv() devuelve lo que esté disponible en ese momento en el
buffer del kernel, hasta el máximo pedido. Si los datos todavía están
en tránsito, recv() devuelve lo que llegó. El buffer grande reduce
llamadas al sistema pero no garantiza recepción completa.

[2.2.4] ¿Qué pasa sin chequeo de cierre?
Cuando el servidor cierra, recv() devuelve b'' (bytes vacíos = EOF).
Sin 'if not datos: break', el while True sigue ejecutándose y recv()
sigue devolviendo b'' indefinidamente → bucle infinito a máxima velocidad.

[2.2.5] El chequeo que falta:
    if not datos:
        break
O equivalentemente: if datos == b'': break

[2.2.6] ¿Por qué consume 100% CPU?
Sin bloqueo ni sleep, el bucle corre sin pausa. recv() retorna
inmediatamente con b'' (no bloquea en EOF ya detectado), y el while
repite a máxima velocidad del procesador → 100% de un núcleo.

[2.3.7] send() vs sendall():
send()    → devuelve int: cuántos bytes mandó realmente (≤ len(datos))
sendall() → devuelve None: garantiza que todo fue enviado, o lanza
            OSError si la conexión se rompió.

[2.3.8] send() con 10 MB:
Devuelve menos de 10 MB (típicamente el tamaño del buffer del SO,
unos 2-4 MB). El resto queda sin enviar y el código no se entera
a menos que revise el valor devuelto.

[2.3.9] ¿Cuándo usar send() en vez de sendall()?
En I/O no bloqueante (socket.setblocking(False) o con select/poll),
donde querés intentar enviar lo que se pueda sin bloquearse y manejar
el resto en el próximo ciclo del event loop. En código bloqueante
normal, siempre sendall().
"""

MODOS = {
    'lectura_parcial': lectura_parcial,
    'senal_cierre': senal_cierre,
    'send_vs_sendall': send_vs_sendall,
    'respuestas': lambda: print(RESPUESTAS),
}

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in MODOS:
        print(f"Uso: python3 {sys.argv[0]} <modo>")
        print(f"Modos: {', '.join(MODOS)}")
        sys.exit(1)
    MODOS[sys.argv[1]]()
