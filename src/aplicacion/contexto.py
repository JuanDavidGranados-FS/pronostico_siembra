"""Contenedor de servicios de la aplicación (lo construye la raíz de composición en main.py)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from src.aplicacion.diagnostico import Diagnostico
from src.aplicacion.gestor_historial import GestorHistorial
from src.aplicacion.gestor_relevancia import GestorRelevancia
from src.aplicacion.orquestador import OrquestadorSimulacion


@dataclass
class Contexto:
    """Todo lo que la interfaz necesita, ya conectado a PostgreSQL o a memoria."""
    orquestador: OrquestadorSimulacion
    historial: GestorHistorial
    relevancia: GestorRelevancia
    diagnostico: Diagnostico
    repo_config: Any
    repo_historial: Any
    repo_externos: Any
    repo_matrices: Any
    adaptador: Any
    preferencias: Any
    modo_bd: str
    carpeta_entrada: str
    reconectar: Optional[Callable[[], "Contexto"]] = field(default=None, repr=False)
