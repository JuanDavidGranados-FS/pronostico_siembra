"""Cálculo del KPI final y selección de la fecha óptima."""
from __future__ import annotations

from datetime import date
from typing import Dict, Tuple


def calcular_kpi(rendimiento_esperado: float, factor_relevancia: float, esfuerzo: float) -> float:
    """KPI = rendimiento · factor de relevancia / (1 + esfuerzo)."""
    if esfuerzo < 0:
        raise ValueError("El esfuerzo no puede ser negativo.")
    return float(rendimiento_esperado * factor_relevancia / (1.0 + esfuerzo))


def encontrar_fecha_optima(resultados_por_fecha: Dict[date, float]) -> Tuple[date, float]:
    """Devuelve (fecha, kpi) con el KPI máximo; en empates gana la fecha más temprana."""
    if not resultados_por_fecha:
        raise ValueError("No hay resultados para evaluar.")
    fecha = min(resultados_por_fecha, key=lambda f: (-resultados_por_fecha[f], f))
    return fecha, float(resultados_por_fecha[fecha])
