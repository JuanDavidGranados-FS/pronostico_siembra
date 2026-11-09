"""Métodos para calcular el Factor de Relevancia (pesos 0-100): Ley del Mínimo, histórico, AHP y diario de campo."""
from __future__ import annotations

import itertools
import math
import unicodedata
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

VARIABLES = ("agua", "temperatura", "humedad", "ph", "nutrientes")
ETIQUETAS = {"agua": "Agua", "temperatura": "Temperatura", "humedad": "Humedad", "ph": "pH",
             "nutrientes": "Nutrientes"}
MIN_FILAS_HISTORICO = 10
MIN_REGISTROS_CAMPO = 5
# Índice de consistencia aleatoria de Saaty (n = 1..9).
_RI = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45}


# ------------------------------------------------------------------ Ley del Mínimo
def ley_del_minimo(variables: Mapping[str, Optional[Dict[str, float]]]) -> Tuple[Dict[str, float], Dict[str, str]]:
    """Relevancia = |valor_actual - óptimo| / rango_tolerable × 100, limitada a [0, 100].

    `variables[nombre]` es {"actual", "optimo", "tolerable"} o None si no hay datos (relevancia 0).
    Cuanto más lejos del óptimo, más limita la variable al cultivo y más relevancia recibe.
    Devuelve (pesos, justificaciones en lenguaje cotidiano).
    """
    pesos: Dict[str, float] = {}
    textos: Dict[str, str] = {}
    for nombre, v in variables.items():
        etiqueta = ETIQUETAS.get(nombre, nombre.capitalize())
        if not v or v.get("actual") is None or v.get("optimo") is None or not v.get("tolerable"):
            pesos[nombre] = 0.0
            textos[nombre] = f"{etiqueta}: relevancia 0 porque no hay datos."
            continue
        if v["tolerable"] <= 0:
            raise ValueError(f"El rango tolerable de '{nombre}' debe ser mayor que 0.")
        dif = v["actual"] - v["optimo"]
        peso = round(min(100.0, abs(dif) / v["tolerable"] * 100.0), 1)
        pesos[nombre] = peso
        if peso < 15:
            donde = "está cerca del óptimo"
        elif peso < 50:
            donde = "está algo por debajo del óptimo" if dif < 0 else "está algo por encima del óptimo"
        else:
            donde = "está muy por debajo del óptimo" if dif < 0 else "está muy por encima del óptimo"
        textos[nombre] = f"{etiqueta}: relevancia {peso:.0f} porque {donde}."
    return pesos, textos


# ------------------------------------------------------------------ Histórico (Spearman)
def _rangos(valores: Sequence[float]) -> np.ndarray:
    """Rangos 1..n con promedio en los empates (necesarios para Spearman)."""
    v = np.asarray(valores, dtype=float)
    orden = np.argsort(v, kind="mergesort")
    ordenado = v[orden]
    rangos = np.empty(len(v))
    i = 0
    while i < len(v):
        j = i
        while j + 1 < len(v) and ordenado[j + 1] == ordenado[i]:
            j += 1
        rangos[orden[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return rangos


def spearman(x: Sequence[float], y: Sequence[float]) -> float:
    """Coeficiente de correlación de Spearman (0 si alguna serie es constante)."""
    if len(x) != len(y) or len(x) < 2:
        raise ValueError("Las series deben tener la misma longitud (mínimo 2).")
    rx, ry = _rangos(x), _rangos(y)
    if rx.std() == 0 or ry.std() == 0:
        return 0.0
    return float(np.corrcoef(rx, ry)[0, 1])


def _normalizar_nombre(texto: str) -> str:
    """Minúsculas, sin tildes ni espacios: 'Rendimiento (t/ha)' -> 'rendimiento(t/ha)'."""
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode().lower()
    return "".join(c for c in t if not c.isspace())


_ALIAS = {"agua": ("agua", "riego", "lluvia", "precipitacion"), "temperatura": ("temperatura", "temp"),
          "humedad": ("humedad",), "ph": ("ph",),
          "nutrientes": ("nutrientes", "npk", "nitrogeno", "fosforo", "potasio", "n", "p", "k")}
_ALIAS_RENDIMIENTO = ("rendimiento", "cosecha", "produccion", "yield")


def _a_numero(valor: Any) -> Optional[float]:
    """Convierte a float (acepta coma decimal); None si no es numérico."""
    if isinstance(valor, bool):
        return None
    try:
        n = float(str(valor).strip().replace(",", "."))
    except ValueError:
        return None
    return n if math.isfinite(n) else None


def relevancia_historica(filas: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Pesos a partir de un histórico (columnas de variables + rendimiento) con correlación de Spearman.

    Valida el archivo (≥ 10 filas válidas, columna de rendimiento, ≥ 1 variable reconocible) y, si sirve,
    normaliza |ρ| a escala 0-100 (la variable más influyente = 100). Devuelve un dict con `valido` y, según
    el caso, `motivo` (por qué no sirve) o `pesos`, `correlaciones` y `justificaciones`.
    """
    if not filas:
        return {"valido": False, "motivo": "El archivo está vacío."}
    columnas = {_normalizar_nombre(c): c for c in filas[0].keys()}
    col_rend = next((orig for norm, orig in columnas.items() if any(norm.startswith(a) for a in _ALIAS_RENDIMIENTO)), None)
    if col_rend is None:
        return {"valido": False, "motivo": "No encontré la columna de rendimiento (debe llamarse «rendimiento» o «cosecha»)."}
    por_variable: Dict[str, List[str]] = {}
    for norm, orig in columnas.items():
        for var, alias in _ALIAS.items():
            if norm in alias or any(norm.startswith(a) and len(a) > 2 for a in alias):
                por_variable.setdefault(var, []).append(orig)
    if not por_variable:
        return {"valido": False, "motivo": "No reconocí ninguna columna de variables (agua, temperatura, humedad, pH, nutrientes)."}
    usadas = [c for cols in por_variable.values() for c in cols]
    validas = []
    for f in filas:
        nums = {c: _a_numero(f.get(c)) for c in usadas + [col_rend]}
        if all(n is not None for n in nums.values()):
            validas.append(nums)
    if len(validas) < MIN_FILAS_HISTORICO:
        return {"valido": False, "motivo": f"Se necesitan al menos {MIN_FILAS_HISTORICO} filas con datos numéricos completos "
                                           f"y solo hay {len(validas)}."}
    rend = [r[col_rend] for r in validas]
    if len(set(rend)) < 2:
        return {"valido": False, "motivo": "El rendimiento es igual en todas las filas; no se puede medir su relación."}
    rhos: Dict[str, float] = {}
    for var, cols in por_variable.items():
        rhos[var] = float(np.mean([spearman([r[c] for r in validas], rend) for c in cols]))
    maximo = max(abs(r) for r in rhos.values())
    if maximo == 0:
        return {"valido": False, "motivo": "Ninguna variable cambia a la vez que el rendimiento (todas son constantes)."}
    pesos = {v: round(abs(r) / maximo * 100.0, 1) for v, r in rhos.items()}
    textos = {}
    for v, r in rhos.items():
        fuerza = "fuerte" if abs(r) >= 0.7 else "moderada" if abs(r) >= 0.4 else "débil"
        sentido = "positiva" if r >= 0 else "negativa"
        textos[v] = (f"{ETIQUETAS[v]}: relevancia {pesos[v]:.0f}; correlación de Spearman ρ = {r:+.2f} "
                     f"({fuerza}, {sentido}) con {len(validas)} temporadas.")
    return {"valido": True, "pesos": pesos, "correlaciones": rhos, "justificaciones": textos, "filas_usadas": len(validas)}


# ------------------------------------------------------------------ AHP (modo experto)
def pares_de_variables(variables: Sequence[str] = VARIABLES) -> List[Tuple[str, str]]:
    """Todas las parejas (a, b) que el experto debe comparar."""
    return list(itertools.combinations(variables, 2))


def matriz_comparacion(variables: Sequence[str], comparaciones: Mapping[Tuple[str, str], float]) -> np.ndarray:
    """Matriz recíproca de Saaty. `comparaciones[(a, b)]` = cuántas veces a es más importante que b (1-9);
    un valor < 1 significa que b es más importante. Una pareja sin respuesta se toma como igual de importante."""
    n = len(variables)
    idx = {v: i for i, v in enumerate(variables)}
    m = np.ones((n, n))
    for (a, b), valor in comparaciones.items():
        if a not in idx or b not in idx or a == b:
            raise ValueError(f"Pareja inválida: {a}, {b}.")
        if not (1 / 9 - 1e-9 <= valor <= 9 + 1e-9):
            raise ValueError("Las comparaciones deben estar en la escala de 1 a 9.")
        m[idx[a], idx[b]] = valor
        m[idx[b], idx[a]] = 1.0 / valor
    return m


def ahp(matriz: np.ndarray, variables: Sequence[str] = VARIABLES) -> Dict[str, Any]:
    """Pesos AHP: autovector principal de la matriz, razón de consistencia CR (< 0.1 es aceptable) y pesos 0-100."""
    m = np.asarray(matriz, dtype=float)
    n = m.shape[0]
    if m.shape != (n, n) or n != len(variables) or n < 2:
        raise ValueError("La matriz debe ser cuadrada, de al menos 2x2 y con una fila por variable.")
    valores, vectores = np.linalg.eig(m)
    k = int(np.argmax(valores.real))
    w = np.abs(vectores[:, k].real)
    w = w / w.sum()
    lam = float(valores[k].real)
    ci = (lam - n) / (n - 1)
    cr = ci / _RI[n] if _RI.get(n, 1.45) > 0 else 0.0
    pesos = {v: round(float(x / w.max() * 100.0), 1) for v, x in zip(variables, w)}
    # Parejas más incoherentes: donde a_ij se aleja más de w_i / w_j.
    desvio = sorted(((abs(math.log(m[i, j] / (w[i] / w[j]))), (variables[i], variables[j]))
                     for i in range(n) for j in range(i + 1, n)), reverse=True)
    return {"pesos": pesos, "vector": w.tolist(), "lambda_max": lam, "ci": float(ci), "cr": float(max(cr, 0.0)),
            "consistente": bool(cr < 0.1), "parejas_a_revisar": [p for _, p in desvio[:2]]}


# ------------------------------------------------------------------ Diario de campo
def experimento_sugerido(variable: str) -> str:
    """Experimento simple: variar una sola variable a la vez."""
    etiqueta = ETIQUETAS.get(variable, variable).lower()
    return (f"Planta 2 lotes iguales. Al lote A dale {etiqueta} normal y al lote B 30 % menos. "
            f"Anota el rendimiento de cada uno.")


def relevancia_empirica(registros: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Relevancia con los datos del propio usuario: sensibilidad = (Δrendimiento relativo) / (Δvariable relativo).

    Con menos de 5 registros devuelve `suficiente = False` (la app usa entonces la Ley del Mínimo).
    Cada registro: {"temporada", "variable", "valor", "rendimiento"}.
    """
    validos = []
    for r in registros:
        valor, rend = _a_numero(r.get("valor")), _a_numero(r.get("rendimiento"))
        if r.get("variable") in VARIABLES and valor is not None and rend is not None:
            validos.append((r["variable"], valor, rend))
    if len(validos) < MIN_REGISTROS_CAMPO:
        return {"suficiente": False, "registros": len(validos),
                "motivo": f"Faltan datos: hay {len(validos)} registros y se necesitan {MIN_REGISTROS_CAMPO}."}
    sens: Dict[str, float] = {}
    for var in {v for v, _, _ in validos}:
        vals = [(x, y) for v, x, y in validos if v == var]
        xs, ys = [p[0] for p in vals], [p[1] for p in vals]
        if len(set(xs)) < 2 or np.mean(np.abs(xs)) == 0 or np.mean(ys) == 0:
            sens[var] = 0.0
            continue
        cambio_x = (max(xs) - min(xs)) / abs(np.mean(xs))
        cambio_y = (max(ys) - min(ys)) / abs(np.mean(ys))
        sens[var] = float(cambio_y / cambio_x) if cambio_x > 0 else 0.0
    maximo = max(sens.values()) if sens else 0.0
    if maximo == 0:
        return {"suficiente": False, "registros": len(validos),
                "motivo": "Los registros no muestran cambios en el rendimiento al variar las variables."}
    pesos = {v: round(s / maximo * 100.0, 1) for v, s in sens.items()}
    textos = {v: f"{ETIQUETAS[v]}: relevancia {p:.0f} según tus {sum(1 for x, _, _ in validos if x == v)} registros."
              for v, p in pesos.items()}
    return {"suficiente": True, "registros": len(validos), "pesos": pesos, "justificaciones": textos}
