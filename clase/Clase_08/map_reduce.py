#!/usr/bin/env python3
"""
Ejercicio 6 - Map-Reduce para conteo de palabras.

Patrón clásico:
  - MAP    (paralelo): cada worker cuenta las palabras de un texto.
  - REDUCE (secuencial): se combinan los conteos parciales en uno total.
"""
from multiprocessing import Pool
from functools import reduce

TEXTOS = [
    "el rapido zorro marron salta sobre el perro perezoso",
    "el perro duerme bajo el arbol mientras el zorro corre",
    "rapido como el viento el zorro vuelve a saltar sobre el perro",
    "el arbol es viejo y el perro lo mira con curiosidad",
    "saltar correr el zorro y el perro juegan bajo el arbol",
]


def mapper(texto):
    conteo = {}
    for palabra in texto.lower().split():
        conteo[palabra] = conteo.get(palabra, 0) + 1
    return conteo


def reducer(d1, d2):
    resultado = d1.copy()
    for palabra, count in d2.items():
        resultado[palabra] = resultado.get(palabra, 0) + count
    return resultado


def main():
    with Pool(4) as pool:
        conteos_parciales = pool.map(mapper, TEXTOS)

    conteo_total = reduce(reducer, conteos_parciales)
    ordenadas = sorted(conteo_total.items(), key=lambda x: -x[1])

    print("Top palabras más frecuentes:")
    for palabra, count in ordenadas[:10]:
        print(f"  {palabra:15s} {count}")


if __name__ == "__main__":
    main()
