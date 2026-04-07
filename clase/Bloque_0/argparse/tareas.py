#!/usr/bin/env python3
"""
Ejercicio 3.3 - Gestor de tareas con subcomandos.

Uso:
    python tareas.py add "Descripción de la tarea"
    python tareas.py add "Tarea urgente" --priority alta
    python tareas.py list
    python tareas.py list --pending
    python tareas.py list --done
    python tareas.py done <id>
    python tareas.py remove <id>

Las tareas se persisten en ~/.tareas.json
"""

import argparse
import json
import sys
from pathlib import Path


ARCHIVO_TAREAS = Path.home() / ".tareas.json"
PRIORIDADES = ["baja", "media", "alta"]
ETIQUETA_PRIORIDAD = {"alta": "[ALTA]", "media": "[MEDIA]", "baja": ""}


# ─── Persistencia ────────────────────────────────────────────────────────────

def cargar_tareas():
    if not ARCHIVO_TAREAS.exists():
        return []
    try:
        with open(ARCHIVO_TAREAS, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        print("Advertencia: no se pudo leer el archivo de tareas. Se crea uno nuevo.")
        return []


def guardar_tareas(tareas):
    try:
        with open(ARCHIVO_TAREAS, "w", encoding="utf-8") as f:
            json.dump(tareas, f, ensure_ascii=False, indent=2)
    except IOError as e:
        print(f"Error: no se pudo guardar las tareas: {e}", file=sys.stderr)
        sys.exit(1)


def siguiente_id(tareas):
    if not tareas:
        return 1
    return max(t["id"] for t in tareas) + 1


# ─── Subcomandos ─────────────────────────────────────────────────────────────

def cmd_add(args):
    tareas = cargar_tareas()
    nueva = {
        "id": siguiente_id(tareas),
        "descripcion": args.descripcion,
        "priority": args.priority,
        "completada": False,
    }
    tareas.append(nueva)
    guardar_tareas(tareas)

    if args.priority:
        print(f"Tarea #{nueva['id']} agregada (prioridad: {args.priority})")
    else:
        print(f"Tarea #{nueva['id']} agregada")


def cmd_list(args):
    tareas = cargar_tareas()

    # Aplicar filtros
    if args.pending and args.done:
        print("Error: no podés usar --pending y --done al mismo tiempo.")
        sys.exit(1)

    if args.pending:
        tareas = [t for t in tareas if not t["completada"]]
    elif args.done:
        tareas = [t for t in tareas if t["completada"]]

    if args.priority:
        tareas = [t for t in tareas if t.get("priority") == args.priority]

    if not tareas:
        print("No hay tareas para mostrar.")
        return

    for t in tareas:
        estado = "x" if t["completada"] else " "
        etiqueta = ETIQUETA_PRIORIDAD.get(t.get("priority") or "", "")
        sufijo = f" {etiqueta}" if etiqueta else ""
        print(f"#{t['id']} [{estado}] {t['descripcion']}{sufijo}")


def cmd_done(args):
    tareas = cargar_tareas()
    tarea = next((t for t in tareas if t["id"] == args.id), None)

    if tarea is None:
        print(f"Error: no existe la tarea #{args.id}.")
        sys.exit(1)

    if tarea["completada"]:
        print(f"La tarea #{args.id} ya estaba completada.")
        return

    tarea["completada"] = True
    guardar_tareas(tareas)
    print(f"Tarea #{args.id} completada")


def cmd_remove(args):
    tareas = cargar_tareas()
    tarea = next((t for t in tareas if t["id"] == args.id), None)

    if tarea is None:
        print(f"Error: no existe la tarea #{args.id}.")
        sys.exit(1)

    try:
        respuesta = input(f'¿Eliminar "{tarea["descripcion"]}"? [s/N] ').strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nOperación cancelada.")
        sys.exit(0)

    if respuesta == "s":
        tareas = [t for t in tareas if t["id"] != args.id]
        guardar_tareas(tareas)
        print(f"Tarea #{args.id} eliminada")
    else:
        print("Operación cancelada.")


# ─── Parser principal ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Gestor de tareas desde la línea de comandos.",
        epilog="Las tareas se guardan en ~/.tareas.json",
    )

    subparsers = parser.add_subparsers(dest="comando", metavar="subcomando")
    subparsers.required = True

    # --- add ---
    p_add = subparsers.add_parser("add", help="Agregar una nueva tarea")
    p_add.add_argument("descripcion", help="Descripción de la tarea")
    p_add.add_argument(
        "--priority",
        choices=PRIORIDADES,
        metavar="{baja,media,alta}",
        help="Prioridad de la tarea (baja, media, alta)",
    )
    p_add.set_defaults(func=cmd_add)

    # --- list ---
    p_list = subparsers.add_parser("list", help="Listar tareas")
    p_list.add_argument("--pending", action="store_true", help="Mostrar solo tareas pendientes")
    p_list.add_argument("--done", action="store_true", help="Mostrar solo tareas completadas")
    p_list.add_argument(
        "--priority",
        choices=PRIORIDADES,
        metavar="{baja,media,alta}",
        help="Filtrar por prioridad",
    )
    p_list.set_defaults(func=cmd_list)

    # --- done ---
    p_done = subparsers.add_parser("done", help="Marcar una tarea como completada")
    p_done.add_argument("id", type=int, help="ID de la tarea a completar")
    p_done.set_defaults(func=cmd_done)

    # --- remove ---
    p_remove = subparsers.add_parser("remove", help="Eliminar una tarea")
    p_remove.add_argument("id", type=int, help="ID de la tarea a eliminar")
    p_remove.set_defaults(func=cmd_remove)

    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
