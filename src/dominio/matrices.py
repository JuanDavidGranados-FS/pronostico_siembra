"""Edición de matrices de transición: normalizar, agregar y quitar estados (Python puro con numpy)."""
from __future__ import annotations

from typing import List, Sequence, Tuple

import numpy as np


def normalizar_filas(matriz) -> List[List[float]]:
    """Divide cada fila entre su suma; una fila nula pasa a ser absorbente (probabilidad 1 de quedarse)."""
    m = np.clip(np.array(matriz, dtype=float), 0.0, None)
    for i in range(m.shape[0]):
        s = m[i].sum()
        if s <= 0:
            m[i] = 0.0
            m[i, i] = 1.0
        else:
            m[i] /= s
    return m.tolist()


def filas_invalidas(matriz, tolerancia: float = 1e-6) -> List[int]:
    """Índices de las filas que no suman 1 (o tienen valores negativos)."""
    m = np.array(matriz, dtype=float)
    return [i for i in range(m.shape[0]) if abs(m[i].sum() - 1.0) > tolerancia or (m[i] < 0).any()]


def agregar_estado(estados: Sequence[str], matriz, nombre: str) -> Tuple[List[str], List[List[float]]]:
    """Agrega un estado absorbente (fila y columna nuevas con 1 en la diagonal)."""
    nombre = nombre.strip()
    if not nombre or nombre in estados:
        raise ValueError("El nombre del estado está vacío o ya existe.")
    n = len(estados)
    nueva = np.zeros((n + 1, n + 1))
    nueva[:n, :n] = np.array(matriz, dtype=float)
    nueva[n, n] = 1.0
    return list(estados) + [nombre], nueva.tolist()


def quitar_estado(estados: Sequence[str], matriz, nombre: str) -> Tuple[List[str], List[List[float]]]:
    """Elimina un estado y renormaliza las filas que quedan."""
    if nombre not in estados:
        raise ValueError(f"Estado desconocido: {nombre!r}")
    if len(estados) <= 2:
        raise ValueError("Una cadena necesita al menos 2 estados.")
    i = list(estados).index(nombre)
    m = np.delete(np.delete(np.array(matriz, dtype=float), i, axis=0), i, axis=1)
    return [e for e in estados if e != nombre], normalizar_filas(m)
