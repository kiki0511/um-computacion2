#!/usr/bin/env python3
"""
Ejercicio adicional 6.1 - Contador de procesos.

Cuenta cuántos procesos hay en el sistema contando las entradas de /proc
cuyo nombre es un número (cada proceso tiene un directorio /proc/<PID>).
"""
import os


def contar_procesos():
    return sum(1 for entrada in os.listdir("/proc") if entrada.isdigit())


if __name__ == "__main__":
    print(f"Procesos en ejecución: {contar_procesos()}")
