#!/usr/bin/env python3
"""
Ejercicio 2.1 - Inspector de archivos.

Muestra información detallada sobre cualquier archivo, directorio o enlace
simbólico, similar a una versión mejorada de 'stat'.

Uso:
    python inspector.py /etc/passwd
    python inspector.py /dev/null
    python inspector.py /bin
    python inspector.py /home
"""

import argparse
import os
import sys
import stat
import pwd
import grp
from datetime import datetime
from pathlib import Path


# ─── Utilidades ──────────────────────────────────────────────────────────────

def tipo_archivo(modo):
    """Devuelve una descripción legible del tipo de archivo según el modo."""
    if stat.S_ISREG(modo):
        return "archivo regular"
    if stat.S_ISDIR(modo):
        return "directorio"
    if stat.S_ISLNK(modo):
        return "enlace simbólico"
    if stat.S_ISCHR(modo):
        return "dispositivo de caracteres"
    if stat.S_ISBLK(modo):
        return "dispositivo de bloques"
    if stat.S_ISFIFO(modo):
        return "pipe (FIFO)"
    if stat.S_ISSOCK(modo):
        return "socket"
    return "desconocido"


def permisos_legibles(modo):
    """Convierte el modo numérico a formato rwxrwxrwx."""
    bits = [
        (stat.S_IRUSR, "r"), (stat.S_IWUSR, "w"), (stat.S_IXUSR, "x"),
        (stat.S_IRGRP, "r"), (stat.S_IWGRP, "w"), (stat.S_IXGRP, "x"),
        (stat.S_IROTH, "r"), (stat.S_IWOTH, "w"), (stat.S_IXOTH, "x"),
    ]
    return "".join(letra if modo & bit else "-" for bit, letra in bits)


def permisos_octal(modo):
    """Devuelve los permisos en formato octal de 3 dígitos (ej: 644)."""
    return oct(stat.S_IMODE(modo))[2:]


def tamanio_legible(bytes_):
    """Convierte bytes a formato legible (KB, MB, GB)."""
    for unidad in ("bytes", "KB", "MB", "GB", "TB"):
        if bytes_ < 1024 or unidad == "TB":
            if unidad == "bytes":
                return f"{bytes_} bytes"
            return f"{bytes_:.2f} {unidad}"
        bytes_ /= 1024


def nombre_usuario(uid):
    """Obtiene el nombre de usuario a partir del UID."""
    try:
        return pwd.getpwuid(uid).pw_name
    except KeyError:
        return str(uid)


def nombre_grupo(gid):
    """Obtiene el nombre del grupo a partir del GID."""
    try:
        return grp.getgrgid(gid).gr_name
    except KeyError:
        return str(gid)


def formatear_tiempo(timestamp):
    """Formatea un timestamp Unix a fecha/hora legible."""
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def contar_elementos(directorio):
    """Cuenta los elementos directos de un directorio."""
    try:
        return len(list(Path(directorio).iterdir()))
    except PermissionError:
        return None


# ─── Inspector principal ──────────────────────────────────────────────────────

def inspeccionar(ruta):
    """Muestra información completa sobre el archivo/directorio/symlink."""
    path = Path(ruta)

    # Usamos lstat para no seguir symlinks (queremos info del link, no del destino)
    try:
        info = path.lstat()
    except FileNotFoundError:
        print(f"Error: '{ruta}' no existe.")
        sys.exit(1)
    except PermissionError:
        print(f"Error: Sin permisos para acceder a '{ruta}'.")
        sys.exit(1)

    modo = info.st_mode
    es_symlink = stat.S_ISLNK(modo)
    es_dir = stat.S_ISDIR(modo)

    # Tipo de archivo
    tipo = tipo_archivo(modo)
    if es_symlink:
        try:
            destino = os.readlink(ruta)
            tipo_str = f"enlace simbólico -> {destino}"
        except OSError:
            tipo_str = "enlace simbólico (destino ilegible)"
    else:
        tipo_str = tipo

    print(f"Archivo: {path.resolve() if not es_symlink else ruta}")
    print(f"Tipo: {tipo_str}")

    # Tamaño
    tam = info.st_size
    print(f"Tamaño: {tam} bytes ({tamanio_legible(tam)})")

    # Permisos
    perms_str = permisos_legibles(modo)
    perms_oct = permisos_octal(modo)
    print(f"Permisos: {perms_str} ({perms_oct})")

    # Propietario y grupo
    usuario = nombre_usuario(info.st_uid)
    grupo = nombre_grupo(info.st_gid)
    print(f"Propietario: {usuario} (uid: {info.st_uid})")
    print(f"Grupo: {grupo} (gid: {info.st_gid})")

    # Inodo y enlaces duros
    print(f"Inodo: {info.st_ino}")
    print(f"Enlaces duros: {info.st_nlink}")

    # Timestamps
    print(f"Última modificación: {formatear_tiempo(info.st_mtime)}")
    print(f"Último acceso: {formatear_tiempo(info.st_atime)}")
    # st_ctime en Linux es el cambio de metadatos, no la creación
    print(f"Cambio de metadatos: {formatear_tiempo(info.st_ctime)}")

    # Info extra para directorios
    if es_dir:
        n = contar_elementos(ruta)
        if n is not None:
            print(f"Contenido: {n} elemento{'s' if n != 1 else ''}")
        else:
            print("Contenido: (sin permisos para listar)")

    # Info extra para symlinks: verificar si el destino existe
    if es_symlink:
        destino_existe = path.exists()
        estado = "válido" if destino_existe else "ROTO (destino no existe)"
        print(f"Estado del enlace: {estado}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Muestra información detallada sobre archivos, directorios y symlinks.",
        epilog="Similar a 'stat' pero con salida más legible.",
    )
    parser.add_argument(
        "ruta",
        help="Ruta al archivo, directorio o enlace simbólico a inspeccionar",
    )

    args = parser.parse_args()
    inspeccionar(args.ruta)
    return 0


if __name__ == "__main__":
    sys.exit(main())
