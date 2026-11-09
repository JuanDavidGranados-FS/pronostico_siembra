"""Simulación de Montecarlo de variables climáticas inciertas."""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

import numpy as np

TIPOS_DISTRIBUCION = ("normal", "uniforme", "triangular")


class SimuladorMontecarlo:
    """Genera escenarios aleatorios reproducibles y estadísticas de rendimiento."""

    def __init__(self, iteraciones: int = 10000, semilla: Optional[int] = None) -> None:
        """Crea el simulador. La misma semilla produce siempre los mismos escenarios."""
        if not isinstance(iteraciones, (int, np.integer)) or iteraciones <= 0:
            raise ValueError("Las iteraciones deben ser un entero positivo.")
        self.iteraciones = int(iteraciones)
        self.semilla = semilla

    @staticmethod
    def perfil_estacional(dia_inicio: int, horizonte_dias: int, amplitud: float, dia_pico: float) -> np.ndarray:
        """Desplazamiento diario A·cos(2π(d - d_pico)/365): la estacionalidad se suma a la media."""
        dias = dia_inicio + np.arange(horizonte_dias)
        return amplitud * np.cos(2 * np.pi * (dias - dia_pico) / 365.0)

    @staticmethod
    def _muestrear(rng: np.random.Generator, dist: Dict[str, Any], forma) -> np.ndarray:
        """Muestrea una distribución Normal, Uniforme o Triangular."""
        tipo = str(dist.get("tipo", "")).lower()
        p = dist.get("parametros", {})
        try:
            if tipo == "normal":
                if p["std"] < 0:
                    raise ValueError("La desviación estándar no puede ser negativa.")
                return rng.normal(p["media"], p["std"], forma)
            if tipo == "uniforme":
                if p["min"] > p["max"]:
                    raise ValueError("En la distribución uniforme min no puede superar a max.")
                return rng.uniform(p["min"], p["max"], forma)
            if tipo == "triangular":
                if not p["min"] <= p["moda"] <= p["max"]:
                    raise ValueError("En la triangular debe cumplirse min <= moda <= max.")
                if p["min"] == p["max"]:
                    return np.full(forma, float(p["min"]))
                return rng.triangular(p["min"], p["moda"], p["max"], forma)
        except KeyError as exc:
            raise ValueError(f"Falta el parámetro {exc} en la distribución {tipo!r}.") from exc
        raise ValueError(f"Distribución no soportada: {tipo!r}. Use {TIPOS_DISTRIBUCION}.")

    def generar_escenarios(self, distribuciones: Dict[str, Dict[str, Any]], horizonte_dias: int) -> np.ndarray:
        """Devuelve un arreglo (iteraciones, horizonte_dias, n_variables) en el orden del diccionario.

        Cada distribución admite `desplazamiento` (vector por día) y `limites` [min, max] opcionales.
        """
        if horizonte_dias <= 0:
            raise ValueError("El horizonte debe ser positivo.")
        if not distribuciones:
            raise ValueError("Se requiere al menos una distribución.")
        rng = np.random.default_rng(self.semilla)
        salida = np.empty((self.iteraciones, horizonte_dias, len(distribuciones)))
        for j, dist in enumerate(distribuciones.values()):
            m = self._muestrear(rng, dist, (self.iteraciones, horizonte_dias))
            desp = dist.get("desplazamiento")
            if desp is not None:
                desp = np.asarray(desp, dtype=float)
                if desp.shape != (horizonte_dias,):
                    raise ValueError("El desplazamiento debe tener un valor por día del horizonte.")
                m = m + desp[None, :]
            lim = dist.get("limites")
            if lim:
                m = np.clip(m, lim[0], lim[1])
            salida[:, :, j] = m
        return salida

    @staticmethod
    def calcular_rendimiento(escenarios: np.ndarray,
                             funcion_rendimiento: Callable[[np.ndarray], np.ndarray]) -> Dict[str, Any]:
        """Aplica la función de rendimiento y resume: media, std, percentiles 10/50/90 (y `valores`)."""
        valores = np.asarray(funcion_rendimiento(escenarios), dtype=float)
        if valores.ndim != 1 or valores.shape[0] != escenarios.shape[0]:
            raise ValueError("La función de rendimiento debe devolver un valor por escenario.")
        p10, p50, p90 = np.percentile(valores, [10, 50, 90])
        return {"media": float(valores.mean()), "std": float(valores.std()),
                "p10": float(p10), "p50": float(p50), "p90": float(p90),
                "minimo": float(valores.min()), "maximo": float(valores.max()), "valores": valores}

