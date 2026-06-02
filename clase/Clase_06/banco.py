#!/usr/bin/env python3
"""
Ejercicio de síntesis - Banco con cuentas en memoria compartida.

Varios "cajeros" (procesos) hacen transferencias sobre un Array compartido de
saldos. NO hay sincronización a propósito: las operaciones
    cuentas[origen] -= monto
    cuentas[destino] += monto
no son atómicas, así que con suficientes transferencias el dinero total se
"pierde" o "aparece" -> race condition.

Tareas incorporadas:
  - ejecutar varias veces (correr el script repetido) para ver el efecto
  - TRANSFERENCIAS_POR_PROCESO alto para notar más la race condition
  - log de cada transferencia (origen, destino, monto) a un archivo

Cómo se resolvería (pregunta de la consigna): usando un Lock alrededor del
par de operaciones (o Value/Array con get_lock()) para hacerlas atómicas.
Eso se ve en clases siguientes (sincronización).
"""
from multiprocessing import Process, Array
import random

NUM_CUENTAS = 5
SALDO_INICIAL = 1000
NUM_PROCESOS = 3
TRANSFERENCIAS_POR_PROCESO = 10_000  # alto, para que la race condition se note
LOG = "/tmp/banco_transferencias.log"


def mostrar_saldos(cuentas, etiqueta):
    saldos = [cuentas[i] for i in range(NUM_CUENTAS)]
    print(f"[{etiqueta}] Saldos: {saldos} | Total: {sum(saldos)}")


def cajero(cuentas, cajero_id, num_transferencias):
    # cada cajero escribe su propio log (modo append)
    with open(LOG, "a") as log:
        for _ in range(num_transferencias):
            origen = random.randint(0, NUM_CUENTAS - 1)
            destino = random.randint(0, NUM_CUENTAS - 1)
            while destino == origen:
                destino = random.randint(0, NUM_CUENTAS - 1)
            monto = random.randint(1, 50)

            if cuentas[origen] >= monto:
                cuentas[origen] -= monto   # NO atómico
                cuentas[destino] += monto  # NO atómico
                log.write(f"cajero={cajero_id} {origen}->{destino} ${monto}\n")
    print(f"[Cajero {cajero_id}] Completó {num_transferencias} transferencias")


def main():
    open(LOG, "w").close()  # vaciar log

    cuentas = Array("i", [SALDO_INICIAL] * NUM_CUENTAS)
    print(f"=== Banco con {NUM_CUENTAS} cuentas ===")
    print(f"=== Total esperado: {NUM_CUENTAS * SALDO_INICIAL} ===\n")
    mostrar_saldos(cuentas, "INICIO")

    procesos = []
    for i in range(NUM_PROCESOS):
        p = Process(target=cajero,
                    args=(cuentas, i, TRANSFERENCIAS_POR_PROCESO))
        p.start()
        procesos.append(p)
    for p in procesos:
        p.join()

    mostrar_saldos(cuentas, "FINAL")

    total_final = sum(cuentas[i] for i in range(NUM_CUENTAS))
    total_esperado = NUM_CUENTAS * SALDO_INICIAL
    if total_final != total_esperado:
        print(f"\n¡ERROR! Diferencia de ${total_esperado - total_final}")
        print("Esto es una race condition: se necesita sincronización (Lock).")
    else:
        print("\nTotal correcto esta vez (pero no está garantizado: "
              "ejecutalo varias veces).")
    print(f"Log de transferencias en: {LOG}")


if __name__ == "__main__":
    main()
