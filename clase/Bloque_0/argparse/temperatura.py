#!/usr/bin/env python3
"""Ejercicio 2.1 - Conversor de temperatura entre Celsius y Fahrenheit."""

import argparse


def celsius_a_fahrenheit(valor):
    return valor * 9 / 5 + 32


def fahrenheit_a_celsius(valor):
    return (valor - 32) * 5 / 9


def main():
    parser = argparse.ArgumentParser(
        description="Convierte temperaturas entre Celsius y Fahrenheit."
    )
    parser.add_argument(
        "valor",
        type=float,
        help="Temperatura a convertir",
    )
    parser.add_argument(
        "-t", "--to",
        choices=["celsius", "fahrenheit"],
        required=True,
        metavar="{celsius,fahrenheit}",
        help="Unidad de destino (celsius o fahrenheit)",
    )

    args = parser.parse_args()

    if args.to == "fahrenheit":
        resultado = celsius_a_fahrenheit(args.valor)
        print(f"{args.valor}°C = {resultado:.2f}°F")
    else:
        resultado = fahrenheit_a_celsius(args.valor)
        print(f"{args.valor}°F = {resultado:.2f}°C")

    return 0


if __name__ == "__main__":
    exit(main())
