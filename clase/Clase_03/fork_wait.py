#!/usr/bin/env python3
"""
Ejercicio 2.2 - Fork con wait.

El padre crea un hijo y espera (os.wait()) a que termine, recuperando
su código de salida.

Pregunta de la consigna:
  ¿Qué pasa si cambiás os._exit(42) por os._exit(0)?
Respuesta:
  El hijo terminaría con código 0 (éxito convencional en Unix). La única
  diferencia visible es el número que reporta el padre: pasa de 42 a 0.
  El código de salida es un canal de comunicación de 8 bits (0-255) que el
  hijo usa para avisarle al padre cómo le fue.
"""
import os


def main():
    print(f"Proceso original: PID={os.getpid()}")

    pid = os.fork()

    if pid == 0:
        # --- HIJO ---
        print("Hijo trabajando...")
        for i in range(3):
            print(f"  Hijo: paso {i + 1}")
        print("Hijo terminando con código 42")
        os._exit(42)  # os._exit no ejecuta cleanup de Python: ideal tras fork
    else:
        # --- PADRE ---
        print(f"Padre esperando al hijo {pid}...")
        _, status = os.wait()

        if os.WIFEXITED(status):
            codigo = os.WEXITSTATUS(status)
            print(f"Padre: hijo terminó con código {codigo}")
        elif os.WIFSIGNALED(status):
            print(f"Padre: hijo terminado por señal {os.WTERMSIG(status)}")


if __name__ == "__main__":
    main()
