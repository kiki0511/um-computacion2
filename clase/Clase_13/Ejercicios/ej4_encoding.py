#!/usr/bin/env python3
"""
Ejercicio 4: Bytes y encoding en sockets.
Demuestra los problemas de encoding y sus soluciones.
"""
import socket
import sys


def demo_encoding():
    """Demuestra los conceptos de encoding relevantes para sockets."""

    print("=== 4.1 Error al hacer sendall() con string ===")
    # s.sendall('hola')  ← esto da TypeError
    try:
        s = socket.socket()
        s.sendall('hola')   # type: ignore
    except TypeError as e:
        print(f"Error: {e}")
        print("Los sockets trabajan con bytes, no con str.")
        print("Correcto: s.sendall('hola'.encode('utf-8'))")
    finally:
        s.close()

    print("\n=== 4.2 Longitud de strings vs bytes ===")
    palabra = 'año'
    encoded = palabra.encode('utf-8')
    print(f"  'año'              → {repr(palabra)}")
    print(f"  'año'.encode()     → {encoded!r}")
    print(f"  len('año')         = {len(palabra)}  (caracteres Unicode)")
    print(f"  len(encoded)       = {len(encoded)}  (bytes UTF-8)")
    print(f"  Difieren porque 'ñ' ocupa 2 bytes en UTF-8 (código > 127)")

    print("\n=== 4.3 Bug: carácter partido en la red ===")
    datos = 'año'.encode('utf-8')
    print(f"  'año' codificado:  {datos!r}  ({len(datos)} bytes)")
    primera_mitad = datos[:2]
    print(f"  Primeros 2 bytes:  {primera_mitad!r}")
    try:
        resultado = primera_mitad.decode('utf-8')
        print(f"  decode() exitoso: {resultado!r}")
    except UnicodeDecodeError as e:
        print(f"  UnicodeDecodeError: {e}")
        print("  La 'ñ' ocupa 2 bytes (0xc3 0xb1); si llega solo 0xc3, falla.")

    print("\n=== 4.4 Solución: decodificar DESPUÉS del framing ===")
    print("  No decodificar cada recv() por separado.")
    print("  Acumular bytes en buffer, extraer mensaje completo")
    print("  con framing (\\n o longitud), y ENTONCES decodificar.")
    print("  Así nunca se decodifica un carácter a mitad.")

    print("\n=== 4.5 ¿Cuándo es aceptable errors='replace'? ===")
    datos_corruptos = b'hola \xff mundo'
    print(f"  Datos con byte inválido: {datos_corruptos!r}")
    with_replace = datos_corruptos.decode('utf-8', errors='replace')
    print(f"  Con errors='replace':    {with_replace!r}  (byte inválido → U+FFFD)")
    print()
    print("  Aceptable cuando:")
    print("  - El dato es para mostrar al usuario (logs, UI) y la pérdida es tolerable")
    print("  - Se procesa texto de fuente externa con encoding desconocido")
    print("  NO aceptable cuando:")
    print("  - El dato se va a reenviar, hashear, o procesar lógicamente")
    print("  - La integridad importa (datos financieros, criptografía, etc.)")


if __name__ == '__main__':
    demo_encoding()
