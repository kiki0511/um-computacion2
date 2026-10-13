"""
Registro en memoria de todas las tareas (dict id -> Tarea).

No usa Lock: todo el acceso ocurre desde corrutinas del mismo event loop,
y ninguna de estas funciones tiene un `await` adentro. El loop solo cambia
de corrutina en un `await`, así que cada operación es atómica de hecho.
"""

from .modelos import Estado, Tarea


class Registro:
    def __init__(self) -> None:
        self._tareas: dict[str, Tarea] = {}

    def agregar(self, tarea: Tarea) -> None:
        self._tareas[tarea.id] = tarea

    def obtener(self, tarea_id: str) -> Tarea | None:
        return self._tareas.get(tarea_id)

    def listar(self, estado: Estado | None = None) -> list[Tarea]:
        """Todas las tareas, o solo las de un estado. Ordenadas por creación."""
        tareas = self._tareas.values()
        if estado is not None:
            tareas = [t for t in tareas if t.estado == estado]
        return sorted(tareas, key=lambda t: t.creada)

    def totales_por_estado(self) -> dict[str, int]:
        totales = {e.value: 0 for e in Estado}
        for t in self._tareas.values():
            totales[t.estado.value] += 1
        return totales

    def tiempo_promedio(self) -> dict[str, float | None]:
        """Duración promedio (segundos) de las tareas completadas, por tipo."""
        duraciones: dict[str, list[float]] = {}
        for t in self._tareas.values():
            if t.estado == Estado.COMPLETADA and t.duracion is not None:
                duraciones.setdefault(t.tipo.value, []).append(t.duracion)
        return {
            tipo: round(sum(lista) / len(lista), 4)
            for tipo, lista in duraciones.items()
        }
