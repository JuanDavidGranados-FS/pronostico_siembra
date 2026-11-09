"""Cadenas de Márkov de tiempo discreto."""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import numpy as np


class CadenaMarkov:
    """Cadena de Márkov finita con matriz de transición estocástica por filas."""

    def __init__(self, estados: Sequence[str], matriz_transicion, tolerancia: float = 1e-6) -> None:
        """Crea la cadena validando que la matriz sea cuadrada, no negativa y estocástica."""
        estados = list(estados)
        n = len(estados)
        if n == 0:
            raise ValueError("Debe haber al menos un estado.")
        if len(set(estados)) != n:
            raise ValueError("Los estados no pueden repetirse.")
        try:
            matriz = np.array(matriz_transicion, dtype=float)
        except (TypeError, ValueError) as exc:
            raise ValueError("La matriz de transición debe ser numérica y rectangular.") from exc
        if matriz.shape != (n, n):
            raise ValueError(f"La matriz debe ser {n}x{n}, se recibió {matriz.shape}.")
        if not np.all(np.isfinite(matriz)) or (matriz < 0).any():
            raise ValueError("La matriz no puede tener valores negativos ni no finitos.")
        if not np.allclose(matriz.sum(axis=1), 1.0, atol=tolerancia):
            raise ValueError("La matriz no es estocástica: cada fila debe sumar 1.")
        self.estados: List[str] = estados
        self.matriz: np.ndarray = matriz
        self._indices = {e: i for i, e in enumerate(estados)}

    def _indice(self, estado: str) -> int:
        """Devuelve el índice de un estado o lanza ValueError si no existe."""
        if estado not in self._indices:
            raise ValueError(f"Estado desconocido: {estado!r}")
        return self._indices[estado]

    def evolucion(self, estado_inicial: str, pasos: int) -> np.ndarray:
        """Devuelve la distribución en cada paso 0..pasos (matriz (pasos+1, n_estados))."""
        if pasos < 0:
            raise ValueError("El número de pasos no puede ser negativo.")
        v = np.zeros(len(self.estados))
        v[self._indice(estado_inicial)] = 1.0
        salida = [v]
        for _ in range(pasos):
            v = v @ self.matriz  # p_{t+1} = p_t · P
            salida.append(v)
        return np.array(salida)

    def probabilidad_estado(self, estado_inicial: str, pasos: int) -> Dict[str, float]:
        """Distribución de probabilidad de estados tras `pasos` transiciones."""
        final = self.evolucion(estado_inicial, pasos)[-1]
        return {e: float(p) for e, p in zip(self.estados, final)}

    def distribucion_estacionaria(self) -> Dict[str, float]:
        """Distribución π con π·P = π y Σπ = 1 (mínimos cuadrados; única si la cadena es ergódica)."""
        n = len(self.estados)
        a = np.vstack([self.matriz.T - np.eye(n), np.ones((1, n))])
        b = np.zeros(n + 1)
        b[-1] = 1.0
        pi = np.clip(np.linalg.lstsq(a, b, rcond=None)[0], 0.0, None)
        pi = pi / pi.sum()
        return {e: float(p) for e, p in zip(self.estados, pi)}

    def simular_trayectoria(self, pasos: int, semilla: Optional[int] = None,
                            estado_inicial: Optional[str] = None) -> List[str]:
        """Simula una trayectoria de `pasos` transiciones (devuelve pasos+1 estados)."""
        if pasos < 0:
            raise ValueError("El número de pasos no puede ser negativo.")
        rng = np.random.default_rng(semilla)
        idx = self._indice(estado_inicial) if estado_inicial is not None else 0
        trayectoria = [self.estados[idx]]
        for _ in range(pasos):
            idx = int(rng.choice(len(self.estados), p=self.matriz[idx]))
            trayectoria.append(self.estados[idx])
        return trayectoria

