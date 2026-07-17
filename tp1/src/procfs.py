#!/usr/bin/env python3
"""
procfs.py - Lectura de /proc para el Monitor de Procesos y Threads (TP1).

Funciones PURAS: reciben un PID (y a veces un TID), devuelven datos en
estructuras Python (dicts, listas, strings). No tienen estado propio y no
hacen multiprocessing — eso es responsabilidad de los analizadores que van
a usar este módulo como "motor" de lectura.

Todas las funciones que leen /proc/<pid>/... pueden lanzar
`FileNotFoundError` o `ProcessLookupError` si el proceso terminó justo entre
que lo listamos y que lo leemos (race condition normal con /proc: un PID es
una foto de un instante). Los analizadores deben capturar esas excepciones
y simplemente ignorar ese PID en esa pasada.
"""
import os
import pwd
import signal


# jiffies por segundo (típicamente 100 en Linux). utime/stime de
# /proc/<pid>/stat están en esta unidad.
CLK_TCK = os.sysconf("SC_CLK_TCK")

# Tamaño de página en bytes, útil para convertir páginas <-> bytes/KB
# (ej: RSS en /proc/<pid>/statm viene en páginas).
PAGE_SIZE = os.sysconf("SC_PAGE_SIZE")

# Códigos de estado de /proc/<pid>/stat campo 3 (man proc(5))
ESTADOS = {
    "R": "Running",
    "S": "Sleeping",
    "D": "Disk sleep (uninterruptible)",
    "T": "Stopped",
    "t": "Tracing stop",
    "Z": "Zombie",
    "X": "Dead",
    "I": "Idle",
}

# /proc/<pid>/stat campo 41 (policy) -> nombre. Valores de sched.h.
POLICIES = {
    0: "SCHED_OTHER",
    1: "SCHED_FIFO",
    2: "SCHED_RR",
    3: "SCHED_BATCH",
    5: "SCHED_IDLE",
    6: "SCHED_DEADLINE",
}


# ---------------------------------------------------------------------------
# Listado de procesos y threads
# ---------------------------------------------------------------------------

def listar_pids():
    """
    Lista todos los PIDs activos, leyendo los nombres de entrada numéricos
    de /proc (cada proceso tiene una carpeta /proc/<pid>/).
    """
    pids = []
    for nombre in os.listdir("/proc"):
        if nombre.isdigit():
            pids.append(int(nombre))
    return sorted(pids)


def listar_threads(pid):
    """
    Lista los TIDs (threads/LWPs) de un proceso, leyendo
    /proc/<pid>/task/<tid>/ (cada thread tiene su propia subcarpeta).
    """
    tids = []
    for nombre in os.listdir(f"/proc/{pid}/task"):
        if nombre.isdigit():
            tids.append(int(nombre))
    return sorted(tids)


# ---------------------------------------------------------------------------
# stat / status / cmdline / comm (proceso o thread)
# ---------------------------------------------------------------------------

def _ruta_base(pid, tid=None):
    """/proc/<pid>/ para el proceso, o /proc/<pid>/task/<tid>/ para un thread."""
    if tid is None:
        return f"/proc/{pid}"
    return f"/proc/{pid}/task/{tid}"


def leer_stat(pid, tid=None):
    """
    Parsea /proc/<pid>/stat (o /proc/<pid>/task/<tid>/stat si se pasa tid,
    que tiene EXACTAMENTE el mismo formato) y devuelve los campos que usa
    este TP.

    Formato: "<pid> (<comm>) <state> <ppid> <pgrp> <session> ... <policy> ..."

    El campo 'comm' (nombre del ejecutable, campo 2) viene entre paréntesis
    y PUEDE contener espacios o paréntesis (ej: nombres de hilos de kernel
    como "(idle_inject/0)"). Por eso NO se puede hacer un simple .split():
    hay que ubicar el PRIMER '(' y el ÚLTIMO ')' para extraer 'comm' bien,
    y recién de ahí en adelante son campos numéricos separados por espacios.

    Numeración de campos (1-indexed, según man proc(5)):
      3 state, 4 ppid, 5 pgrp, 6 session, 10 minflt, 11 cminflt,
      12 majflt, 13 cmajflt, 14 utime, 15 stime, 18 priority, 19 nice,
      20 num_threads, 22 starttime, 40 rt_priority, 41 policy
    """
    ruta = _ruta_base(pid, tid)
    with open(f"{ruta}/stat") as f:
        contenido = f.read()

    inicio = contenido.index("(")
    fin = contenido.rindex(")")
    comm = contenido[inicio + 1:fin]
    resto = contenido[fin + 2:].split()  # +2 para saltear ") "

    # resto[0] = campo 3 (state) => resto[i] = campo (i + 3)
    return {
        "pid": pid,
        "tid": tid if tid is not None else pid,
        "comm": comm,
        "state": resto[0],
        "ppid": int(resto[1]),
        "pgrp": int(resto[2]),
        "session": int(resto[3]),
        "minflt": int(resto[6]),        # campo 10
        "cminflt": int(resto[7]),       # campo 11
        "majflt": int(resto[8]),        # campo 12
        "cmajflt": int(resto[9]),       # campo 13
        "utime": int(resto[11]),        # campo 14
        "stime": int(resto[12]),        # campo 15
        "priority": int(resto[15]),     # campo 18
        "nice": int(resto[16]),         # campo 19
        "num_threads": int(resto[17]),  # campo 20
        "starttime": int(resto[19]),    # campo 22
        "rt_priority": int(resto[37]),  # campo 40
        "policy": int(resto[38]),       # campo 41
    }


def leer_status(pid, tid=None):
    """
    Parsea /proc/<pid>/status (o el de un thread): un archivo de líneas
    "Clave:\tValor".

    Devuelve un dict {clave: valor_string} SIN tipar — cada analizador
    convierte lo que necesita (la mayoría son enteros o listas de enteros
    separados por tabs/espacios, ej: "Uid:\t0\t0\t0\t0").
    """
    ruta = _ruta_base(pid, tid)
    datos = {}
    with open(f"{ruta}/status") as f:
        for linea in f:
            clave, _, valor = linea.partition(":")
            datos[clave.strip()] = valor.strip()
    return datos


def leer_cmdline(pid):
    """
    Comando completo desde /proc/<pid>/cmdline: los argumentos vienen
    separados por bytes NUL (\\x00), no por espacios.

    Si está vacío (típico de kernel threads, que no tienen argv), se cae
    al 'comm' de /proc/<pid>/stat entre corchetes — igual que hace `ps`
    para mostrar, por ejemplo, "[kworker/0:1]".
    """
    with open(f"/proc/{pid}/cmdline", "rb") as f:
        contenido = f.read()

    if not contenido:
        return f"[{leer_stat(pid)['comm']}]"

    partes = contenido.split(b"\x00")
    return " ".join(p.decode(errors="replace") for p in partes if p)


def leer_comm(pid, tid=None):
    """
    Nombre corto del proceso/thread desde /proc/<pid>/comm (o el del
    thread). A diferencia del 'comm' que sale de /proc/<pid>/stat, este
    archivo no requiere parsear paréntesis y es la fuente recomendada por
    la consigna para el nombre de cada thread en la vista Threads.
    """
    ruta = _ruta_base(pid, tid)
    with open(f"{ruta}/comm") as f:
        return f.read().strip()


def nombre_usuario(uid):
    """uid (int) -> nombre de usuario, o el uid como string si no existe."""
    try:
        return pwd.getpwuid(uid).pw_name
    except KeyError:
        return str(uid)


def estado_legible(codigo):
    """Código de un solo caracter (R/S/D/T/t/Z/X/I) -> descripción."""
    return ESTADOS.get(codigo, codigo)


def calcular_cpu_pct(utime_actual, stime_actual, utime_anterior, stime_anterior, delta_segundos):
    """
    % de CPU usado por un proceso (o thread) entre dos lecturas de
    /proc/<pid>/stat.

    (utime + stime) está en "jiffies" (CLK_TCK por segundo, típicamente
    100). El % se normaliza a UN core: un proceso con varios threads
    corriendo en paralelo en distintos cores puede superar el 100%
    (igual que en `top`/`htop`).

    Si delta_segundos <= 0 (primera lectura, todavía sin "anterior"),
    devuelve 0.0.
    """
    if delta_segundos <= 0:
        return 0.0
    jiffies_delta = (utime_actual + stime_actual) - (utime_anterior + stime_anterior)
    segundos_cpu = jiffies_delta / CLK_TCK
    return 100.0 * segundos_cpu / delta_segundos


def identificar_proceso(pid):
    """
    Helper chico compartido por los analizadores que no necesitan todo
    info_resumen(), solo identificar de quién es el proceso: pid, usuario
    y comando completo. Evita repetir "leer status, sacar Uid, resolver
    nombre_usuario, leer cmdline" en Memoria/FDs/Señales/Scheduling.
    """
    status = leer_status(pid)
    uid = int(status.get("Uid", "0").split()[0])
    return {
        "pid": pid,
        "usuario": nombre_usuario(uid),
        "comando": leer_cmdline(pid),
    }


def info_resumen(pid):
    """
    Combina stat + status + cmdline en un solo dict con los datos de la
    vista "Resumen" (excepto CPU%, que requiere DOS lecturas en el tiempo
    y se calcula en el analizador, no acá).
    """
    stat = leer_stat(pid)
    status = leer_status(pid)

    uid = int(status.get("Uid", "0").split()[0])
    gid = int(status.get("Gid", "0").split()[0])

    return {
        "pid": pid,
        "ppid": stat["ppid"],
        "uid": uid,
        "usuario": nombre_usuario(uid),
        "gid": gid,
        "estado": stat["state"],
        "estado_desc": estado_legible(stat["state"]),
        "comando": leer_cmdline(pid),
        "num_threads": stat["num_threads"],
        "utime": stat["utime"],
        "stime": stat["stime"],
    }


# ---------------------------------------------------------------------------
# Memoria
# ---------------------------------------------------------------------------

# Claves de /proc/<pid>/status que la vista Memoria necesita tal cual
# (vienen como "123456 kB", en kB).
_CLAVES_VM = ("VmSize", "VmRSS", "VmData", "VmStk", "VmExe", "VmLib",
              "VmHWM", "VmSwap")


def info_memoria_status(pid):
    """
    Extrae de /proc/<pid>/status los campos VmSize/VmRSS/.../VmSwap que
    pide la vista Memoria, convertidos de "123456 kB" a int (kB).
    Si un proceso no tiene alguna clave (raro, pero puede pasar con
    kernel threads), la deja en 0.
    """
    status = leer_status(pid)
    datos = {}
    for clave in _CLAVES_VM:
        valor = status.get(clave, "0 kB")
        datos[clave] = int(valor.split()[0])
    return datos


def leer_maps(pid):
    """
    Parsea /proc/<pid>/maps: una línea por región de memoria mapeada.

    Formato de línea:
        "start-end perms offset dev inode pathname"
    ej: "00400000-00452000 r-xp 00000000 08:02 1234  /bin/cat"
        "7f2a3c000000-7f2a3c021000 rw-p 00000000 00:00 0  [heap]"

    Devuelve una lista de dicts {inicio, fin, tamanio, perms, pathname}.
    El pathname puede venir vacío (mapeo anónimo) o ser un pseudo-nombre
    entre corchetes ([heap], [stack], [vdso], etc.).
    """
    regiones = []
    with open(f"/proc/{pid}/maps") as f:
        for linea in f:
            partes = linea.split(maxsplit=5)
            rango, perms = partes[0], partes[1]
            pathname = partes[5].strip() if len(partes) == 6 else ""

            inicio_hex, fin_hex = rango.split("-")
            inicio, fin = int(inicio_hex, 16), int(fin_hex, 16)

            regiones.append({
                "inicio": inicio,
                "fin": fin,
                "tamanio": fin - inicio,
                "perms": perms,
                "pathname": pathname,
            })
    return regiones


def agrupar_memoria(pid):
    """
    Agrupa las regiones de /proc/<pid>/maps en las categorías que pide la
    consigna: text/data/heap/stack/shared, sumando bytes por categoría.

    Criterio de clasificación:
      - pathname == "[heap]"           -> heap
      - pathname == "[stack]"          -> stack
      - perms[3] == 's'                -> shared (mapeo MAP_SHARED)
      - 'x' en perms y hay pathname    -> text (código ejecutable mapeado
                                           desde un archivo, ej. el binario
                                           o una .so)
      - resto (típicamente rw-p con o
        sin pathname)                  -> data
    """
    categorias = {"text": 0, "data": 0, "heap": 0, "stack": 0,
                  "shared": 0, "otros": 0}

    for region in leer_maps(pid):
        perms = region["perms"]
        pathname = region["pathname"]
        tam = region["tamanio"]

        if pathname == "[heap]":
            categorias["heap"] += tam
        elif pathname == "[stack]":
            categorias["stack"] += tam
        elif len(perms) >= 4 and perms[3] == "s":
            categorias["shared"] += tam
        elif "x" in perms and pathname and not pathname.startswith("["):
            categorias["text"] += tam
        elif pathname.startswith("[") and pathname not in ("[heap]", "[stack]"):
            categorias["otros"] += tam
        else:
            categorias["data"] += tam

    return categorias


# ---------------------------------------------------------------------------
# File descriptors
# ---------------------------------------------------------------------------

def inferir_tipo_fd(destino):
    """
    Infiere el tipo de un FD a partir de a dónde apunta su symlink en
    /proc/<pid>/fd/<n> (lo que devuelve os.readlink).

    Los FDs que no son archivos regulares tienen un destino "sintético"
    generado por el kernel, con un formato reconocible:
      socket:[12345]   -> socket
      pipe:[12345]     -> pipe
      anon_inode:[...] -> anon_inode (ej: eventfd, epoll)
      /dev/pts/...     -> tty
      cualquier otra ruta real -> file
    """
    if destino.startswith("socket:"):
        return "socket"
    if destino.startswith("pipe:"):
        return "pipe"
    if destino.startswith("anon_inode:"):
        return "anon_inode"
    if destino.startswith("/dev/pts/") or destino == "/dev/tty":
        return "tty"
    return "file"


def listar_fds(pid):
    """
    Lista los FDs abiertos de un proceso: número, destino (target del
    symlink) y tipo inferido.

    Un FD puede desaparecer entre el listdir() y el readlink() (el
    proceso lo cerró en el medio) — eso se resuelve por FD individual con
    OSError/FileNotFoundError, sin abortar el listado completo.
    """
    ruta = f"/proc/{pid}/fd"
    fds = []
    for nombre in os.listdir(ruta):
        try:
            destino = os.readlink(f"{ruta}/{nombre}")
        except OSError:
            destino = "?"
        fds.append({
            "fd": int(nombre),
            "destino": destino,
            "tipo": inferir_tipo_fd(destino),
        })
    return sorted(fds, key=lambda x: x["fd"])


# ---------------------------------------------------------------------------
# Señales
# ---------------------------------------------------------------------------

def decodificar_mascara_senales(mascara_hex):
    """
    Decodifica una máscara hexadecimal de 64 bits (SigBlk/SigIgn/SigCgt/
    SigPnd/ShdPnd de /proc/<pid>/status) a una lista de nombres de señal
    legibles.

    El bit N (1-indexed, bit 0 = señal 1 = SIGHUP) corresponde a la señal
    número N. Se recorre cada bit prendido y se mapea a través del enum
    `signal.Signals`; las señales de tiempo real (32-64) no tienen nombre
    fijo en todas las libc, así que se listan como "SIGRTMIN+k".
    """
    valor = int(mascara_hex, 16)
    nombres = []
    n = 1
    while valor:
        if valor & 1:
            try:
                nombres.append(signal.Signals(n).name)
            except ValueError:
                nombres.append(f"SIGRTMIN+{n - signal.SIGRTMIN}" if n >= signal.SIGRTMIN else f"señal {n}")
        valor >>= 1
        n += 1
    return nombres


def info_senales(pid):
    """
    Extrae y decodifica las 5 máscaras de señales que pide la consigna:
    SigBlk, SigIgn, SigCgt (por proceso), SigPnd (pendientes del proceso)
    y ShdPnd (pendientes compartidas del grupo de threads).
    """
    status = leer_status(pid)
    claves = {
        "bloqueadas": "SigBlk",
        "ignoradas": "SigIgn",
        "con_handler": "SigCgt",
        "pendientes": "SigPnd",
        "pendientes_grupo": "ShdPnd",
    }
    return {
        nombre: decodificar_mascara_senales(status.get(clave, "0"))
        for nombre, clave in claves.items()
    }


# ---------------------------------------------------------------------------
# Scheduling
# ---------------------------------------------------------------------------

def parsear_lista_cpus(texto):
    """
    Parsea el formato de Cpus_allowed_list de /proc/<pid>/status
    (ej: "0-2,5,7-8") a una lista plana de enteros [0, 1, 2, 5, 7, 8].
    """
    cpus = []
    texto = texto.strip()
    if not texto:
        return cpus
    for parte in texto.split(","):
        if "-" in parte:
            inicio, fin = parte.split("-")
            cpus.extend(range(int(inicio), int(fin) + 1))
        else:
            cpus.append(int(parte))
    return cpus


def info_scheduling(pid):
    """
    Combina stat + status para la vista Scheduling: nice, priority,
    policy (nombre legible), rt_priority, affinity, context switches y
    utime/stime crudos (para que el analizador calcule CPU% si quiere).
    """
    stat = leer_stat(pid)
    status = leer_status(pid)

    return {
        "nice": stat["nice"],
        "priority": stat["priority"],
        "policy": POLICIES.get(stat["policy"], f"desconocida({stat['policy']})"),
        "rt_priority": stat["rt_priority"],
        "cpu_affinity": parsear_lista_cpus(status.get("Cpus_allowed_list", "")),
        "ctxt_switches_voluntarios": int(status.get("voluntary_ctxt_switches", "0")),
        "ctxt_switches_involuntarios": int(status.get("nonvoluntary_ctxt_switches", "0")),
        "utime": stat["utime"],
        "stime": stat["stime"],
        "sid": stat["session"],
        "pgid": stat["pgrp"],
    }


# ---------------------------------------------------------------------------
# Sistema global
# ---------------------------------------------------------------------------

def leer_meminfo():
    """
    Parsea /proc/meminfo: líneas "Clave:    12345 kB" (a veces sin
    unidad, ej. HugePages_Total). Devuelve dict {clave: int_kb_o_valor}.
    """
    datos = {}
    with open("/proc/meminfo") as f:
        for linea in f:
            clave, _, valor = linea.partition(":")
            partes = valor.split()
            datos[clave.strip()] = int(partes[0]) if partes else 0
    return datos


def leer_loadavg():
    """
    Parsea /proc/loadavg: "0.10 0.05 0.01 2/456 12345"
    -> load promedio 1/5/15 min, procesos corriendo/totales, último PID.
    """
    with open("/proc/loadavg") as f:
        partes = f.read().split()

    corriendo, totales = partes[3].split("/")
    return {
        "load1": float(partes[0]),
        "load5": float(partes[1]),
        "load15": float(partes[2]),
        "procesos_corriendo": int(corriendo),
        "procesos_totales": int(totales),
        "ultimo_pid": int(partes[4]),
    }


def leer_uptime():
    """Parsea /proc/uptime: "segundos_uptime segundos_idle_acumulados"."""
    with open("/proc/uptime") as f:
        uptime, idle = f.read().split()
    return {"uptime_seg": float(uptime), "idle_seg": float(idle)}


def leer_stat_sistema():
    """
    Parsea la línea "cpu ..." (agregado de todos los cores) y "btime" de
    /proc/stat.

    La línea cpu trae, en jiffies acumulados desde el boot:
        user nice system idle iowait irq softirq steal guest guest_nice
    btime es el boot time en segundos desde epoch.
    """
    datos = {}
    with open("/proc/stat") as f:
        for linea in f:
            if linea.startswith("cpu "):
                campos = [int(x) for x in linea.split()[1:]]
                nombres = ("user", "nice", "system", "idle", "iowait",
                           "irq", "softirq", "steal", "guest", "guest_nice")
                datos["cpu"] = dict(zip(nombres, campos))
            elif linea.startswith("btime"):
                datos["btime"] = int(linea.split()[1])
    return datos


def calcular_cpu_pct_sistema(cpu_actual, cpu_anterior):
    """
    % de CPU global (user/system/idle/iowait) entre dos lecturas de la
    línea "cpu" de /proc/stat, ambas obtenidas con leer_stat_sistema()["cpu"].

    A diferencia del CPU% por proceso, acá no hace falta un delta de
    tiempo real: se usa el propio total de jiffies transcurridos (suma de
    todos los campos) como base del porcentaje.
    """
    total_actual = sum(cpu_actual.values())
    total_anterior = sum(cpu_anterior.values())
    delta_total = total_actual - total_anterior

    if delta_total <= 0:
        return {"user": 0.0, "system": 0.0, "idle": 0.0, "iowait": 0.0}

    def pct(clave):
        delta = cpu_actual[clave] - cpu_anterior[clave]
        return 100.0 * delta / delta_total

    return {
        "user": pct("user"),
        "system": pct("system"),
        "idle": pct("idle"),
        "iowait": pct("iowait"),
    }


def contar_procesos():
    """
    Recorre todos los PIDs y agrega totales para la vista Sistema:
    cantidad de procesos, threads totales, cantidad por estado y
    cantidad de zombies. Ignora PIDs que desaparecen durante el barrido.
    """
    por_estado = {}
    total_threads = 0
    zombies = 0
    total_procesos = 0

    for pid in listar_pids():
        try:
            stat = leer_stat(pid)
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue

        total_procesos += 1
        total_threads += stat["num_threads"]
        por_estado[stat["state"]] = por_estado.get(stat["state"], 0) + 1
        if stat["state"] == "Z":
            zombies += 1

    return {
        "total_procesos": total_procesos,
        "total_threads": total_threads,
        "por_estado": por_estado,
        "zombies": zombies,
    }


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def main():
    """Demo: lista todos los procesos visibles con sus datos de Resumen."""
    print(f"{'PID':>7} {'PPID':>7} {'USUARIO':<10} {'EST':<3} {'THR':>4}  COMANDO")
    for pid in listar_pids():
        try:
            info = info_resumen(pid)
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue  # el proceso terminó entre listar_pids() y leerlo, o no tenemos permiso

        comando = info["comando"]
        if len(comando) > 60:
            comando = comando[:57] + "..."

        print(f"{info['pid']:>7} {info['ppid']:>7} {info['usuario']:<10} "
              f"{info['estado']:<3} {info['num_threads']:>4}  {comando}")


if __name__ == "__main__":
    main()
