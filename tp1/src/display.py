#!/usr/bin/env python3
"""
display.py - TUI del monitor (patrón curses).

Dividido a propósito en dos capas:

  1. LÓGICA PURA (EstadoUI, procesar_tecla, filtrar_y_ordenar, ...): no
     tocan curses para nada, reciben datos y devuelven datos. Se pueden
     testear con un intérprete de Python normal, sin terminal interactiva
     de por medio -- clave para poder probarlas antes de confiar en el
     dibujado.

  2. RENDERIZADO (renderizar, pedir_texto, bucle_ui): acá sí se usa
     curses. bucle_ui es el loop principal de la TUI; lo llama main.py
     con curses.wrapper(), que garantiza que la terminal se restaura
     aunque el programa explote con una excepción.

Solo la vista "Resumen" tiene un analizador real detrás (Fase 2/3). Las
otras 6 ya están completamente navegables -- cambian de vista, aceptan
ajustar su intervalo, etc. -- pero muestran un cartel de "pendiente"
hasta que la Fase 5 les conecte un analizador de verdad.
"""
import curses
import time


# Metadata de las 7 vistas obligatorias: número, teclas que la activan,
# la clave con la que el analizador correspondiente escribe en el
# snapshot (Manager.dict), nombre para mostrar, e intervalo mínimo (de
# la tabla de la consigna -- estos mínimos NO son configurables por el
# usuario, son parte del enunciado).
VISTAS = [
    {"numero": 1, "teclas": ("1", "r"), "clave": "resumen",    "nombre": "Resumen",            "intervalo_min": 0.5},
    {"numero": 2, "teclas": ("2", "m"), "clave": "memoria",    "nombre": "Memoria",             "intervalo_min": 1.0},
    {"numero": 3, "teclas": ("3", "f"), "clave": "fds",        "nombre": "File Descriptors",    "intervalo_min": 2.0},
    {"numero": 4, "teclas": ("4", "t"), "clave": "threads",    "nombre": "Threads",             "intervalo_min": 0.5},
    {"numero": 5, "teclas": ("5", "s"), "clave": "senales",    "nombre": "Señales",             "intervalo_min": 5.0},
    {"numero": 6, "teclas": ("6", "p"), "clave": "scheduling", "nombre": "Scheduling",          "intervalo_min": 5.0},
    {"numero": 7, "teclas": ("7", "g"), "clave": "sistema",    "nombre": "Sistema global",      "intervalo_min": 1.0},
]

ORDEN_OPCIONES = ["cpu", "rss", "pid"]
# A qué campo del dict de cada fila corresponde cada opción de orden, y
# si el orden es descendente (mayor primero). "rss" todavía no existe en
# ninguna fila real (lo trae el analizador de Memoria, Fase 5) -- el
# .get(campo, 0) en ordenar_filas() hace que mientras tanto sea un no-op
# en vez de romper.
CAMPO_ORDEN = {
    "cpu": ("cpu_pct", True),
    "rss": ("VmRSS", True),
    "pid": ("pid", False),
}

INTERVALO_PASO = 0.5
INTERVALO_MAX = 30.0


class EstadoUI:
    """Estado local de la interfaz. Vive solo en el proceso de display,
    no se comparte con nadie -- por eso es una clase común y no un
    Manager.dict()."""

    def __init__(self, vista_inicial="resumen", filtro_comando="", filtro_usuario="", orden="cpu"):
        self.vista_activa = vista_inicial
        self.indice_seleccionado = 0
        self.pid_pineado = None
        # Vienen de config.json ("filtros_default") -- se pueden cambiar
        # en caliente con /, u y c una vez arrancado el programa, esto
        # solo define el punto de partida.
        self.filtro_comando = filtro_comando
        self.filtro_usuario = filtro_usuario
        self.orden = orden if orden in ORDEN_OPCIONES else "cpu"
        self.mostrar_ayuda = False


def vista_por_clave(clave):
    """VISTAS[i] cuya clave coincide, o None."""
    for vista in VISTAS:
        if vista["clave"] == clave:
            return vista
    return None


def vista_por_tecla(caracter):
    """VISTAS[i] cuya lista de teclas incluye este caracter (ya en
    minúscula), o None si el caracter no activa ninguna vista."""
    for vista in VISTAS:
        if caracter in vista["teclas"]:
            return vista
    return None


def obtener_filas(snapshot, clave_vista):
    """
    Extrae la lista de filas (datos por proceso) que el analizador de
    `clave_vista` haya escrito en el snapshot. Si esa clave todavía no
    existe (analizador no implementado, o implementado pero sin su
    primera pasada todavía), devuelve None -- distinto de [] (vista
    implementada pero sin resultados, ej. filtro no matchea nada).
    """
    entrada = snapshot.get(clave_vista)
    if entrada is None:
        return None
    return entrada.get("datos", [])


def filtrar_y_ordenar(filas, estado):
    """
    Aplica filtro_comando / filtro_usuario (substring, case-insensitive)
    y el orden activo. Pura -- no muta `estado`, no toca curses.
    """
    resultado = filas

    if estado.filtro_comando:
        objetivo = estado.filtro_comando.lower()
        resultado = [f for f in resultado if objetivo in str(f.get("comando", "")).lower()]

    if estado.filtro_usuario:
        objetivo = estado.filtro_usuario.lower()
        resultado = [f for f in resultado if objetivo in str(f.get("usuario", "")).lower()]

    campo, descendente = CAMPO_ORDEN[estado.orden]
    resultado = sorted(resultado, key=lambda f: f.get(campo, 0), reverse=descendente)

    return resultado


def sincronizar_seleccion_pineada(estado, filas):
    """
    Si hay un PID pineado, hace que indice_seleccionado lo siga aunque
    `filas` haya cambiado de orden entre refrescos -- eso es justamente
    lo que pide la consigna con "Pin del proceso seleccionado (no cambia
    aunque cambie el orden)". Si el proceso pineado ya no existe (murió),
    se despinea solo en vez de quedar apuntando a nada.
    """
    if estado.pid_pineado is None:
        if estado.indice_seleccionado >= len(filas):
            estado.indice_seleccionado = max(0, len(filas) - 1)
        return

    for i, fila in enumerate(filas):
        if fila.get("pid") == estado.pid_pineado:
            estado.indice_seleccionado = i
            return

    # El proceso pineado ya no está en esta pasada -- se despinea.
    estado.pid_pineado = None
    estado.indice_seleccionado = min(estado.indice_seleccionado, max(0, len(filas) - 1))


def procesar_tecla(estado, tecla, intervalos, filas):
    """
    Aplica el efecto de una tecla sobre `estado` (y, para +/-, sobre el
    Value de intervalo correspondiente). No toca curses -- se testea con
    un entero cualquiera como "tecla", sin pantalla real.

    Devuelve uno de:
      None               -- ya se resolvió acá, no hace falta más nada
      "salir"             -- el usuario pidió salir (tecla 'q')
      "pedir_comando"      -- el usuario pidió filtrar por comando ('/'),
                              el LOOP (que sí tiene curses) debe pedir el
                              texto y guardarlo en estado.filtro_comando
      "pedir_usuario"      -- ídem para 'u' / filtro por usuario
    """
    if tecla == -1:
        return None

    # Teclas especiales de curses (flechas, etc.) vienen como enteros
    # >255; el resto son códigos ASCII de caracteres imprimibles.
    caracter = chr(tecla).lower() if 0 <= tecla < 256 else None

    if caracter == "q":
        return "salir"

    if caracter in ("h", "?"):
        estado.mostrar_ayuda = not estado.mostrar_ayuda
        return None

    if estado.mostrar_ayuda:
        # Con la ayuda abierta, cualquier tecla la cierra (salvo que ya
        # se haya manejado arriba con h/?). Evita que se procesen
        # navegación/filtros "por accidente" mientras se lee la ayuda.
        estado.mostrar_ayuda = False
        return None

    vista = vista_por_tecla(caracter) if caracter else None
    if vista is not None:
        if estado.vista_activa != vista["clave"]:
            estado.vista_activa = vista["clave"]
            if estado.pid_pineado is None:
                estado.indice_seleccionado = 0
        return None

    if tecla == curses.KEY_UP:
        estado.indice_seleccionado = max(0, estado.indice_seleccionado - 1)
        return None

    if tecla == curses.KEY_DOWN:
        if filas:
            estado.indice_seleccionado = min(len(filas) - 1, estado.indice_seleccionado + 1)
        return None

    if tecla in (curses.KEY_ENTER, 10, 13):
        if filas and 0 <= estado.indice_seleccionado < len(filas):
            pid_actual = filas[estado.indice_seleccionado]["pid"]
            estado.pid_pineado = None if estado.pid_pineado == pid_actual else pid_actual
        return None

    if caracter == "/":
        return "pedir_comando"

    if caracter == "u":
        return "pedir_usuario"

    if caracter == "c":
        i = ORDEN_OPCIONES.index(estado.orden)
        estado.orden = ORDEN_OPCIONES[(i + 1) % len(ORDEN_OPCIONES)]
        return None

    if caracter in ("+", "="):  # "=" porque en la mayoría de los teclados es la misma tecla que "+"
        valor = intervalos[estado.vista_activa]
        valor.value = min(INTERVALO_MAX, valor.value + INTERVALO_PASO)
        return None

    if caracter == "-":
        vista_activa = vista_por_clave(estado.vista_activa)
        valor = intervalos[estado.vista_activa]
        valor.value = max(vista_activa["intervalo_min"], valor.value - INTERVALO_PASO)
        return None

    return None


# ---------------------------------------------------------------------------
# Renderizado (curses de verdad, a partir de acá)
# ---------------------------------------------------------------------------

# Config de columnas por vista, para no repetir 6 funciones de formateo
# casi idénticas. Cada entrada: (etiqueta, campo_del_dict, ancho, fmt).
# "final_campo"/"final_etiqueta" es la columna de texto libre al final
# (comando, o el nombre del thread en la vista Threads).
COLUMNAS_POR_VISTA = {
    "resumen": {
        "base": [("PID", "pid", 7, str), ("PPID", "ppid", 7, str),
                  ("USUARIO", "usuario", 10, str), ("EST", "estado", 3, str),
                  ("CPU%", "cpu_pct", 6, lambda v: f"{v:.1f}"), ("THR", "num_threads", 4, str)],
        "verbose_extra": [("UID", "uid", 5, str), ("GID", "gid", 5, str),
                           ("UTIME", "utime", 7, str), ("STIME", "stime", 7, str)],
        "final_campo": "comando", "final_etiqueta": "COMANDO",
    },
    "memoria": {
        "base": [("PID", "pid", 7, str), ("USUARIO", "usuario", 10, str),
                  ("RSS(kB)", "VmRSS", 9, str), ("VSZ(kB)", "VmSize", 9, str),
                  ("DATA(kB)", "VmData", 9, str), ("MINFLT", "minflt", 8, str), ("MAJFLT", "majflt", 8, str)],
        "verbose_extra": [("EXE(kB)", "VmExe", 8, str), ("LIB(kB)", "VmLib", 8, str),
                           ("HWM(kB)", "VmHWM", 8, str), ("SWAP(kB)", "VmSwap", 9, str)],
        "final_campo": "comando", "final_etiqueta": "COMANDO",
    },
    "fds": {
        "base": [("PID", "pid", 7, str), ("USUARIO", "usuario", 10, str), ("TOTAL", "total_fds", 6, str)],
        "verbose_extra": [],  # el detalle de cada FD va en el panel de abajo, no en la tabla
        "final_campo": "comando", "final_etiqueta": "COMANDO",
    },
    "threads": {
        "base": [("TID", "tid", 7, str), ("PID", "pid_proceso", 7, str),
                  ("EST", "estado", 3, str), ("CPU%", "cpu_pct", 6, lambda v: f"{v:.1f}")],
        "verbose_extra": [("VOL_CS", "ctxt_switches_voluntarios", 7, str),
                           ("INV_CS", "ctxt_switches_involuntarios", 7, str)],
        "final_campo": "nombre", "final_etiqueta": "NOMBRE",
    },
    "senales": {
        "base": [("PID", "pid", 7, str), ("USUARIO", "usuario", 10, str),
                  ("BLOQ", "bloqueadas", 5, lambda v: str(len(v))),
                  ("IGN", "ignoradas", 5, lambda v: str(len(v))),
                  ("HANDLER", "con_handler", 8, lambda v: str(len(v))),
                  ("PEND", "pendientes", 5, lambda v: str(len(v)))],
        "verbose_extra": [],
        "final_campo": "comando", "final_etiqueta": "COMANDO",
    },
    "scheduling": {
        "base": [("PID", "pid", 7, str), ("USUARIO", "usuario", 10, str),
                  ("NICE", "nice", 5, str), ("PRIO", "priority", 5, str),
                  ("POLICY", "policy", 12, str), ("SID", "sid", 7, str), ("PGID", "pgid", 7, str)],
        "verbose_extra": [("VOL_CS", "ctxt_switches_voluntarios", 7, str),
                           ("INV_CS", "ctxt_switches_involuntarios", 7, str)],
        "final_campo": "comando", "final_etiqueta": "COMANDO",
    },
}


def _addstr_seguro(stdscr, y, x, texto, attr=0):
    """
    stdscr.addstr() tira curses.error si se escribe fuera de la ventana
    (el caso típico: la esquina inferior derecha exacta -- una rareza
    histórica de curses). Envolver cada escritura evita que un resize de
    terminal tire abajo todo el monitor por una excepción de dibujado.
    """
    altura, ancho = stdscr.getmaxyx()
    if y < 0 or y >= altura or x >= ancho:
        return
    try:
        stdscr.addstr(y, x, texto[:max(0, ancho - x - 1)], attr)
    except curses.error:
        pass


def _titulo_columnas(config, verbose):
    columnas = config["base"] + (config["verbose_extra"] if verbose else [])
    return "".join(f"{etq:>{ancho}} " for etq, _campo, ancho, _fmt in columnas) + " " + config["final_etiqueta"]


def _formatear_fila(fila, config, verbose):
    columnas = config["base"] + (config["verbose_extra"] if verbose else [])
    partes = [f"{fmt(fila.get(campo, 0)):>{ancho}}" for _etq, campo, ancho, fmt in columnas]
    texto_final = str(fila.get(config["final_campo"], ""))
    return " ".join(partes) + "  " + texto_final


# --- Panel de detalle: una función por vista, cada una devuelve una
# lista de líneas de texto para el proceso/fila seleccionada. ---

def _detalle_resumen(f):
    return [
        f"PPID: {f['ppid']}   UID: {f['uid']} ({f['usuario']})   GID: {f['gid']}",
        f"Threads: {f['num_threads']}   CPU%: {f['cpu_pct']:.1f}   utime: {f['utime']}   stime: {f['stime']}",
        f"Comando: {f['comando']}",
    ]


def _detalle_memoria(f):
    return [
        f"VmSize: {f['VmSize']} kB   VmRSS: {f['VmRSS']} kB   VmData: {f['VmData']} kB   VmStk: {f['VmStk']} kB",
        f"VmExe: {f['VmExe']} kB   VmLib: {f['VmLib']} kB   VmHWM: {f['VmHWM']} kB   VmSwap: {f['VmSwap']} kB",
        f"minflt: {f['minflt']}   majflt: {f['majflt']}",
        "Segmentos (bytes): " + ", ".join(f"{k}={v}" for k, v in f["segmentos"].items()),
        f"Comando: {f['comando']}",
    ]


def _detalle_fds(f):
    conteo_txt = ", ".join(f"{k}={v}" for k, v in f["conteo_por_tipo"].items()) or "(ninguno)"
    lineas = [f"Total FDs: {f['total_fds']}   Por tipo: {conteo_txt}", f"Comando: {f['comando']}"]
    for fd in f["fds"][:5]:
        lineas.append(f"  fd {fd['fd']:>3} ({fd['tipo']}) -> {fd['destino']}")
    if len(f["fds"]) > 5:
        lineas.append(f"  ... y {len(f['fds']) - 5} más")
    return lineas


def _detalle_threads(f):
    return [
        f"Proceso dueño (PID): {f['pid_proceso']}   Estado: {f['estado_desc']}",
        f"CPU%: {f['cpu_pct']:.1f}   ctxt vol: {f['ctxt_switches_voluntarios']}   "
        f"ctxt inv: {f['ctxt_switches_involuntarios']}",
        f"Nombre del thread: {f['nombre']}",
    ]


def _detalle_senales(f):
    def fmt(lista):
        return ", ".join(lista) if lista else "(ninguna)"
    return [
        f"Bloqueadas: {fmt(f['bloqueadas'])}",
        f"Ignoradas: {fmt(f['ignoradas'])}",
        f"Con handler propio: {fmt(f['con_handler'])}",
        f"Pendientes: {fmt(f['pendientes'])}   Pendientes de grupo: {fmt(f['pendientes_grupo'])}",
        f"Comando: {f['comando']}",
    ]


def _detalle_scheduling(f):
    return [
        f"Nice: {f['nice']}   Priority: {f['priority']}   Policy: {f['policy']}   RT prio: {f['rt_priority']}",
        f"CPU affinity: {f['cpu_affinity']}",
        f"ctxt vol: {f['ctxt_switches_voluntarios']}   ctxt inv: {f['ctxt_switches_involuntarios']}   "
        f"SID: {f['sid']}   PGID: {f['pgid']}",
        f"Comando: {f['comando']}",
    ]


DETALLE_POR_VISTA = {
    "resumen": _detalle_resumen,
    "memoria": _detalle_memoria,
    "fds": _detalle_fds,
    "threads": _detalle_threads,
    "senales": _detalle_senales,
    "scheduling": _detalle_scheduling,
}


def _renderizar_sistema(stdscr, entrada):
    """
    Render especial para la vista Sistema global: no es una tabla de
    procesos con selección, es un panel fijo con los datos agregados que
    escribió analizadores/sistema.py (ver ese módulo para el porqué de
    esta diferencia de forma).
    """
    d = entrada["datos"]
    y = 2

    cpu = d["cpu_pct"]
    _addstr_seguro(stdscr, y, 0,
                    f"CPU global -- user: {cpu['user']:.1f}%  system: {cpu['system']:.1f}%  "
                    f"idle: {cpu['idle']:.1f}%  iowait: {cpu['iowait']:.1f}%")
    y += 2

    la = d["loadavg"]
    _addstr_seguro(stdscr, y, 0,
                    f"Load average -- 1m: {la['load1']:.2f}  5m: {la['load5']:.2f}  15m: {la['load15']:.2f}   "
                    f"procesos corriendo: {la['procesos_corriendo']}/{la['procesos_totales']}")
    y += 2

    m = d["meminfo"]

    def mb(clave):
        return m.get(clave, 0) / 1024

    _addstr_seguro(stdscr, y, 0,
                    f"Memoria -- Total: {mb('MemTotal'):.0f} MB   Libre: {mb('MemFree'):.0f} MB   "
                    f"Disponible: {mb('MemAvailable'):.0f} MB")
    y += 1
    _addstr_seguro(stdscr, y, 0,
                    f"           Buffers: {mb('Buffers'):.0f} MB   Cached: {mb('Cached'):.0f} MB   "
                    f"Swap libre: {mb('SwapFree'):.0f}/{mb('SwapTotal'):.0f} MB")
    y += 2

    c = d["conteos_procesos"]
    por_estado_txt = ", ".join(f"{k}={v}" for k, v in c["por_estado"].items())
    _addstr_seguro(stdscr, y, 0,
                    f"Procesos -- total: {c['total_procesos']}   threads totales: {c['total_threads']}   "
                    f"zombies: {c['zombies']}   por estado: {por_estado_txt}")
    y += 2

    horas = int(d["uptime_seg"] // 3600)
    minutos = int((d["uptime_seg"] % 3600) // 60)
    boot_legible = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(d["btime"]))
    _addstr_seguro(stdscr, y, 0, f"Uptime: {horas}h {minutos}m   Boot time: {boot_legible}")
    y += 2

    _addstr_seguro(stdscr, y, 0, "Top 3 por CPU%:", curses.A_UNDERLINE)
    y += 1
    for p in d["top_cpu"]:
        comando = p["comando"][:60]
        _addstr_seguro(stdscr, y, 2, f"PID {p['pid']:>7} {p['usuario']:<10} {p['valor']:>6.1f}%  {comando}")
        y += 1
    y += 1

    _addstr_seguro(stdscr, y, 0, "Top 3 por RSS:", curses.A_UNDERLINE)
    y += 1
    for p in d["top_mem"]:
        comando = p["comando"][:60]
        _addstr_seguro(stdscr, y, 2, f"PID {p['pid']:>7} {p['usuario']:<10} {p['valor']:>9} kB  {comando}")
        y += 1


def renderizar(stdscr, estado, snapshot, filas, intervalos, verbose):
    """Dibuja un frame completo. No devuelve nada -- efecto de lado
    (curses) puro."""
    stdscr.erase()
    altura, ancho = stdscr.getmaxyx()

    if estado.mostrar_ayuda:
        _renderizar_ayuda(stdscr)
        stdscr.refresh()
        return

    vista = vista_por_clave(estado.vista_activa)
    valor_intervalo = intervalos[estado.vista_activa].value

    # --- Encabezado ---
    filtros = []
    if estado.filtro_comando:
        filtros.append(f"comando~'{estado.filtro_comando}'")
    if estado.filtro_usuario:
        filtros.append(f"usuario~'{estado.filtro_usuario}'")
    filtros_txt = f" | filtros: {', '.join(filtros)}" if filtros else ""

    encabezado = (f"[{vista['numero']}] {vista['nombre']}  "
                  f"(refresco {valor_intervalo:.1f}s, orden={estado.orden}, "
                  f"verbose={verbose}){filtros_txt}")
    _addstr_seguro(stdscr, 0, 0, encabezado, curses.A_BOLD)

    entrada = snapshot.get(estado.vista_activa)

    if entrada is None:
        _addstr_seguro(stdscr, 2, 2,
                        f"Analizador de '{vista['nombre']}' todavía no implementado.")
        _renderizar_pie(stdscr, estado)
        stdscr.refresh()
        return

    if estado.vista_activa == "sistema":
        _renderizar_sistema(stdscr, entrada)
        _renderizar_pie(stdscr, estado)
        stdscr.refresh()
        return

    if not filas:
        mensaje = ("(sin procesos que coincidan con el filtro)" if entrada.get("datos") else
                   "(esperando la primera pasada del analizador...)")
        _addstr_seguro(stdscr, 2, 2, mensaje)
        _renderizar_pie(stdscr, estado)
        stdscr.refresh()
        return

    # --- Tabla de procesos (genérica, según COLUMNAS_POR_VISTA) ---
    config = COLUMNAS_POR_VISTA[estado.vista_activa]
    _addstr_seguro(stdscr, 2, 0, _titulo_columnas(config, verbose), curses.A_UNDERLINE)

    altura_detalle = 7  # líneas reservadas abajo para el panel de detalle
    filas_visibles = max(0, altura - 2 - altura_detalle - 1)

    inicio = max(0, estado.indice_seleccionado - filas_visibles // 2)
    for offset, fila in enumerate(filas[inicio:inicio + filas_visibles]):
        indice_real = inicio + offset
        y = 3 + offset
        attr = curses.A_REVERSE if indice_real == estado.indice_seleccionado else 0
        if fila.get("pid") == estado.pid_pineado:
            attr |= curses.A_BOLD
        _addstr_seguro(stdscr, y, 0, _formatear_fila(fila, config, verbose), attr)

    # --- Panel de detalle de la fila seleccionada ---
    y_detalle = altura - altura_detalle
    if 0 <= estado.indice_seleccionado < len(filas):
        seleccionado = filas[estado.indice_seleccionado]
        _addstr_seguro(stdscr, y_detalle, 0, "-" * min(ancho, 78), curses.A_DIM)
        pineado_txt = " [PINEADO]" if seleccionado.get("pid") == estado.pid_pineado else ""
        _addstr_seguro(stdscr, y_detalle + 1, 0, f"Detalle{pineado_txt}", curses.A_BOLD)
        detalle_fn = DETALLE_POR_VISTA.get(estado.vista_activa)
        if detalle_fn:
            for i, linea in enumerate(detalle_fn(seleccionado)):
                _addstr_seguro(stdscr, y_detalle + 2 + i, 0, linea)

    _renderizar_pie(stdscr, estado)
    stdscr.refresh()


def _renderizar_pie(stdscr, estado):
    altura, _ = stdscr.getmaxyx()
    pie = "1-7/rmftspg vista | ↑↓ navegar | Enter pin | / filtro cmd | u filtro user | c orden | +/- intervalo | q salir | h ayuda"
    _addstr_seguro(stdscr, altura - 1, 0, pie, curses.A_DIM)


def _renderizar_ayuda(stdscr):
    lineas = [
        "AYUDA -- cualquier tecla cierra este panel",
        "",
        "1-7 / r m f t s p g   Cambiar de vista",
        "flechas arriba/abajo  Navegar la lista de procesos",
        "Enter                 Pinear/despinear el proceso seleccionado",
        "/                     Filtrar por nombre de comando",
        "u                     Filtrar por usuario",
        "c                     Rotar orden: CPU% / RSS / PID",
        "+ / -                 Ajustar el intervalo de refresco de la vista activa",
        "q                     Salir limpiamente",
        "h / ?                 Mostrar/ocultar esta ayuda",
    ]
    for i, linea in enumerate(lineas):
        _addstr_seguro(stdscr, 1 + i, 2, linea)


def pedir_texto(stdscr, prompt):
    """
    Prompt de texto bloqueante sobre la última línea de la pantalla
    (para '/' y 'u'). Habilita eco y cursor visible solo mientras dura
    el prompt, y los vuelve a apagar al salir -- son globales de curses,
    si no se restauran quedan "pisando" el resto de la TUI.
    """
    altura, ancho = stdscr.getmaxyx()
    curses.echo()
    curses.curs_set(1)
    stdscr.timeout(-1)  # bloqueante mientras se escribe el filtro
    try:
        _addstr_seguro(stdscr, altura - 1, 0, " " * (ancho - 1))
        _addstr_seguro(stdscr, altura - 1, 0, prompt)
        stdscr.refresh()
        texto = stdscr.getstr(altura - 1, len(prompt)).decode(errors="replace")
    finally:
        curses.noecho()
        curses.curs_set(0)
        stdscr.timeout(150)
    return texto.strip()
