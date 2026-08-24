#!/usr/bin/env python3
"""
Ejercicio adicional: escáner de puertos 1-1024 en localhost.

Equivalente en Python al script bash con 'nc -z'.
Solo usar contra tu propia máquina.

Uso: python3 ej_extra_port_scanner.py [--timeout 0.3] [--host localhost]
"""
import socket
import argparse
import concurrent.futures
from datetime import datetime

# Servicios conocidos para mostrar nombres
SERVICIOS_CONOCIDOS = {
    21: 'FTP', 22: 'SSH', 23: 'Telnet', 25: 'SMTP',
    53: 'DNS', 80: 'HTTP', 110: 'POP3', 143: 'IMAP',
    443: 'HTTPS', 3306: 'MySQL', 5432: 'PostgreSQL',
    6379: 'Redis', 8080: 'HTTP-alt', 8443: 'HTTPS-alt',
}


def escanear_puerto(host, puerto, timeout):
    """Intenta conectarse al puerto. Devuelve True si está abierto."""
    try:
        with socket.create_connection((host, puerto), timeout=timeout):
            return True
    except (ConnectionRefusedError, socket.timeout, OSError):
        return False


def escanear_rango(host, inicio, fin, timeout, workers=100):
    """Escanea un rango de puertos en paralelo."""
    puertos_abiertos = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(escanear_puerto, host, p, timeout): p
            for p in range(inicio, fin + 1)
        }
        for future in concurrent.futures.as_completed(futures):
            puerto = futures[future]
            if future.result():
                puertos_abiertos.append(puerto)

    return sorted(puertos_abiertos)


def main():
    parser = argparse.ArgumentParser(description='Escáner de puertos (solo usar en tu propia máquina)')
    parser.add_argument('--host', default='localhost', help='Host a escanear (default: localhost)')
    parser.add_argument('--inicio', type=int, default=1, help='Puerto inicial (default: 1)')
    parser.add_argument('--fin', type=int, default=1024, help='Puerto final (default: 1024)')
    parser.add_argument('--timeout', type=float, default=0.3, help='Timeout por puerto en segundos (default: 0.3)')
    parser.add_argument('--workers', type=int, default=100, help='Threads paralelos (default: 100)')
    args = parser.parse_args()

    print(f"╔═══════════════════════════════════════════════╗")
    print(f"║         Escáner de puertos propios            ║")
    print(f"╚═══════════════════════════════════════════════╝")
    print(f"Host:    {args.host}")
    print(f"Rango:   {args.inicio} - {args.fin}")
    print(f"Timeout: {args.timeout}s por puerto")
    print(f"Workers: {args.workers} threads paralelos")
    print(f"Inicio:  {datetime.now().strftime('%H:%M:%S')}")
    print()

    inicio = datetime.now()
    puertos_abiertos = escanear_rango(
        args.host, args.inicio, args.fin, args.timeout, args.workers
    )
    duracion = (datetime.now() - inicio).total_seconds()

    print(f"Fin: {datetime.now().strftime('%H:%M:%S')} ({duracion:.1f}s)\n")

    if puertos_abiertos:
        print(f"{'Puerto':<10} {'Servicio':<20}")
        print("─" * 30)
        for p in puertos_abiertos:
            servicio = SERVICIOS_CONOCIDOS.get(p, 'desconocido')
            print(f"{p:<10} {servicio:<20}")
        print(f"\nTotal abiertos: {len(puertos_abiertos)}")
    else:
        print("No se encontraron puertos abiertos en el rango.")

    print("\nCompará este resultado con: ss -tlnp")


if __name__ == '__main__':
    main()
