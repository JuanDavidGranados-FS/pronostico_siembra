"""Reutilizar la configuración con la que se ejecutó una simulación guardada."""
from __future__ import annotations

from typing import Any, Optional

from src.dominio.entidades import DatosEntrada


def configuracion_de_simulacion(repo_historial: Any, repo_config: Any, id_sim: int) -> Optional[DatosEntrada]:
    """Reconstruye los datos de entrada de una simulación guardada (None si no hay configuración disponible)."""
    fila = repo_historial.obtener(id_sim)
    if not fila or not fila.get("configuracion_id"):
        return None
    cfg = repo_config.obtener(fila["configuracion_id"])
    if not cfg:
        return None
    datos = cfg.get("datos")
    if datos is None:  # PostgreSQL: la configuración completa viaja dentro de datos_deterministas["_completo"]
        datos = (cfg.get("datos_deterministas") or {}).get("_completo")
    return DatosEntrada.desde_dict(datos) if isinstance(datos, dict) else None
