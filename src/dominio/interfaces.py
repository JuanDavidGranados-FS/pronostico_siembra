"""Interfaces (puertos) que la infraestructura debe implementar."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class RepositorioCultivos(ABC):
    """Persistencia del catálogo de cultivos."""
    @abstractmethod
    def guardar(self, cultivo: Dict[str, Any]) -> int: """Guarda un cultivo y devuelve su id."""
    @abstractmethod
    def obtener(self, id_cultivo: int) -> Optional[Dict[str, Any]]: """Obtiene un cultivo por id."""
    @abstractmethod
    def listar(self) -> List[Dict[str, Any]]: """Lista todos los cultivos."""
    @abstractmethod
    def eliminar(self, id_cultivo: int) -> bool: """Elimina un cultivo; True si existía."""


class RepositorioConfiguraciones(ABC):
    """Persistencia de configuraciones de simulación."""
    @abstractmethod
    def guardar(self, nombre: str, datos: Dict[str, Any]) -> int: """Guarda una configuración."""
    @abstractmethod
    def obtener(self, id_config: int) -> Optional[Dict[str, Any]]: """Obtiene una configuración."""
    @abstractmethod
    def listar(self) -> List[Dict[str, Any]]: """Lista configuraciones."""
    @abstractmethod
    def eliminar(self, id_config: int) -> bool: """Elimina una configuración."""


class RepositorioHistorial(ABC):
    """Persistencia del historial de simulaciones."""
    @abstractmethod
    def guardar(self, resultado: Dict[str, Any], configuracion_id: Optional[int] = None,
                nombre: str = "") -> int: """Guarda un resultado con un nombre opcional."""
    @abstractmethod
    def obtener(self, id_sim: int) -> Optional[Dict[str, Any]]: """Obtiene una simulación (incluye `resultado_completo`)."""
    @abstractmethod
    def listar(self, limite: int = 50) -> List[Dict[str, Any]]: """Lista las simulaciones más recientes."""
    @abstractmethod
    def renombrar(self, id_sim: int, nombre: str) -> bool: """Cambia el nombre de una simulación."""
    @abstractmethod
    def eliminar(self, id_sim: int) -> bool: """Elimina una simulación."""


class RepositorioDatosExternos(ABC):
    """Registro de datos recibidos de simuladores externos."""
    @abstractmethod
    def guardar(self, origen: str, datos: Dict[str, Any], valido: bool = True) -> int: """Registra datos externos."""
    @abstractmethod
    def ultimo(self) -> Optional[Dict[str, Any]]: """Devuelve el último registro."""


class RepositorioConfigRelevancia(ABC):
    """Persistencia de perfiles de Factor de Relevancia."""
    @abstractmethod
    def guardar(self, config: Dict[str, Any]) -> int: """Guarda un perfil {nombre, pesos, metodo, autor, notas, fecha}."""
    @abstractmethod
    def obtener(self, id_config: int) -> Optional[Dict[str, Any]]: """Obtiene un perfil."""
    @abstractmethod
    def listar(self) -> List[Dict[str, Any]]: """Lista los perfiles."""
    @abstractmethod
    def eliminar(self, id_config: int) -> bool: """Elimina un perfil."""


class RepositorioMatrices(ABC):
    """Persistencia de matrices de transición de Márkov."""
    @abstractmethod
    def guardar(self, nombre: str, tipo: str, estados: List[str], matriz: List[List[float]]) -> int: """Guarda una matriz."""
    @abstractmethod
    def listar(self, tipo: Optional[str] = None) -> List[Dict[str, Any]]: """Lista matrices, opcionalmente de un tipo."""
    @abstractmethod
    def obtener(self, id_matriz: int) -> Optional[Dict[str, Any]]: """Obtiene una matriz."""
    @abstractmethod
    def eliminar(self, id_matriz: int) -> bool: """Elimina una matriz."""


class RepositorioRegistrosCampo(ABC):
    """Persistencia del diario de campo (experimentos del usuario)."""
    @abstractmethod
    def guardar(self, registro: Dict[str, Any]) -> int: """Guarda {temporada, variable, valor, rendimiento}."""
    @abstractmethod
    def listar(self) -> List[Dict[str, Any]]: """Lista los registros."""
    @abstractmethod
    def eliminar(self, id_registro: int) -> bool: """Elimina un registro."""


class AdaptadorDatosExternos(ABC):
    """Lectura y validación de datos de simuladores externos."""
    @abstractmethod
    def leer_json(self, ruta: str) -> Dict[str, Any]: """Lee un archivo JSON."""
    @abstractmethod
    def validar(self, datos: Dict[str, Any]) -> List[str]: """Devuelve la lista de errores (vacía si es válido)."""
