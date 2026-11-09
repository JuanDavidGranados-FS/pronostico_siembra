"""Validación de los datos de entrada. Cada método devuelve una lista de errores (vacía = válido)."""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from src.dominio.entidades import Cultivo, DatosEntrada
from src.dominio.markov import CadenaMarkov
from src.dominio.montecarlo import TIPOS_DISTRIBUCION

VARIABLES_ESTOCASTICAS = ("temperatura", "lluvia", "humedad")
CADENAS_REQUERIDAS = ("salud", "enfermedad", "crecimiento")
PARAMETROS = {"normal": ("media", "std"), "uniforme": ("min", "max"), "triangular": ("min", "moda", "max")}


class ErrorValidacion(ValueError):
    """Error de validación con la lista completa de problemas detectados."""

    def __init__(self, errores: List[str]) -> None:
        super().__init__("; ".join(errores))
        self.errores = list(errores)


def _num(valor: Any) -> Optional[float]:
    """Convierte a float si es un número real finito; si no, None."""
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return None
    return float(valor) if valor == valor and abs(valor) != float("inf") else None


class Validador:
    """Valida cada tipo de dato del sistema."""

    def validar_cultivo(self, c: Cultivo) -> List[str]:
        """Valida los parámetros del cultivo."""
        e: List[str] = []
        if not c.nombre or not str(c.nombre).strip():
            e.append("El cultivo debe tener nombre.")
        if not isinstance(c.dias_crecimiento, int) or not 7 <= c.dias_crecimiento <= 730:
            e.append("Los días de crecimiento deben ser un entero entre 7 y 730.")
        if _num(c.temp_min) is None or _num(c.temp_max) is None or not c.temp_min < c.temp_max:
            e.append("La temperatura mínima debe ser menor que la máxima.")
        if _num(c.requerimiento_agua) is None or c.requerimiento_agua <= 0:
            e.append("El requerimiento de agua debe ser mayor que 0.")
        if _num(c.resistencia_plagas) is None or not 0 <= c.resistencia_plagas <= 100:
            e.append("La resistencia a plagas del cultivo debe estar entre 0 y 100.")
        if _num(c.rendimiento_base) is None or c.rendimiento_base <= 0:
            e.append("El rendimiento base debe ser mayor que 0.")
        return e

    def validar_deterministas(self, d: Dict[str, Any]) -> List[str]:
        """Valida fecha, pH, N/P/K, resistencia y agua."""
        e: List[str] = []
        try:
            date.fromisoformat(str(d.get("fecha")))
        except ValueError:
            e.append("La fecha debe tener el formato AAAA-MM-DD.")
        rangos = {"ph": (0, 14), "nitrogeno": (0, 1e4), "fosforo": (0, 1e4), "potasio": (0, 1e4),
                  "resistencia": (0, 100), "agua": (0, 1e3)}
        for clave, (lo, hi) in rangos.items():
            v = _num(d.get(clave))
            if v is None:
                e.append(f"'{clave}' es obligatorio y debe ser numérico.")
            elif not lo <= v <= hi:
                e.append(f"'{clave}' debe estar entre {lo} y {hi}.")
        return e

    def validar_estocasticos(self, est: Dict[str, Dict[str, Any]]) -> List[str]:
        """Valida las distribuciones de temperatura, lluvia y humedad."""
        e: List[str] = []
        for var in VARIABLES_ESTOCASTICAS:
            dist = est.get(var)
            if not isinstance(dist, dict):
                e.append(f"Falta la distribución de '{var}'.")
                continue
            tipo = str(dist.get("tipo", "")).lower()
            if tipo not in TIPOS_DISTRIBUCION:
                e.append(f"'{var}': tipo de distribución inválido ({tipo!r}).")
                continue
            p = dist.get("parametros", {})
            vals = {k: _num(p.get(k)) for k in PARAMETROS[tipo]}
            if any(v is None for v in vals.values()):
                e.append(f"'{var}': parámetros incompletos o no numéricos {PARAMETROS[tipo]}.")
                continue
            if tipo == "normal" and vals["std"] < 0:
                e.append(f"'{var}': la desviación estándar no puede ser negativa.")
            if tipo == "uniforme" and vals["min"] > vals["max"]:
                e.append(f"'{var}': min no puede superar a max.")
            if tipo == "triangular" and not vals["min"] <= vals["moda"] <= vals["max"]:
                e.append(f"'{var}': debe cumplirse min <= moda <= max.")
            for extra in ("amplitud_estacional", "dia_pico"):
                if extra in dist and _num(dist[extra]) is None:
                    e.append(f"'{var}': '{extra}' debe ser numérico.")
        return e

    def validar_estado(self, estado: Dict[str, Dict[str, Any]]) -> List[str]:
        """Valida las cadenas de Márkov (matrices estocásticas y estado inicial)."""
        e: List[str] = []
        for nombre in CADENAS_REQUERIDAS:
            cfg = estado.get(nombre)
            if not isinstance(cfg, dict):
                e.append(f"Falta la cadena de Márkov '{nombre}'.")
                continue
            try:
                CadenaMarkov(cfg.get("estados", []), cfg.get("matriz"))
            except ValueError as exc:
                e.append(f"Cadena '{nombre}': {exc}")
                continue
            if cfg.get("estado_inicial") not in cfg["estados"]:
                e.append(f"Cadena '{nombre}': el estado inicial no pertenece a los estados.")
        return e

    def validar_pesos(self, pesos: Dict[str, Any]) -> List[str]:
        """Valida que cada peso esté entre 0 y 100."""
        e = []
        for k, v in pesos.items():
            n = _num(v)
            if n is None or not 0 <= n <= 100:
                e.append(f"El peso de '{k}' debe estar entre 0 y 100.")
        return e

    def validar_eventos_raros(self, eventos: Dict[str, Dict[str, Any]]) -> List[str]:
        """Valida la tasa mensual (>= 0) y la pérdida por evento (0-1) de cada evento raro."""
        e: List[str] = []
        if not isinstance(eventos, dict):
            return ["Los eventos raros deben ser un conjunto de eventos con tasa y pérdida."]
        for nombre, cfg in eventos.items():
            tasa = _num(cfg.get("tasa_mensual")) if isinstance(cfg, dict) else None
            perdida = _num(cfg.get("perdida")) if isinstance(cfg, dict) else None
            if tasa is None or not 0 <= tasa <= 100:
                e.append(f"Evento '{nombre}': la tasa mensual debe estar entre 0 y 100.")
            if perdida is None or not 0 <= perdida <= 1:
                e.append(f"Evento '{nombre}': la pérdida por evento debe estar entre 0 y 1 (0 % a 100 %).")
        return e

    def validar_plan(self, plan: Dict[str, Any]) -> List[str]:
        """Valida el plan multi-temporada (Galton-Watson)."""
        e: List[str] = []
        reglas = {"temporadas": (1, 30, True), "media_descendientes": (0, 100, False),
                  "plantas_iniciales": (1, 1e6, True), "capacidad": (1, 1e7, True), "agotamiento_suelo": (0, 0.9, False)}
        for clave, (lo, hi, entero) in reglas.items():
            v = _num(plan.get(clave))
            if v is None or not lo <= v <= hi or (entero and v != int(v)):
                e.append(f"Plan: '{clave}' debe ser un número{' entero' if entero else ''} entre {lo:g} y {hi:g}.")
        if not e and plan["capacidad"] < plan["plantas_iniciales"]:
            e.append("Plan: la capacidad del terreno no puede ser menor que las plantas iniciales.")
        return e

    def validar_datos_entrada(self, datos: DatosEntrada) -> List[str]:
        """Valida todo el conjunto de datos de entrada."""
        e = self.validar_cultivo(datos.cultivo)
        e += self.validar_deterministas(datos.deterministas)
        e += self.validar_estocasticos(datos.estocasticos)
        e += self.validar_estado(datos.estado)
        e += self.validar_pesos(datos.pesos)
        e += self.validar_eventos_raros(datos.eventos_raros)
        e += self.validar_plan(datos.plan)
        if len(str(datos.nombre)) > 150:
            e.append("El nombre de la simulación no puede superar 150 caracteres.")
        if not isinstance(datos.iteraciones, int) or not 100 <= datos.iteraciones <= 1_000_000:
            e.append("Las iteraciones deben ser un entero entre 100 y 1.000.000.")
        if not isinstance(datos.ventana_dias, int) or not 1 <= datos.ventana_dias <= 730:
            e.append("La ventana de búsqueda debe estar entre 1 y 730 días.")
        if not isinstance(datos.paso_dias, int) or not 1 <= datos.paso_dias <= 365:
            e.append("El paso entre fechas debe estar entre 1 y 365 días.")
        elif isinstance(datos.ventana_dias, int) and datos.ventana_dias // datos.paso_dias > 400:
            e.append("Demasiadas fechas candidatas (máximo 400); aumente el paso.")
        if _num(datos.esfuerzo) is None or datos.esfuerzo < 0:
            e.append("El esfuerzo debe ser un número mayor o igual a 0.")
        return e
