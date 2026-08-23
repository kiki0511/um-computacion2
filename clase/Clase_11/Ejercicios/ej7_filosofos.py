#!/usr/bin/env python3
"""
Ejercicio 7: Filósofos comensales.

Parte A: versión que se cuelga (deadlock garantizado con Barrier).
Parte B: solución por jerarquía de recursos (índice menor primero).
Parte C: solución por semáforo limitador (máximo N-1 comensales).
Parte D: medición comparativa de tiempos y equidad.

Respuestas a las preguntas del enunciado al final del archivo.
"""
import threading
import time
import random
import argparse

NUM = 5
COMIDAS_POR_FILOSOFO = 3


# ─────────────────────────────────────────────
# Parte A: deadlock garantizado con Barrier
# ─────────────────────────────────────────────

def parte_a():
    """
    La Barrier fuerza que los 5 filósofos tengan su tenedor izquierdo
    al mismo tiempo antes de pedir el derecho → deadlock 100% reproducible.
    """
    print("\n=== Parte A: deadlock garantizado ===")
    tenedores = [threading.Lock() for _ in range(NUM)]
    tomaron_izq = threading.Barrier(NUM)
    deadlock = threading.Event()

    def filosofo_ingenuo(id):
        izq = id
        der = (id + 1) % NUM
        with tenedores[izq]:
            print(f"  Filósofo {id} tomó tenedor izquierdo ({izq})")
            tomaron_izq.wait()         # Todos tienen su izquierdo
            # Ninguno puede tomar el derecho → deadlock
            adquirido = tenedores[der].acquire(timeout=1.5)
            if adquirido:
                print(f"  Filósofo {id} come")
                tenedores[der].release()
            else:
                print(f"  Filósofo {id}: NO pudo obtener tenedor {der} → DEADLOCK")
                deadlock.set()

    threads = [threading.Thread(target=filosofo_ingenuo, args=(i,)) for i in range(NUM)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    if deadlock.is_set():
        print("  Resultado: DEADLOCK detectado (esperado)")
    else:
        print("  Resultado: completado (no debería pasar con la Barrier)")


# ─────────────────────────────────────────────
# Parte B: jerarquía de recursos
# ─────────────────────────────────────────────

def parte_b():
    """
    Cada filósofo toma primero el tenedor de MENOR índice.
    Rompe la espera circular: el filósofo 4 tomaría 0 antes que 4,
    mismo que el filósofo 0 → uno de los dos cede.
    """
    print("\n=== Parte B: jerarquía de recursos (menor índice primero) ===")
    tenedores = [threading.Lock() for _ in range(NUM)]
    comidas = [0] * NUM

    def filosofo_jerarquia(id):
        izq = id
        der = (id + 1) % NUM
        primero  = min(izq, der)
        segundo  = max(izq, der)

        for _ in range(COMIDAS_POR_FILOSOFO):
            with tenedores[primero]:
                with tenedores[segundo]:
                    comidas[id] += 1
                    print(f"  Filósofo {id} come (comida {comidas[id]})")
                    time.sleep(random.uniform(0.05, 0.15))
            time.sleep(random.uniform(0.05, 0.1))  # Pensar

    threads = [threading.Thread(target=filosofo_jerarquia, args=(i,)) for i in range(NUM)]
    inicio = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    duracion = time.time() - inicio

    print(f"  Comidas por filósofo: {comidas}")
    print(f"  Tiempo total: {duracion:.3f}s")
    return duracion, comidas


# ─────────────────────────────────────────────
# Parte C: semáforo limitador (máximo N-1)
# ─────────────────────────────────────────────

def parte_c():
    """
    Se permite que como máximo N-1 filósofos intenten comer a la vez.
    Garantiza que al menos uno siempre puede obtener ambos tenedores.
    ¿Por qué basta N-1? Con N-1 comensales hay al menos un tenedor libre
    en la mesa, rompiendo la espera circular.
    """
    print("\n=== Parte C: semáforo limitador (máximo N-1 comensales) ===")
    tenedores = [threading.Lock() for _ in range(NUM)]
    mesa = threading.Semaphore(NUM - 1)
    comidas = [0] * NUM

    def filosofo_semaforo(id):
        izq = id
        der = (id + 1) % NUM

        for _ in range(COMIDAS_POR_FILOSOFO):
            with mesa:                  # Solo N-1 pueden intentar a la vez
                with tenedores[izq]:
                    with tenedores[der]:
                        comidas[id] += 1
                        print(f"  Filósofo {id} come (comida {comidas[id]})")
                        time.sleep(random.uniform(0.05, 0.15))
            time.sleep(random.uniform(0.05, 0.1))

    threads = [threading.Thread(target=filosofo_semaforo, args=(i,)) for i in range(NUM)]
    inicio = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    duracion = time.time() - inicio

    print(f"  Comidas por filósofo: {comidas}")
    print(f"  Tiempo total: {duracion:.3f}s")
    return duracion, comidas


# ─────────────────────────────────────────────
# Parte D: comparación
# ─────────────────────────────────────────────

def parte_d():
    print("\n=== Parte D: comparación de soluciones ===")
    dur_b, comidas_b = parte_b()
    dur_c, comidas_c = parte_c()

    print("\n--- Resumen ---")
    print(f"  Jerarquía:  {dur_b:.3f}s | comidas: {comidas_b} | varianza: {max(comidas_b)-min(comidas_b)}")
    print(f"  Semáforo:   {dur_c:.3f}s | comidas: {comidas_c} | varianza: {max(comidas_c)-min(comidas_c)}")
    print()
    print("  Nota: con sleeps aleatorios la equidad depende del azar.")
    print("  Para detectar starvation habría que correr cientos de iteraciones")
    print("  y medir la distribución estadística de comidas por filósofo.")


# ─────────────────────────────────────────────
# Respuestas a las preguntas del enunciado
# ─────────────────────────────────────────────

RESPUESTAS = """
Preguntas del enunciado:

1. ¿Por qué la Barrier convierte un deadlock esporádico en uno determinista?
   La Barrier fuerza que todos los filósofos lleguen al mismo punto
   (tener su tenedor izquierdo) antes de que cualquiera intente el derecho.
   Eso garantiza la espera circular: cada uno espera el tenedor que tiene
   su vecino, y ninguno puede avanzar. Sin la Barrier el scheduling del SO
   puede hacer que alguno tome ambos tenedores antes de que los demás tomen
   el suyo, evitando el deadlock por puro azar de timing.

2. ¿Cuál condición de Coffman rompe el semáforo?
   La espera circular. Las cuatro condiciones de Coffman son:
     (a) Exclusión mutua       → se mantiene (los locks siguen siendo exclusivos)
     (b) Retención y espera    → se mantiene (un filósofo retiene un tenedor
                                 mientras espera el otro)
     (c) No apropiación        → se mantiene (nadie arranca un tenedor a otro)
     (d) Espera circular       → SE ROMPE: con N-1 comensales siempre hay al
                                 menos un tenedor libre, imposibilitando que
                                 todos esperen al siguiente en un círculo cerrado.

3. ¿Que no coman la misma cantidad es deadlock, starvation, o ninguna?
   Es starvation potencial. Deadlock requiere que ningún thread pueda avanzar.
   Acá todos comen (eventualmente avanzan), pero alguno podría comer mucho
   menos que los demás si el scheduler lo desfavorece sistemáticamente.
   Con sleeps aleatorios y pocas iteraciones es difícil de observar; con
   miles de ciclos y un scheduler injusto podría manifestarse como starvation.
"""


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Filósofos comensales")
    parser.add_argument("parte", nargs="?", choices=["a", "b", "c", "d", "respuestas"],
                        default="d", help="Qué parte ejecutar (default: d = todas)")
    args = parser.parse_args()

    if args.parte == "a":
        parte_a()
    elif args.parte == "b":
        parte_b()
    elif args.parte == "c":
        parte_c()
    elif args.parte == "d":
        parte_a()
        parte_b()
        parte_c()
        parte_d()
    elif args.parte == "respuestas":
        print(RESPUESTAS)
