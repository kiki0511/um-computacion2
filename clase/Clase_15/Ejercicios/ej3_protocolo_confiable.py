#!/usr/bin/env python3
"""
Ejercicio 3 (OBLIGATORIO): Protocolo confiable sobre UDP.

Partes:
  B → cliente con reintentos (settimeout + TimeoutError)
  C → servidor ingenuo que cuenta el trabajo real: con reintentos procesa de más
  D → números de secuencia (struct '!I'): el servidor deduplica y reenvía la
      respuesta guardada; el cliente descarta respuestas con seq viejo

Todo corre en un solo proceso (servidor en un thread) con pérdidas
simuladas en AMBOS sentidos: se pierde el pedido o se pierde la respuesta.

Modos:
  python3 ej3_protocolo_confiable.py reintentos [perdida]   # Parte B (sin seq)
  python3 ej3_protocolo_confiable.py duplicados [perdida]   # Parte C: el bug
  python3 ej3_protocolo_confiable.py secuencia  [perdida]   # Parte D: arreglado
  python3 ej3_protocolo_confiable.py timeouts               # punto 6
  python3 ej3_protocolo_confiable.py todo                   # todo lo anterior
"""
import random
import socket
import statistics
import struct
import sys
import threading
import time

HOST = 'localhost'
MENSAJES = 20
INTENTOS = 50          # con 70% de pérdida en cada sentido, P(éxito)=0.09 por intento
TIMEOUT = 0.05         # en localhost el RTT es de microsegundos


# ─────────────────────────────────────────────
# Red simulada
# ─────────────────────────────────────────────

def enviar_con_perdidas(sock, datos, destino, prob):
    """Con probabilidad `prob` el datagrama "se pierde": no se manda y nadie avisa."""
    if random.random() >= prob:
        sock.sendto(datos, destino)


# ─────────────────────────────────────────────
# Parte D: formato [4 bytes seq][payload]
# ─────────────────────────────────────────────

def empaquetar(seq, payload):
    return struct.pack('!I', seq) + payload          # '!' = orden de red


def desempaquetar(datos):
    (seq,) = struct.unpack('!I', datos[:4])
    return seq, datos[4:]


# ─────────────────────────────────────────────
# Servidores
# ─────────────────────────────────────────────

class Servidor(threading.Thread):
    """
    Servidor eco-mayúsculas en un thread.

    con_seq=False → ingenuo: cada datagrama que llega = trabajo nuevo.
    con_seq=True  → deduplica por (origen, seq) y reenvía la respuesta guardada.
    """

    def __init__(self, prob, con_seq, demora=0.0):
        super().__init__(daemon=True)
        self.prob = prob
        self.demora = demora              # simula un servidor/red lentos
        self.con_seq = con_seq
        self.trabajos = 0                 # cuántas veces se hizo el trabajo REAL
        self.recibidos = 0                # datagramas que llegaron (incluye dups)
        self.vistos = {}                  # (origen, seq) -> respuesta
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((HOST, 0))         # puerto libre elegido por el SO
        self.direccion = self.sock.getsockname()
        self.sock.settimeout(0.2)
        self.fin = threading.Event()

    def trabajo_real(self, payload):
        self.trabajos += 1                # imaginá "transferir $100"
        return payload.upper()

    def run(self):
        while not self.fin.is_set():
            try:
                datos, origen = self.sock.recvfrom(65535)
            except TimeoutError:
                continue
            self.recibidos += 1

            if not self.con_seq:
                respuesta = self.trabajo_real(datos)
            else:
                seq, payload = desempaquetar(datos)
                clave = (origen, seq)
                if clave in self.vistos:
                    # Duplicado: se perdió MI respuesta. Reenvío sin rehacer.
                    cuerpo = self.vistos[clave]
                else:
                    cuerpo = self.trabajo_real(payload)
                    self.vistos[clave] = cuerpo
                respuesta = empaquetar(seq, cuerpo)

            if self.demora:
                # la respuesta "viaja" demorada sin frenar al servidor
                threading.Timer(self.demora, enviar_con_perdidas,
                                (self.sock, respuesta, origen, self.prob)).start()
            else:
                enviar_con_perdidas(self.sock, respuesta, origen, self.prob)
        time.sleep(self.demora + 0.05)    # dejar salir respuestas demoradas
        self.sock.close()


# ─────────────────────────────────────────────
# Parte B: cliente con reintentos (sin seq)
# ─────────────────────────────────────────────

def pedir_con_reintentos(sock, mensaje, destino, prob, intentos=5, timeout=0.5):
    """
    Manda y reintenta si no llega respuesta.
    Devuelve (respuesta, intentos_usados). Lanza TimeoutError si se agotan.
    """
    sock.settimeout(timeout)
    for intento in range(1, intentos + 1):
        enviar_con_perdidas(sock, mensaje, destino, prob)
        try:
            datos, _ = sock.recvfrom(65535)
            return datos, intento
        except TimeoutError:
            continue
    raise TimeoutError(f'sin respuesta tras {intentos} intentos')


# ─────────────────────────────────────────────
# Parte D: cliente con seq
# ─────────────────────────────────────────────

def pedir_con_seq(sock, seq, payload, destino, prob, intentos=5, timeout=0.5):
    """
    Igual que pedir_con_reintentos, pero descarta respuestas cuyo seq no
    es el del pedido en curso: una respuesta demorada de un intento
    ANTERIOR no puede confundirse con la de este.
    Devuelve (respuesta, intentos_usados, descartadas).
    """
    sock.settimeout(timeout)
    descartadas = 0
    datos_pedido = empaquetar(seq, payload)
    for intento in range(1, intentos + 1):
        enviar_con_perdidas(sock, datos_pedido, destino, prob)
        limite = time.monotonic() + timeout
        while True:
            restante = limite - time.monotonic()
            if restante <= 0:
                break
            sock.settimeout(restante)
            try:
                datos, _ = sock.recvfrom(65535)
            except TimeoutError:
                break
            seq_resp, cuerpo = desempaquetar(datos)
            if seq_resp == seq:
                return cuerpo, intento, descartadas
            descartadas += 1              # respuesta vieja: la ignoro y sigo esperando
    raise TimeoutError(f'seq={seq}: sin respuesta tras {intentos} intentos')


# ─────────────────────────────────────────────
# Experimentos
# ─────────────────────────────────────────────

def correr(prob, con_seq, intentos=INTENTOS, timeout=TIMEOUT, n=MENSAJES,
           verbose=True, demora=0.0):
    random.seed(1234)
    srv = Servidor(prob, con_seq, demora)
    srv.start()
    cliente = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    usados, fallidos, descartadas, incorrectas = [], 0, 0, 0
    t0 = time.perf_counter()
    for i in range(n):
        payload = f'mensaje {i}'.encode()
        try:
            if con_seq:
                resp, k, d = pedir_con_seq(cliente, i, payload, srv.direccion,
                                           prob, intentos, timeout)
                descartadas += d
            else:
                resp, k = pedir_con_reintentos(cliente, payload, srv.direccion,
                                               prob, intentos, timeout)
            usados.append(k)
            if resp != payload.upper():
                incorrectas += 1          # me respondieron OTRO pedido
        except TimeoutError:
            fallidos += 1
    total = time.perf_counter() - t0
    srv.fin.set()
    srv.join()
    cliente.close()

    r = {
        'prob': prob, 'ok': len(usados), 'fallidos': fallidos,
        'prom_intentos': statistics.mean(usados) if usados else 0,
        'max_intentos': max(usados) if usados else 0,
        'envios_reales': sum(usados) + fallidos * intentos,
        'trabajos': srv.trabajos, 'descartadas': descartadas, 'tiempo': total,
        'incorrectas': incorrectas,
    }
    if verbose:
        tipo = 'CON seq' if con_seq else 'SIN seq'
        print(f'  [{tipo}] pérdida={prob:.0%}  mensajes={n}')
        print(f'    respondidos: {r["ok"]}   fallidos: {r["fallidos"]}')
        print(f'    intentos promedio: {r["prom_intentos"]:.2f}  (máx {r["max_intentos"]})')
        print(f'    envíos reales del cliente: {r["envios_reales"]}')
        print(f'    veces que el servidor hizo trabajo: {r["trabajos"]}  '
              f'(debería ser {n})')
        if con_seq:
            print(f'    respuestas viejas descartadas por el cliente: {descartadas}')
        print(f'    respuestas que correspondían a OTRO pedido: {incorrectas}')
        print(f'    tiempo total: {total:.2f}s')
    return r


def modo_reintentos(prob):
    print(f'=== Parte B: reintentos, pérdida {prob:.0%} ===')
    correr(prob, con_seq=False)


def modo_duplicados(prob):
    print(f'=== Parte C: el servidor procesa de más (pérdida {prob:.0%}) ===')
    r = correr(prob, con_seq=False)
    print(f'  → hizo {r["trabajos"] - MENSAJES} trabajos DE MÁS: cada vez que se '
          f'perdió la respuesta, el reintento volvió a ejecutar el pedido.')


def modo_secuencia(prob):
    print(f'=== Parte D: números de secuencia (pérdida {prob:.0%}) ===')
    r = correr(prob, con_seq=True)
    print(f'  → trabajos == mensajes: {"SÍ" if r["trabajos"] == MENSAJES else "NO"}'
          f' (la deduplicación evita repetir el trabajo aunque haya reintentos)')


def modo_timeouts():
    print('=== Punto 6: efecto del timeout (pérdida 30%) ===')
    for t, n in ((0.01, 20), (0.05, 20), (5.0, 4)):
        # con 5s cada pérdida cuesta 5s: lo mido con pocos mensajes
        r = correr(0.3, con_seq=True, timeout=t, n=n, verbose=False)
        print(f'  timeout={t:<5} ok={r["ok"]}/{n} envíos={r["envios_reales"]:<4} '
              f'trabajos={r["trabajos"]:<3} tiempo={r["tiempo"]:.2f}s')

    print('\n=== Punto 11: timeout MENOR que la demora del servidor (30 ms) ===')
    print('  Sin pérdidas: todo reintento es innecesario y las respuestas llegan tarde.')
    for con_seq in (False, True):
        r = correr(0.0, con_seq=con_seq, timeout=0.02, n=10, verbose=False, demora=0.03)
        tipo = 'CON seq' if con_seq else 'SIN seq'
        print(f'  [{tipo}] envíos={r["envios_reales"]:<3} trabajos={r["trabajos"]:<3} '
              f'descartadas={r["descartadas"]:<3} respuestas_equivocadas={r["incorrectas"]}')
    print('  SIN seq el cliente acepta la respuesta demorada del intento anterior como si')
    print('  fuera la del pedido actual: las respuestas quedan corridas un mensaje.')


if __name__ == '__main__':
    args = sys.argv[1:]
    modo = args[0] if args else 'todo'
    prob = float(args[1]) if len(args) > 1 else 0.3

    if modo == 'reintentos':
        modo_reintentos(prob)
    elif modo == 'duplicados':
        modo_duplicados(prob)
    elif modo == 'secuencia':
        modo_secuencia(prob)
    elif modo == 'timeouts':
        modo_timeouts()
    elif modo == 'todo':
        for p in (0.3, 0.7):
            modo_reintentos(p)
            print()
        modo_duplicados(0.3)
        print()
        for p in (0.3, 0.7):
            modo_secuencia(p)
            print()
        modo_timeouts()
    else:
        print(__doc__)
        sys.exit(1)
