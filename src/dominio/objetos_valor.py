"""Objetos de valor inmutables del dominio."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class KPI:
    """Indicador final: rendimiento esperado ajustado por relevancia y esfuerzo."""
    valor: float
    rendimiento_esperado: float
    factor_relevancia: float
    esfuerzo: float


@dataclass(frozen=True)
class FechaOptima:
    """Fecha de siembra recomendada."""
    fecha: date
    kpi: float
    probabilidad_exito: float  # 0-1
    viable: bool


@dataclass(frozen=True)
class ResultadoSimulacion:
    """Resultado completo de una simulación."""
    fecha_optima: FechaOptima
    kpi: KPI
    resultados_por_fecha: Dict[str, Dict[str, float]]
    estadisticas_rendimiento: Dict[str, float]
    histograma_rendimiento: Dict[str, list]
    evolucion_estados: Dict[str, Dict[str, list]]
    semilla: int
    iteraciones: int
    id_historial: Optional[int] = None
    nombre: str = ""
    cultivo: str = ""
    justificacion: str = ""
    justificacion_detalle: List[str] = field(default_factory=list)
    comparaciones: List[Dict[str, Any]] = field(default_factory=list)
    riesgos: List[Dict[str, Any]] = field(default_factory=list)
    plan_temporadas: Dict[str, Any] = field(default_factory=dict)
    duracion_segundos: float = 0.0
    pesos: Dict[str, float] = field(default_factory=dict)

    def con_id(self, id_historial: Optional[int]) -> "ResultadoSimulacion":
        """Devuelve una copia con el identificador de historial asignado."""
        return replace(self, id_historial=id_historial)

    def a_dict(self) -> Dict[str, Any]:
        """Convierte el resultado a un diccionario serializable a JSON."""
        f = self.fecha_optima
        k = self.kpi
        return {
            "fecha_optima": {"fecha": f.fecha.isoformat(), "kpi": f.kpi,
                             "probabilidad_exito": f.probabilidad_exito, "viable": f.viable},
            "kpi": {"valor": k.valor, "rendimiento_esperado": k.rendimiento_esperado,
                    "factor_relevancia": k.factor_relevancia, "esfuerzo": k.esfuerzo},
            "resultados_por_fecha": self.resultados_por_fecha,
            "estadisticas_rendimiento": self.estadisticas_rendimiento,
            "histograma_rendimiento": self.histograma_rendimiento,
            "evolucion_estados": self.evolucion_estados,
            "semilla": self.semilla,
            "iteraciones": self.iteraciones,
            "id_historial": self.id_historial,
            "nombre": self.nombre,
            "cultivo": self.cultivo,
            "justificacion": self.justificacion,
            "justificacion_detalle": list(self.justificacion_detalle),
            "comparaciones": list(self.comparaciones),
            "riesgos": list(self.riesgos),
            "plan_temporadas": dict(self.plan_temporadas),
            "duracion_segundos": self.duracion_segundos,
            "pesos": dict(self.pesos),
        }
