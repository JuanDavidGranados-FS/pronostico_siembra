"""Distribución de Poisson para eventos raros (plagas, heladas, lluvias intensas)."""
from __future__ import annotations

import math
from typing import Dict

import numpy as np


def _validar_lambda(lam: float) -> None:
    """La tasa media debe ser un número finito y no negativo."""
    if not isinstance(lam, (int, float)) or isinstance(lam, bool) or not math.isfinite(lam) or lam < 0:
        raise ValueError("La tasa media (λ) debe ser un número mayor o igual a 0.")


def probabilidad(lam: float, k: int) -> float:
    """P(X = k) = λ^k · e^(-λ) / k!  (se calcula en logaritmos para ser estable con λ o k grandes)."""
    _validar_lambda(lam)
    if k < 0 or int(k) != k:
        raise ValueError("k debe ser un entero mayor o igual a 0.")
    if lam == 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(k * math.log(lam) - lam - math.lgamma(k + 1))


def distribucion(lam: float, k_max: int = 2) -> Dict[str, float]:
    """Probabilidades de 0, 1, ..., k_max eventos y de «k_max+1 o más». Siempre suman 1."""
    _validar_lambda(lam)
    if k_max < 0:
        raise ValueError("k_max no puede ser negativo.")
    salida = {str(k): probabilidad(lam, k) for k in range(k_max + 1)}
    salida[f"{k_max + 1}+"] = max(0.0, 1.0 - sum(salida.values()))
    return salida


def perdida_esperada(lam: float, perdida_por_evento: float) -> float:
    """Fracción esperada de cosecha perdida: 1 - E[(1-p)^N] = 1 - exp(-λ·p) (función generadora de Poisson)."""
    _validar_lambda(lam)
    if not 0 <= perdida_por_evento <= 1:
        raise ValueError("La pérdida por evento debe estar entre 0 y 1.")
    return 1.0 - math.exp(-lam * perdida_por_evento)


def factor_rendimiento(conteos, perdida_por_evento: float) -> np.ndarray:
    """Factor multiplicativo (1-p)^N para cada escenario, dado el número de eventos N de cada uno."""
    if not 0 <= perdida_por_evento <= 1:
        raise ValueError("La pérdida por evento debe estar entre 0 y 1.")
    return (1.0 - perdida_por_evento) ** np.asarray(conteos, dtype=float)


def muestrear(rng: np.random.Generator, lam: float, n: int) -> np.ndarray:
    """Número de eventos de cada uno de `n` escenarios."""
    _validar_lambda(lam)
    return rng.poisson(lam, n)
