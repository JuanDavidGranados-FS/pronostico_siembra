"""Entidades del dominio: Cultivo, Estado, ConfiguracionRelevancia y DatosEntrada (Python puro)."""
from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional


@dataclass
class Cultivo:
    """Cultivo con sus requerimientos agronómicos."""
    nombre: str
    dias_crecimiento: int
    temp_min: float
    temp_max: float
    requerimiento_agua: float   # mm/día
    resistencia_plagas: float   # 0-100
    rendimiento_base: float     # t/ha en condiciones ideales
    id: Optional[int] = None

    def a_dict(self) -> Dict[str, Any]:
        """Convierte el cultivo a diccionario."""
        return asdict(self)

    @classmethod
    def desde_dict(cls, d: Dict[str, Any]) -> "Cultivo":
        """Crea un cultivo desde un diccionario (acepta nombres de columna de la BD o de atributo)."""
        return cls(
            nombre=str(d["nombre"]),
            dias_crecimiento=int(d["dias_crecimiento"]),
            temp_min=float(d["temp_min"] if "temp_min" in d else d["temperatura_min"]),
            temp_max=float(d["temp_max"] if "temp_max" in d else d["temperatura_max"]),
            requerimiento_agua=float(d["requerimiento_agua"]),
            resistencia_plagas=float(d["resistencia_plagas"]),
            rendimiento_base=float(d["rendimiento_base"]),
            id=d.get("id"),
        )


@dataclass
class Estado:
    """Estado de una cadena de Márkov (salud, enfermedad o crecimiento)."""
    tipo: str
    valor: str
    transiciones: Dict[str, float] = field(default_factory=dict)


@dataclass
class ConfiguracionRelevancia:
    """Perfil de Factor de Relevancia: pesos 0-100 por variable, con metadatos para compartirlo."""
    nombre: str
    pesos: Dict[str, float]
    metodo: str = "manual"
    autor: str = ""
    notas: str = ""
    fecha: str = field(default_factory=lambda: date.today().isoformat())
    id: Optional[int] = None

    def a_dict(self) -> Dict[str, Any]:
        """Convierte la configuración a diccionario."""
        return asdict(self)


CULTIVOS_POR_DEFECTO: List[Dict[str, Any]] = [{'nombre': 'Maíz',
  'dias_crecimiento': 120,
  'temperatura_min': 15,
  'temperatura_max': 32,
  'requerimiento_agua': 5.0,
  'resistencia_plagas': 60,
  'rendimiento_base': 8.0},
 {'nombre': 'Trigo',
  'dias_crecimiento': 140,
  'temperatura_min': 5,
  'temperatura_max': 24,
  'requerimiento_agua': 4.0,
  'resistencia_plagas': 55,
  'rendimiento_base': 5.0},
 {'nombre': 'Papa',
  'dias_crecimiento': 100,
  'temperatura_min': 8,
  'temperatura_max': 22,
  'requerimiento_agua': 4.5,
  'resistencia_plagas': 40,
  'rendimiento_base': 25.0},
 {'nombre': 'Arroz',
  'dias_crecimiento': 130,
  'temperatura_min': 20,
  'temperatura_max': 35,
  'requerimiento_agua': 8.0,
  'resistencia_plagas': 50,
  'rendimiento_base': 6.0}]

ESTADO_POR_DEFECTO: Dict[str, Dict[str, Any]] = {'salud': {'estados': ['Sano', 'Estresado', 'Enfermo', 'Muerto'],
           'matriz': [[0.97, 0.02, 0.007, 0.003],
                      [0.25, 0.6, 0.12, 0.03],
                      [0.05, 0.15, 0.65, 0.15],
                      [0.0, 0.0, 0.0, 1.0]],
           'estado_inicial': 'Sano',
           'rendimiento_por_estado': {'Sano': 1.0, 'Estresado': 0.6, 'Enfermo': 0.3, 'Muerto': 0.0}},
 'enfermedad': {'estados': ['Ninguna', 'Leve', 'Grave'],
                'matriz': [[0.94, 0.05, 0.01], [0.3, 0.6, 0.1], [0.05, 0.25, 0.7]],
                'estado_inicial': 'Ninguna',
                'rendimiento_por_estado': {'Ninguna': 1.0, 'Leve': 0.8, 'Grave': 0.4}},
 'crecimiento': {'estados': ['Germinación', 'Vegetativo', 'Floración', 'Madurez'],
                 'matriz': [[0.7, 0.3, 0.0, 0.0],
                            [0.0, 0.75, 0.25, 0.0],
                            [0.0, 0.0, 0.8, 0.2],
                            [0.0, 0.0, 0.0, 1.0]],
                 'estado_inicial': 'Germinación',
                 'rendimiento_por_estado': {'Germinación': 0.3,
                                            'Vegetativo': 0.6,
                                            'Floración': 0.85,
                                            'Madurez': 1.0}}}

ESTOCASTICOS_POR_DEFECTO: Dict[str, Dict[str, Any]] = {'temperatura': {'tipo': 'normal',
                 'parametros': {'media': 22.0, 'std': 3.0},
                 'amplitud_estacional': 6.0,
                 'dia_pico': 200},
 'lluvia': {'tipo': 'triangular',
            'parametros': {'min': 0.0, 'moda': 4.0, 'max': 15.0},
            'amplitud_estacional': 3.0,
            'dia_pico': 100},
 'humedad': {'tipo': 'uniforme',
             'parametros': {'min': 50.0, 'max': 85.0},
             'amplitud_estacional': 0.0,
             'dia_pico': 100}}

PESOS_POR_DEFECTO: Dict[str, float] = {'agua': 80, 'temperatura': 70, 'ph': 40, 'nutrientes': 60, 'humedad': 50}

EVENTOS_RAROS_POR_DEFECTO: Dict[str, Dict[str, float]] = {'plagas': {'tasa_mensual': 1.0, 'perdida': 0.08},
 'heladas': {'tasa_mensual': 0.1, 'perdida': 0.3},
 'lluvias_intensas': {'tasa_mensual': 0.3, 'perdida': 0.1}}

PLAN_POR_DEFECTO: Dict[str, float] = {'temporadas': 1,
 'media_descendientes': 2.5,
 'plantas_iniciales': 100,
 'capacidad': 1000,
 'agotamiento_suelo': 0.05}


@dataclass
class DatosEntrada:
    """Conjunto completo de datos de una simulación."""
    cultivo: Cultivo
    deterministas: Dict[str, Any]
    estocasticos: Dict[str, Dict[str, Any]]
    estado: Dict[str, Dict[str, Any]]
    pesos: Dict[str, float]
    iteraciones: int = 10000
    semilla: Optional[int] = None
    ventana_dias: int = 365   # días a explorar a partir de la fecha inicial
    paso_dias: int = 15       # separación entre fechas candidatas
    esfuerzo: float = 0.0     # costo/esfuerzo relativo (>= 0)
    eventos_raros: Dict[str, Dict[str, float]] = field(default_factory=lambda: copy.deepcopy(EVENTOS_RAROS_POR_DEFECTO))
    plan: Dict[str, float] = field(default_factory=lambda: dict(PLAN_POR_DEFECTO))
    nombre: str = ""

    def a_dict(self) -> Dict[str, Any]:
        """Convierte los datos de entrada a un diccionario serializable."""
        return copy.deepcopy(asdict(self))

    @classmethod
    def desde_dict(cls, d: Dict[str, Any]) -> "DatosEntrada":
        """Crea los datos desde un diccionario, completando con valores por defecto lo que falte."""
        base = datos_por_defecto()
        cultivo = d.get("cultivo")
        return cls(
            cultivo=Cultivo.desde_dict(cultivo) if isinstance(cultivo, dict) else base.cultivo,
            deterministas={**base.deterministas, **d.get("deterministas", {})},
            estocasticos=copy.deepcopy(d.get("estocasticos") or base.estocasticos),
            estado=copy.deepcopy(d.get("estado") or base.estado),
            pesos={**base.pesos, **d.get("pesos", {})},
            iteraciones=int(d.get("iteraciones", base.iteraciones)),
            semilla=d.get("semilla"),
            ventana_dias=int(d.get("ventana_dias", base.ventana_dias)),
            paso_dias=int(d.get("paso_dias", base.paso_dias)),
            esfuerzo=float(d.get("esfuerzo", base.esfuerzo)),
            eventos_raros=copy.deepcopy(d.get("eventos_raros") or base.eventos_raros),
            plan={**base.plan, **d.get("plan", {})},
            nombre=str(d.get("nombre", "")),
        )


def datos_por_defecto() -> DatosEntrada:
    """Devuelve datos de entrada con valores por defecto razonables (maíz, clima templado)."""
    return DatosEntrada(
        cultivo=Cultivo("Maíz", 120, 15.0, 32.0, 5.0, 60.0, 8.0),
        deterministas={"fecha": date.today().isoformat(), "ph": 6.5, "nitrogeno": 100.0,
                       "fosforo": 50.0, "potasio": 100.0, "resistencia": 60.0, "agua": 1.0},
        estocasticos=copy.deepcopy(ESTOCASTICOS_POR_DEFECTO),
        estado=copy.deepcopy(ESTADO_POR_DEFECTO),
        pesos=dict(PESOS_POR_DEFECTO),
    )
