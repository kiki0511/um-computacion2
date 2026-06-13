#!/usr/bin/env python3
"""
Ejercicio 5 - Race condition y Lock.

Versión insegura: 10 hilos intentan retirar $200 cada uno de un saldo de
$1000. Cada retiro hace `if saldo >= monto`, duerme 0.001s (simula
"procesamiento") y recién ahí resta. Esa ventana entre el chequeo y la resta
es la "ventana de vulnerabilidad": varios hilos pueden pasar el chequeo
viendo el mismo saldo todavía no actualizado, y el saldo termina siendo
negativo (debería llegar a 0 con 5 retiros válidos y rechazar los otros 5).

Versión corregida: el mismo flujo, pero el chequeo + la resta quedan dentro
de un `with lock:`. Así la sección crítica se ejecuta de forma atómica: un
hilo entra, chequea, resta y sale recién ahí; el siguiente ve el saldo ya
actualizado. El saldo final nunca puede ser negativo.
"""
import threading
import time

MONTO = 200
INTENTOS = 10
SALDO_INICIAL = 1000


# --- Versión CON race condition ---
saldo_inseguro = SALDO_INICIAL


def retirar_inseguro(monto):
    global saldo_inseguro
    if saldo_inseguro >= monto:
        time.sleep(0.001)  # simula procesamiento; abre la ventana de carrera
        saldo_inseguro -= monto


# --- Versión CORREGIDA con Lock ---
saldo_seguro = SALDO_INICIAL
lock = threading.Lock()


def retirar_seguro(monto):
    global saldo_seguro
    with lock:
        if saldo_seguro >= monto:
            time.sleep(0.001)
            saldo_seguro -= monto
            print(f"Retiro de ${monto} OK. Saldo: ${saldo_seguro}")
        else:
            print(f"Saldo insuficiente para ${monto}. Saldo: ${saldo_seguro}")


def main():
    print("=== Versión insegura (sin Lock) ===")
    hilos = [threading.Thread(target=retirar_inseguro, args=(MONTO,)) for _ in range(INTENTOS)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    print(f"Saldo inseguro final: ${saldo_inseguro}")
    if saldo_inseguro < 0:
        print("  -> ¡Race condition! El saldo quedó negativo (no debería pasar).")
    else:
        print("  -> Esta vez no se manifestó la condición de carrera, pero")
        print("     puede ocurrir en otra corrida (es no-determinista).")

    print("\n=== Versión corregida (con Lock) ===")
    hilos = [threading.Thread(target=retirar_seguro, args=(MONTO,)) for _ in range(INTENTOS)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    print(f"Saldo seguro final: ${saldo_seguro}")
    assert saldo_seguro >= 0, "El saldo nunca debería ser negativo con Lock"
    print("  -> Nunca es negativo: el Lock vuelve atómica la sección")
    print("     'chequear + restar'.")


if __name__ == "__main__":
    main()
