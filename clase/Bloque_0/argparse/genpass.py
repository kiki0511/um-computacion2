#!/usr/bin/env python3
"""Ejercicio 2.3 - Generador de contraseñas seguras."""

import argparse
import secrets
import string
import sys


LETRAS = string.ascii_letters
NUMEROS = string.digits
SIMBOLOS = "!@#$%&*+-?"


def generar_password(longitud, incluir_numeros, incluir_simbolos):
    pool = LETRAS
    if incluir_numeros:
        pool += NUMEROS
    if incluir_simbolos:
        pool += SIMBOLOS

    if not pool:
        print("Error: no puede excluir todos los tipos de caracteres.")
        sys.exit(1)

    return "".join(secrets.choice(pool) for _ in range(longitud))


def main():
    parser = argparse.ArgumentParser(
        description="Genera contraseñas seguras desde la línea de comandos."
    )
    parser.add_argument(
        "-n", "--length",
        type=int,
        default=12,
        metavar="N",
        help="Longitud de la contraseña (default: 12)",
    )
    parser.add_argument(
        "--no-symbols",
        action="store_true",
        help="Excluir símbolos especiales (!@#$%%&*+-?)",
    )
    parser.add_argument(
        "--no-numbers",
        action="store_true",
        help="Excluir números",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        metavar="N",
        help="Cantidad de contraseñas a generar (default: 1)",
    )

    args = parser.parse_args()

    if args.length < 1:
        print("Error: la longitud debe ser al menos 1.")
        sys.exit(1)

    if args.count < 1:
        print("Error: el conteo debe ser al menos 1.")
        sys.exit(1)

    for _ in range(args.count):
        print(generar_password(
            args.length,
            incluir_numeros=not args.no_numbers,
            incluir_simbolos=not args.no_symbols,
        ))

    return 0


if __name__ == "__main__":
    exit(main())
