"""
Mediciones obligatorias del TP2. Corre desde el host, con la API levantada.

Solo usa la biblioteca estándar: no hace falta instalar nada en la máquina.

    python3 mediciones/medir.py io                     # medición 1
    python3 mediciones/medir.py io --reales            # medición 1 con sitios reales
    python3 mediciones/medir.py loop                   # medición 2 (correr 2 veces, ver abajo)
    python3 mediciones/medir.py techo --tipo esperar   # medición 3
    python3 mediciones/medir.py techo --tipo hashear   # medición 3

Medición 2: se corre dos veces, cambiando cómo arranca la API:
    USAR_EXECUTOR=false docker compose up --build      # hash dentro del event loop (mal)
    docker compose up --build                          # hash en el ProcessPoolExecutor (bien)

Cada medición imprime una tabla en Markdown lista para pegar en el README y
guarda los datos crudos en mediciones/resultados/<medicion>_<fecha>.json.

Este script es un CLIENTE: usa threads y urllib (bloqueante) a propósito,
porque solo dispara requests y mide. Lo que se mide es la API, no esto.
"""

from __future__ import annotations  # para correr también con el python3 3.9 de macOS

import argparse
import json
import math
import platform
import random
import re
import statistics
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

API = "http://localhost:8000"
CARPETA_RESULTADOS = Path(__file__).parent / "resultados"
ESTADOS_FINALES = {"completada", "fallida", "cancelada"}

# 20 sitios reales para `io --reales`. Varían en tamaño y en distancia.
URLS_REALES = [
    "https://www.python.org",
    "https://docs.python.org/3/",
    "https://fastapi.tiangolo.com",
    "https://www.python-httpx.org",
    "https://github.com",
    "https://www.wikipedia.org",
    "https://es.wikipedia.org/wiki/Asyncio",
    "https://www.um.edu.ar",
    "https://www.google.com",
    "https://www.mozilla.org",
    "https://www.debian.org",
    "https://www.kernel.org",
    "https://www.docker.com",
    "https://pypi.org",
    "https://www.rust-lang.org",
    "https://www.apache.org",
    "https://www.cloudflare.com",
    "https://www.mercadolibre.com.ar",
    "https://www.clarin.com",
    "https://www.lanacion.com.ar",
]


# --------------------------------------------------------------------- HTTP


def pedir(metodo: str, ruta: str, cuerpo: dict | None = None, timeout: float = 300):
    """Hace un request a la API. Devuelve (json, segundos que tardó)."""
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    req = urllib.request.Request(
        API + ruta,
        data=datos,
        method=metodo,
        headers={"Content-Type": "application/json"},
    )
    inicio = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            contenido = r.read()
    except urllib.error.HTTPError as e:
        sys.exit(f"Error {e.code} en {metodo} {ruta}: {e.read().decode()}")
    except urllib.error.URLError as e:
        sys.exit(f"No se pudo conectar a {API} ({e.reason}). ¿Está levantada la API?")
    return json.loads(contenido), time.perf_counter() - inicio


def crear(tipo: str, parametros: dict, timeout: float | None = None) -> str:
    cuerpo = {"tipo": tipo, "parametros": parametros}
    if timeout is not None:
        cuerpo["timeout"] = timeout
    respuesta, _ = pedir("POST", "/tareas", cuerpo)
    return respuesta["id"]


def esperar_finales(ids: list[str], intervalo: float = 0.2) -> dict[str, dict]:
    """Consulta la API hasta que todas las tareas estén en un estado final."""
    pendientes = set(ids)
    while True:
        tareas, _ = pedir("GET", "/tareas")
        por_id = {t["id"]: t for t in tareas if t["id"] in pendientes}
        if all(t["estado"] in ESTADOS_FINALES for t in por_id.values()) and len(por_id) == len(pendientes):
            return por_id
        time.sleep(intervalo)


def esperar_inactiva() -> None:
    """Espera a que no haya tareas en cola ni ejecutando, para no mezclar mediciones."""
    while True:
        est, _ = pedir("GET", "/estadisticas")
        if est["en_cola"] == 0 and est["workers"]["ocupados"] == 0:
            return
        time.sleep(0.2)


def fecha(iso: str) -> datetime:
    """Parsea las fechas ISO de la API. Rellena los decimales a 6 dígitos
    porque fromisoformat de Python < 3.11 no acepta otra cantidad."""
    iso = iso.replace("Z", "+00:00")
    iso = re.sub(r"\.(\d{1,6})", lambda m: "." + m.group(1).ljust(6, "0"), iso)
    return datetime.fromisoformat(iso)


def guardar(nombre: str, datos: dict) -> Path:
    CARPETA_RESULTADOS.mkdir(exist_ok=True)
    ruta = CARPETA_RESULTADOS / f"{nombre}_{datetime.now():%Y%m%d_%H%M%S}.json"
    est, _ = pedir("GET", "/estadisticas")
    datos["entorno"] = {
        "host": f"{platform.system()} {platform.machine()}",
        "workers": est["workers"]["total"],
        "executor": est.get("executor"),
    }
    ruta.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8")
    return ruta


def ms(segundos: float) -> str:
    return f"{segundos * 1000:.1f} ms"


# ---------------------------------------------------------- medición 1: I/O


def medir_io(args) -> None:
    if args.reales:
        urls = URLS_REALES
        origen = "20 sitios reales"
    else:
        # Demoras fijas (semilla) entre 0,2 y 1,5 s: siempre las mismas 20 URLs
        azar = random.Random(2026)
        demoras = [round(azar.uniform(0.2, 1.5), 2) for _ in range(20)]
        urls = [f"{args.lento}/demora/{d}?bytes=50000" for d in demoras]
        origen = (
            f"servidor lento local (demoras 0,2-1,5 s; suma {sum(demoras):.2f} s, "
            f"máxima {max(demoras):.2f} s)"
        )

    print(f"Medición 1 — 20 descargas, {origen}")
    print(f"{args.repeticiones} repeticiones de cada modo\n")
    esperar_inactiva()

    corridas = {"secuencial": [], "concurrente": []}
    detalle_corridas = []  # resultado completo de cada corrida (por URL), para el JSON
    errores = 0
    for i in range(1, args.repeticiones + 1):
        for modo in ("secuencial", "concurrente"):
            tid = crear("descargar", {"urls": urls, "secuencial": modo == "secuencial"}, timeout=300)
            tarea = esperar_finales([tid])[tid]
            if tarea["estado"] != "completada":
                sys.exit(f"La tarea terminó {tarea['estado']}: {tarea['error']}")
            res = tarea["resultado"]
            fallidas = [d for d in res["descargas"] if "error" in d]
            errores += len(fallidas)
            corridas[modo].append(res["total_segundos"])
            detalle_corridas.append({"corrida": i, "modo": modo, **res})
            # La más lenta: en modo concurrente es la que marca el tiempo total
            lenta = max(res["descargas"], key=lambda d: d["segundos"])
            print(f"  corrida {i} {modo:<11} {res['total_segundos']:7.3f} s"
                  f"  | más lenta: {lenta['url']} ({lenta['segundos']:.2f} s)")
            for d in fallidas:
                print(f"      error en {d['url']}: {d['error']}")

    sec = statistics.median(corridas["secuencial"])
    conc = statistics.median(corridas["concurrente"])
    print(f"\nDescargas con error: {errores}")
    print("\n| Modo | Tiempo (mediana) | Corridas |")
    print("|------|-----------------:|----------|")
    for modo, valor in (("Secuencial (`for` + `await`)", sec), ("Concurrente (`gather`)", conc)):
        clave = "secuencial" if "Secuencial" in modo else "concurrente"
        detalle = ", ".join(f"{x:.2f}" for x in corridas[clave])
        print(f"| {modo} | {valor:.2f} s | {detalle} |")
    print(f"\n**Speedup: {sec / conc:.1f}x**")

    ruta = guardar(
        "io_reales" if args.reales else "io_lento",
        {"origen": origen, "urls": urls, "corridas": corridas, "errores": errores,
         "detalle": detalle_corridas,
         "mediana_secuencial": sec, "mediana_concurrente": conc, "speedup": sec / conc},
    )
    print(f"\nDatos crudos: {ruta}")


# ------------------------------------------------ medición 2: loop bloqueado


def medir_loop(args) -> None:
    est, _ = pedir("GET", "/estadisticas")
    usar = est.get("executor", {}).get("usar")
    modo = "CON executor" if usar else "SIN executor (hash en el event loop)"
    print(f"Medición 2 — latencia de GET /tareas durante un hash de {args.iteraciones:,} iteraciones")
    print(f"API corriendo {modo}\n")
    esperar_inactiva()

    # Línea de base: la API sin nada corriendo
    base = [pedir("GET", "/tareas")[1] for _ in range(20)]

    tid, lat_post = None, None
    respuesta, lat_post = pedir(
        "POST", "/tareas",
        {"tipo": "hashear", "parametros": {"texto": "medicion", "iteraciones": args.iteraciones},
         "timeout": 600},
    )
    tid = respuesta["id"]

    # Mientras el hash corre, un GET /tareas cada 50 ms. Cada request
    # espera a la respuesta anterior: si el loop está bloqueado, se nota.
    durante = []
    while True:
        tareas, lat = pedir("GET", "/tareas")
        durante.append(lat)
        tarea = next(t for t in tareas if t["id"] == tid)
        if tarea["estado"] in ESTADOS_FINALES:
            break
        time.sleep(0.05)

    duracion = (fecha(tarea["finalizada"]) - fecha(tarea["iniciada"])).total_seconds()
    print(f"Hash terminó en {duracion:.2f} s (estado: {tarea['estado']})")
    print(f"POST /tareas respondió en {ms(lat_post)}\n")
    print("| Modo | Duración del hash | GET /tareas en reposo (prom.) | GET durante el hash: atendidos | prom. | máx. |")
    print("|------|------------------:|------------------------------:|-------------------------------:|------:|-----:|")
    print(
        f"| {'Con' if usar else 'Sin'} `run_in_executor` | {duracion:.2f} s | {ms(statistics.mean(base))} "
        f"| {len(durante)} | {ms(statistics.mean(durante))} | {ms(max(durante))} |"
    )

    ruta = guardar(
        "loop_con_executor" if usar else "loop_sin_executor",
        {"iteraciones": args.iteraciones, "usar_executor": usar, "duracion_hash": duracion,
         "latencia_post": lat_post, "latencias_reposo": base, "latencias_durante": durante},
    )
    print(f"\nDatos crudos: {ruta}")


# ----------------------------------------------------- medición 3: techo


def medir_techo(args) -> None:
    if args.tipo == "esperar":
        parametros = {"segundos": args.segundos}
        descripcion = f"esperar {args.segundos:g} s"
    else:
        parametros = {"texto": "techo", "iteraciones": args.iteraciones}
        descripcion = f"hashear {args.iteraciones:,} iteraciones"

    est, _ = pedir("GET", "/estadisticas")
    workers = est["workers"]["total"]
    procesos = (est.get("executor") or {}).get("procesos")
    niveles = [int(x) for x in args.niveles.split(",")]
    print(f"Medición 3 — techo del pool con tareas '{descripcion}'")
    print(f"API con {workers} workers y {procesos} procesos en el executor\n")

    if args.tipo == "hashear":
        # Calentamiento: el ProcessPoolExecutor crea sus procesos recién cuando
        # le llega trabajo. Sin esto, el primer nivel mediría el arranque de
        # los procesos (spawn + importar módulos) y no el hash.
        esperar_finales([crear("hashear", {"texto": "calentar", "iteraciones": 200_000})
                         for _ in range(procesos or 2)])

    filas = []
    for k in niveles:
        esperar_inactiva()
        # Las k tareas se mandan "de golpe", desde varios hilos a la vez
        with ThreadPoolExecutor(max_workers=min(k, 32)) as hilos:
            ids = list(hilos.map(lambda _: crear(args.tipo, parametros, timeout=600), range(k)))
        tareas = list(esperar_finales(ids).values())

        creadas = [fecha(t["creada"]) for t in tareas]
        iniciadas = [fecha(t["iniciada"]) for t in tareas]
        finalizadas = [fecha(t["finalizada"]) for t in tareas]
        total = (max(finalizadas) - min(creadas)).total_seconds()
        cola = statistics.mean((i - c).total_seconds() for i, c in zip(iniciadas, creadas))
        ejec = statistics.mean((f - i).total_seconds() for f, i in zip(finalizadas, iniciadas))
        fila = {"tareas": k, "total": total, "cola_prom": cola, "ejecucion_prom": ejec,
                "por_segundo": k / total,
                "fallidas": sum(1 for t in tareas if t["estado"] != "completada")}
        if args.tipo == "esperar":
            fila["ideal"] = math.ceil(k / workers) * args.segundos
        filas.append(fila)
        print(f"  {k:>4} tareas: total {total:7.2f} s | cola prom. {cola:6.2f} s | ejecución prom. {ejec:6.2f} s")

    print()
    if args.tipo == "esperar":
        print("| Tareas | Tiempo total | Ideal ⌈k/workers⌉·s | Espera en cola (prom.) | Ejecución (prom.) | Tareas/s |")
        print("|-------:|-------------:|--------------------:|-----------------------:|------------------:|---------:|")
        for f in filas:
            print(f"| {f['tareas']} | {f['total']:.2f} s | {f['ideal']:.0f} s | {f['cola_prom']:.2f} s "
                  f"| {f['ejecucion_prom']:.2f} s | {f['por_segundo']:.1f} |")
    else:
        print("| Tareas | Tiempo total | Espera en cola (prom.) | Ejecución (prom.) | Tareas/s |")
        print("|-------:|-------------:|-----------------------:|------------------:|---------:|")
        for f in filas:
            print(f"| {f['tareas']} | {f['total']:.2f} s | {f['cola_prom']:.2f} s "
                  f"| {f['ejecucion_prom']:.2f} s | {f['por_segundo']:.2f} |")
    if any(f["fallidas"] for f in filas):
        print("\nOjo: hubo tareas que no terminaron 'completada' (ver JSON).")

    ruta = guardar(f"techo_{args.tipo}_w{workers}",
                   {"tipo": args.tipo, "parametros": parametros, "filas": filas})
    print(f"\nDatos crudos: {ruta}")


# ---------------------------------------------------------------------- CLI


def main() -> None:
    global API
    parser = argparse.ArgumentParser(description="Mediciones del TP2")
    parser.add_argument("--api", default=API, help="URL base de la API (default %(default)s)")
    sub = parser.add_subparsers(dest="medicion", required=True)

    p_io = sub.add_parser("io", help="1: 20 descargas secuenciales vs concurrentes")
    p_io.add_argument("--reales", action="store_true", help="usar 20 sitios reales")
    p_io.add_argument("--repeticiones", type=int, default=3)
    p_io.add_argument("--lento", default="http://lento:8001",
                      help="URL del servidor lento VISTA DESDE LA API (default %(default)s)")

    p_loop = sub.add_parser("loop", help="2: latencia de la API durante un hash pesado")
    p_loop.add_argument("--iteraciones", type=int, default=8_000_000)

    p_techo = sub.add_parser("techo", help="3: subir la carga hasta que se degrade")
    p_techo.add_argument("--tipo", choices=["esperar", "hashear"], default="esperar")
    p_techo.add_argument("--niveles", default="1,2,4,8,16,32,64")
    p_techo.add_argument("--segundos", type=float, default=1.0)
    p_techo.add_argument("--iteraciones", type=int, default=1_000_000)

    args = parser.parse_args()
    API = args.api.rstrip("/")
    {"io": medir_io, "loop": medir_loop, "techo": medir_techo}[args.medicion](args)


if __name__ == "__main__":
    main()
