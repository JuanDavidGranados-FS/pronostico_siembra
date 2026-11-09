"""Factor de Relevancia: ponderación dinámica de variables."""
from __future__ import annotations

from typing import Dict, Mapping, Optional, Tuple

import numpy as np


class FactorRelevancia:
    """Asigna pesos 0-100 a las variables y combina sus puntajes normalizados (0-1)."""

    def __init__(self, pesos: Dict[str, float], rangos: Optional[Mapping[str, Tuple[float, float, float]]] = None,
                 peso_por_defecto: float = 50.0) -> None:
        """`rangos[variable] = (mínimo, óptimo, máximo)`; puntaje 1 en el óptimo y 0 en los extremos."""
        for nombre, peso in {**pesos, "__defecto__": peso_por_defecto}.items():
            if isinstance(peso, bool) or not isinstance(peso, (int, float)) or not 0 <= peso <= 100:
                raise ValueError(f"El peso de '{nombre}' debe estar entre 0 y 100.")
        for nombre, (mn, op, mx) in (rangos or {}).items():
            if not mn < op < mx:
                raise ValueError(f"El rango de '{nombre}' debe cumplir mínimo < óptimo < máximo.")
        self.pesos = dict(pesos)
        self.rangos = dict(rangos or {})
        self.peso_por_defecto = peso_por_defecto

    def peso(self, variable: str) -> float:
        """Peso (0-100) de una variable; usa el valor por defecto si no fue definido."""
        return float(self.pesos.get(variable, self.peso_por_defecto))

    def normalizar(self, variable: str, valor):
        """Convierte un valor (escalar o arreglo) a puntaje 0-1 con función triangular sobre el rango."""
        if variable not in self.rangos:
            raise KeyError(f"No hay rango definido para '{variable}'.")
        mn, op, mx = self.rangos[variable]
        v = np.asarray(valor, dtype=float)
        # Sube linealmente de mn a op y baja linealmente de op a mx.
        puntaje = np.clip(np.minimum((v - mn) / (op - mn), (mx - v) / (mx - op)), 0.0, 1.0)
        return float(puntaje) if puntaje.ndim == 0 else puntaje

    def calcular_kpi_ponderado(self, variables: Dict[str, object]):
        """Promedio ponderado Σ(w·s)/Σw de puntajes 0-1. Si Σw = 0 devuelve 1.0 (sin preferencia: neutro)."""
        total = sum(self.peso(k) for k in variables)
        if total == 0:
            return 1.0
        return sum(self.peso(k) * v for k, v in variables.items()) / total
