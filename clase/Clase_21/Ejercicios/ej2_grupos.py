#!/usr/bin/env python3
"""
Ejercicio 2: Grupos de tareas (gather contra TaskGroup).

Las preguntas 1 a 4 se responden corriendo grupos.py de la clase.
Este archivo cubre las que piden escribir código:
  2.1  Tres fallas del mismo tipo en un TaskGroup (pregunta 5)
       ¿Un except común captura un ExceptionGroup? (pregunta 6)
  2.2  Los cuatro casos de "cuál usar", demostrados (pregunta 7)
       Cómo sacar resultados de un TaskGroup (pregunta 8)

Uso:
  python3 ej2_grupos.py
"""
import asyncio
import random


async def falla(n, tipo=ValueError, demora=0.1):
    await asyncio.sleep(demora)
    raise tipo(f'falló la {n}')


# ─────────────────────────────────────────────
# 2.1 ExceptionGroup
# ─────────────────────────────────────────────

async def tres_fallas_iguales():
    print('=== Pregunta 5: tres fallas del mismo tipo ===')
    try:
        async with asyncio.TaskGroup() as g:
            for n in range(3):
                g.create_task(falla(n))
    except* ValueError as eg:
        print(f'  eg.exceptions tiene {len(eg.exceptions)}: '
              f'{[str(e) for e in eg.exceptions]}')
    print('  -> Llegan las tres: el grupo junta TODAS las que fallaron "a la vez"')
    print('     (antes de que la cancelación de las hermanas las alcanzara).\n')


async def except_comun():
    print('=== Pregunta 6: except común contra ExceptionGroup ===')

    # a) except ValueError: NO lo agarra (lo que sale es un ExceptionGroup)
    try:
        try:
            async with asyncio.TaskGroup() as g:
                g.create_task(falla(1))
        except ValueError:
            print('  except ValueError: lo agarró')
    except ExceptionGroup as eg:
        print(f'  except ValueError: NO lo agarró, se escapó un {type(eg).__name__}')

    # b) except ExceptionGroup: SÍ (es una subclase de Exception como cualquier otra)
    try:
        async with asyncio.TaskGroup() as g:
            g.create_task(falla(1))
            g.create_task(falla(2, TypeError))
    except ExceptionGroup as eg:
        tipos = [type(e).__name__ for e in eg.exceptions]
        print(f'  except ExceptionGroup: SÍ lo agarró, adentro hay {tipos}')
        # Lo que se pierde: tenés que recorrer eg.exceptions a mano.
        # .split() hace lo mismo que except* pero a mano:
        valores, resto = eg.split(ValueError)
        print(f'  eg.split(ValueError) -> {len(valores.exceptions)} ValueError, '
              f'resto: {[type(e).__name__ for e in resto.exceptions]}')
    print()


# ─────────────────────────────────────────────
# 2.2 Cuál usar
# ─────────────────────────────────────────────

async def descargar(url):
    await asyncio.sleep(random.uniform(0.05, 0.15))
    if url.endswith('7'):
        raise ConnectionError(f'{url}: no responde')
    return f'{url}: 200'


async def casos():
    print('=== Pregunta 7: cuál usar ===\n')

    # Caso 1: 10 URLs, si una falla quiero las otras 9 → gather(return_exceptions=True)
    urls = [f'https://ejemplo/{i}' for i in range(10)]
    resultados = await asyncio.gather(*(descargar(u) for u in urls),
                                      return_exceptions=True)
    ok = [r for r in resultados if not isinstance(r, Exception)]
    mal = [r for r in resultados if isinstance(r, Exception)]
    print(f'  Caso 1 (10 URLs)   gather(return_exceptions=True): '
          f'{len(ok)} bien, {len(mal)} con error ({mal[0]})')

    # Caso 2: conexión + worker que la usa → TaskGroup (si una muere, la otra no
    # tiene sentido: que se cancelen juntas)
    estado = []

    async def conexion():
        await asyncio.sleep(0.1)
        raise ConnectionResetError('se cayó la base')

    async def worker_db():
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            estado.append('worker cancelado')
            raise

    try:
        async with asyncio.TaskGroup() as g:
            g.create_task(conexion())
            g.create_task(worker_db())
    except* ConnectionResetError:
        pass
    print(f'  Caso 2 (base + worker) TaskGroup: se cayó la conexión -> {estado[0]}')

    # Caso 3: 4 workers que viven lo que el servidor → ninguno de los dos "a secas":
    # create_task + guardar referencias, y cada worker atrapa sus propios errores
    # para no morirse. TaskGroup sirve si querés que una falla tire todo abajo.
    print('  Caso 3 (4 workers permanentes) create_task en el lifespan; '
          'cada worker con try/except propio (ver ej5)')

    # Caso 4: lote todo-o-nada → TaskGroup: al primer error cancela el resto
    hechas = []

    async def paso(i):
        await asyncio.sleep(0.05 * i)
        if i == 2:
            raise ValueError(f'ítem {i} inválido')
        hechas.append(i)

    try:
        async with asyncio.TaskGroup() as g:
            for i in range(6):
                g.create_task(paso(i))
    except* ValueError as eg:
        print(f'  Caso 4 (lote)       TaskGroup: {eg.exceptions[0]} -> '
              f'se cancelaron las que faltaban, terminaron solo {hechas}')
    print()


async def resultados_taskgroup():
    print('=== Pregunta 8: resultados de un TaskGroup ===')
    async with asyncio.TaskGroup() as g:
        tareas = [g.create_task(descargar(f'u{i}')) for i in range(3)]
    # Afuera del async with ya terminaron todas: .result() no bloquea
    print(f'  {[t.result() for t in tareas]}')
    print('  -> Se guardan las Task que devuelve create_task y se lee .result()')


async def main():
    random.seed(21)
    await tres_fallas_iguales()
    await except_comun()
    await casos()
    await resultados_taskgroup()


if __name__ == '__main__':
    asyncio.run(main())
