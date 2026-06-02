#!/usr/bin/env python3
"""
Ejercicio 6.2 - Construir un pipeline con subprocess.

Equivalente a: echo "$texto" | grep error | wc -l

Cada Popen conecta su stdin al stdout del anterior. El padre cierra los
stdout intermedios para que los EOF se propaguen correctamente, y usa
communicate() para recoger el resultado final.
"""
import subprocess


def main():
    texto = """
primera linea
segunda linea con error
tercera linea
otra linea con error
ultima linea
"""

    echo = subprocess.Popen(["echo", texto], stdout=subprocess.PIPE)
    grep = subprocess.Popen(
        ["grep", "error"], stdin=echo.stdout, stdout=subprocess.PIPE
    )
    wc = subprocess.Popen(
        ["wc", "-l"], stdin=grep.stdout, stdout=subprocess.PIPE, text=True
    )

    # Cerrar los extremos del padre para no bloquear el pipeline
    echo.stdout.close()
    grep.stdout.close()

    resultado, _ = wc.communicate()
    print(f"Líneas con 'error': {resultado.strip()}")


if __name__ == "__main__":
    main()
