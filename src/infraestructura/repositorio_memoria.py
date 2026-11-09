"""Repositorios en memoria: alternativa cuando PostgreSQL no está disponible (y para pruebas)."""
from __future__ import annotations

import copy
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.dominio.entidades import CULTIVOS_POR_DEFECTO
from src.dominio.interfaces import (RepositorioConfigRelevancia, RepositorioConfiguraciones, RepositorioCultivos,
                                    RepositorioDatosExternos, RepositorioHistorial, RepositorioMatrices,
                                    RepositorioRegistrosCampo)


class _Base:
    """Almacén clave-valor con ids autoincrementales."""

    def __init__(self) -> None:
        self._filas: Dict[int, Dict[str, Any]] = {}
        self._sig = 1

    def _insertar(self, fila: Dict[str, Any]) -> int:
        fila = copy.deepcopy(fila)
        fila["id"] = self._sig
        self._filas[self._sig] = fila
        self._sig += 1
        return fila["id"]

    def obtener(self, id_: int) -> Optional[Dict[str, Any]]:
        """Devuelve una copia de la fila o None."""
        fila = self._filas.get(id_)
        return copy.deepcopy(fila) if fila else None

    def eliminar(self, id_: int) -> bool:
        """Elimina la fila; True si existía."""
        return self._filas.pop(id_, None) is not None

    def _todas(self) -> List[Dict[str, Any]]:
        return [copy.deepcopy(f) for f in self._filas.values()]


class RepositorioCultivosMemoria(_Base, RepositorioCultivos):
    """Catálogo de cultivos en memoria (precargado)."""

    def __init__(self, precargar: bool = True) -> None:
        super().__init__()
        if precargar:
            for c in CULTIVOS_POR_DEFECTO:
                self._insertar(c)

    def guardar(self, cultivo: Dict[str, Any]) -> int:
        """Guarda un cultivo."""
        return self._insertar(cultivo)

    def listar(self) -> List[Dict[str, Any]]:
        """Lista los cultivos."""
        return self._todas()


class RepositorioConfiguracionesMemoria(_Base, RepositorioConfiguraciones):
    """Configuraciones de simulación en memoria."""

    def guardar(self, nombre: str, datos: Dict[str, Any]) -> int:
        """Guarda una configuración."""
        return self._insertar({"nombre": nombre, "datos": datos, "fecha_creacion": datetime.now().isoformat()})

    def listar(self) -> List[Dict[str, Any]]:
        """Lista las configuraciones."""
        return self._todas()


class RepositorioHistorialMemoria(_Base, RepositorioHistorial):
    """Historial en memoria."""

    def guardar(self, resultado: Dict[str, Any], configuracion_id: Optional[int] = None, nombre: str = "") -> int:
        """Guarda un resultado."""
        fo = resultado["fecha_optima"]
        return self._insertar({"configuracion_id": configuracion_id, "nombre": nombre or resultado.get("nombre", ""),
                               "fecha_optima": fo["fecha"], "kpi_esperado": fo["kpi"],
                               "probabilidad_exito": fo["probabilidad_exito"] * 100,
                               "resultado_completo": resultado, "fecha_ejecucion": datetime.now().isoformat()})

    def listar(self, limite: int = 50) -> List[Dict[str, Any]]:
        """Lista las simulaciones más recientes primero (sin el resultado completo, como en PostgreSQL)."""
        filas = sorted(self._filas.values(), key=lambda f: f["id"], reverse=True)[:limite]
        return [{k: copy.deepcopy(v) for k, v in f.items() if k != "resultado_completo"} for f in filas]

    def renombrar(self, id_sim: int, nombre: str) -> bool:
        """Cambia el nombre de una simulación."""
        fila = self._filas.get(id_sim)
        if not fila:
            return False
        fila["nombre"] = nombre
        fila["resultado_completo"]["nombre"] = nombre
        return True


class RepositorioDatosExternosMemoria(_Base, RepositorioDatosExternos):
    """Registro de datos externos en memoria."""

    def guardar(self, origen: str, datos: Dict[str, Any], valido: bool = True) -> int:
        """Registra datos externos."""
        return self._insertar({"origen": origen, "datos": datos, "valido": valido,
                               "fecha_recepcion": datetime.now().isoformat()})

    def ultimo(self) -> Optional[Dict[str, Any]]:
        """Devuelve el último registro."""
        return self.obtener(max(self._filas)) if self._filas else None


class RepositorioConfigRelevanciaMemoria(_Base, RepositorioConfigRelevancia):
    """Perfiles de relevancia en memoria."""

    def guardar(self, config: Dict[str, Any]) -> int:
        """Guarda un perfil de relevancia."""
        return self._insertar({**config, "fecha_creacion": datetime.now().isoformat()})

    def listar(self) -> List[Dict[str, Any]]:
        """Lista los perfiles (más recientes primero)."""
        return sorted(self._todas(), key=lambda f: f["id"], reverse=True)


class RepositorioMatricesMemoria(_Base, RepositorioMatrices):
    """Matrices de Márkov en memoria."""

    def guardar(self, nombre: str, tipo: str, estados: List[str], matriz: List[List[float]]) -> int:
        """Guarda una matriz."""
        return self._insertar({"nombre": nombre, "tipo": tipo, "estados": list(estados), "matriz_transicion": matriz})

    def listar(self, tipo: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lista las matrices, opcionalmente solo de un tipo."""
        return [f for f in self._todas() if tipo is None or f["tipo"] == tipo]


class RepositorioRegistrosCampoMemoria(_Base, RepositorioRegistrosCampo):
    """Diario de campo en memoria."""

    def guardar(self, registro: Dict[str, Any]) -> int:
        """Guarda un registro de campo."""
        return self._insertar(registro)

    def listar(self) -> List[Dict[str, Any]]:
        """Lista los registros."""
        return self._todas()
