"""Proceso de Galton-Watson: sostenibilidad del cultivo a lo largo de varias temporadas."""
from __future__ import annotations

import math
from typing import Dict, List, Optional

import numpy as np


def clasificar(media: float) -> str:
    """Clasifica el proceso según la media de descendientes μ."""
    if media > 1:
        return "supercrítico (crece)"
    if media == 1:
        return "crítico (se mantiene)"
    return "subcrítico (se extingue)"


def probabilidad_extincion(media: float, iteraciones_max: int = 200000, tolerancia: float = 1e-12) -> float:
    """Probabilidad de extinción q de una sola planta con descendencia Poisson(μ).

    q es la menor raíz de q = exp(μ(q-1)); se obtiene iterando q ← exp(μ(q-1)) desde 0, que converge
    monótonamente a esa raíz. Si μ <= 1 la extinción es segura (q = 1).
    """
    if not isinstance(media, (int, float)) or not math.isfinite(media) or media < 0:
        raise ValueError("La media de descendientes debe ser un número mayor o igual a 0.")
    if media <= 1:
        return 1.0
    q = 0.0
    for _ in range(iteraciones_max):
        nuevo = math.exp(media * (q - 1.0))
        if abs(nuevo - q) < tolerancia:
            return nuevo
        q = nuevo
    return q


class ProcesoGaltonWatson:
    """Población de plantas con descendencia Poisson(μ_t), tope de capacidad y agotamiento del suelo."""

    def __init__(self, media_descendientes: float, plantas_iniciales: int = 1,
                 capacidad: Optional[int] = None, agotamiento: float = 0.0) -> None:
        """`agotamiento` (0-1) reduce μ cada temporada: μ_t = μ·(1-agotamiento)^t."""
        if media_descendientes < 0:
            raise ValueError("La media de descendientes no puede ser negativa.")
        if plantas_iniciales < 1:
            raise ValueError("Debe haber al menos una planta inicial.")
        if capacidad is not None and capacidad < plantas_iniciales:
            raise ValueError("La capacidad no puede ser menor que las plantas iniciales.")
        if not 0 <= agotamiento < 1:
            raise ValueError("El agotamiento del suelo debe estar entre 0 y 1.")
        self.media = float(media_descendientes)
        self.plantas_iniciales = int(plantas_iniciales)
        self.capacidad = capacidad
        self.agotamiento = float(agotamiento)

    def media_temporada(self, t: int) -> float:
        """Media efectiva de descendientes en la temporada t (t = 0 es la primera)."""
        return self.media * (1.0 - self.agotamiento) ** t

    def probabilidad_extincion_largo_plazo(self) -> float:
        """Probabilidad de que la población parta de `plantas_iniciales` y se extinga (media constante μ_0)."""
        return probabilidad_extincion(self.media) ** self.plantas_iniciales

    def simular(self, temporadas: int, trayectorias: int = 2000, semilla: Optional[int] = None) -> np.ndarray:
        """Simula `trayectorias` poblaciones. Devuelve un arreglo (trayectorias, temporadas+1).

        Como la suma de Z_t variables Poisson(μ) es Poisson(μ·Z_t), se usa Z_{t+1} ~ Poisson(μ_t·Z_t).
        """
        if temporadas < 1:
            raise ValueError("Debe haber al menos una temporada.")
        rng = np.random.default_rng(semilla)
        z = np.empty((trayectorias, temporadas + 1))
        z[:, 0] = self.plantas_iniciales
        for t in range(temporadas):
            siguiente = rng.poisson(self.media_temporada(t) * z[:, t]).astype(float)
            z[:, t + 1] = np.minimum(siguiente, self.capacidad) if self.capacidad else siguiente
        return z

    def resumen(self, temporadas: int, trayectorias: int = 2000, semilla: Optional[int] = None) -> Dict[str, object]:
        """Resumen: población esperada y percentiles por temporada, medias y probabilidades de extinción."""
        z = self.simular(temporadas, trayectorias, semilla)
        medias = [self.media_temporada(t) for t in range(temporadas)]
        return {
            "poblacion_media": z.mean(axis=0).tolist(),
            "poblacion_p10": np.percentile(z, 10, axis=0).tolist(),
            "poblacion_p90": np.percentile(z, 90, axis=0).tolist(),
            "medias": medias,
            "clasificacion": clasificar(medias[0]),
            "prob_extincion_largo_plazo": self.probabilidad_extincion_largo_plazo(),
            "prob_extincion_horizonte": float(np.mean(z[:, -1] == 0)),
            "riesgo_extincion": any(m < 1 for m in medias),
        }
