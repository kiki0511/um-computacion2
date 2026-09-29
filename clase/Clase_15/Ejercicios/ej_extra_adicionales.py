#!/usr/bin/env python3
"""
Ejercicios adicionales - Clase 15 (UDP).

Modos:
  tiempo   → servidor de tiempo estilo RFC 868 + cliente que calcula desfasaje
  jitter   → medidor de pérdida, desorden y jitter (un iperf en miniatura)

Uso:
  python3 ej_extra_adicionales.py tiempo
  python3 ej_extra_adicionales.py jitter [cantidad] [perdida]
"""
import random
import socket
import statistics
import struct
import sys
import threading
import time

# RFC 868 cuenta segundos desde 1900-01-01; epoch Unix es 1970-01-01
DESFASE_1900 = 2_208_988_800


# ─────────────────────────────────────────────
# Servidor de tiempo (RFC 868)
# ─────────────────────────────────────────────

def servidor_tiempo(sock, fin):
    sock.settimeout(0.2)
    while not fin.is_set():
        try:
            _, origen = sock.recvfrom(1024)       # cualquier datagrama = pedido
        except TimeoutError:
            continue
        segundos = int(time.time()) + DESFASE_1900
        sock.sendto(struct.pack('!I', segundos), origen)


def demo_tiempo():
    srv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    srv.bind(('localhost', 0))
    fin = threading.Event()
    threading.Thread(target=servidor_tiempo, args=(srv, fin), daemon=True).start()

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as c:
        c.settimeout(2)
        t0 = time.time()
        c.sendto(b'', srv.getsockname())
        datos, _ = c.recvfrom(4)
        t1 = time.time()
    (seg_1900,) = struct.unpack('!I', datos)
    remoto = seg_1900 - DESFASE_1900
    local = (t0 + t1) / 2              # estimación: el servidor respondió a mitad del RTT
    print(f'Hora del servidor : {time.strftime("%H:%M:%S", time.localtime(remoto))}')
    print(f'RTT               : {(t1 - t0) * 1000:.3f} ms')
    print(f'Desfasaje estimado: {remoto - local:+.3f} s  (resolución de 1 s por el protocolo)')
    fin.set()
    srv.close()


# ─────────────────────────────────────────────
# Medidor de pérdida y jitter
# ─────────────────────────────────────────────

def demo_jitter(cantidad=1000, perdida=0.05, intervalo=0.001):
    receptor = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receptor.bind(('localhost', 0))
    receptor.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1 << 20)
    receptor.settimeout(0.5)
    emisor = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    llegadas = []                               # (seq, t_envio, t_llegada)

    def recibir():
        while True:
            try:
                datos, _ = receptor.recvfrom(64)
            except TimeoutError:
                return
            seq, t_envio = struct.unpack('!Id', datos)
            llegadas.append((seq, t_envio, time.perf_counter()))

    hilo = threading.Thread(target=recibir)
    hilo.start()
    for seq in range(cantidad):
        if random.random() >= perdida:          # pérdida simulada
            emisor.sendto(struct.pack('!Id', seq, time.perf_counter()),
                          receptor.getsockname())
        time.sleep(intervalo)
    hilo.join()

    seqs = [s for s, _, _ in llegadas]
    desordenados = sum(1 for a, b in zip(seqs, seqs[1:]) if b < a)
    retardos = [(tl - te) * 1000 for _, te, tl in llegadas]
    # jitter = variación entre retardos consecutivos (como RFC 3550, simplificado)
    jitter = statistics.mean(abs(b - a) for a, b in zip(retardos, retardos[1:]))
    print(f'Enviados    : {cantidad}')
    print(f'Recibidos   : {len(llegadas)}  (perdidos {cantidad - len(set(seqs))}, '
          f'{(cantidad - len(set(seqs))) / cantidad:.1%})')
    print(f'Desordenados: {desordenados}')
    print(f'Retardo     : prom {statistics.mean(retardos):.3f} ms, '
          f'máx {max(retardos):.3f} ms')
    print(f'Jitter      : {jitter:.3f} ms')
    receptor.close()
    emisor.close()


if __name__ == '__main__':
    args = sys.argv[1:]
    modo = args[0] if args else ''
    if modo == 'tiempo':
        demo_tiempo()
    elif modo == 'jitter':
        n = int(args[1]) if len(args) > 1 else 1000
        p = float(args[2]) if len(args) > 2 else 0.05
        demo_jitter(n, p)
    else:
        print(__doc__)
        sys.exit(1)
