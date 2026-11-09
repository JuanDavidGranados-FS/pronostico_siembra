"""Diagnóstico de inicio: ¿qué necesita la aplicación para funcionar y qué opciones hay?"""
from __future__ import annotations

import glob
import os
from dataclasses import dataclass
from typing import Callable, List, Optional

from src.aplicacion.gestor_relevancia import GestorRelevancia
from src.dominio.entidades import CULTIVOS_POR_DEFECTO
from src.dominio.interfaces import RepositorioCultivos

OK, ADVERTENCIA, FALTA = "ok", "advertencia", "falta"


@dataclass
class ItemDiagnostico:
    """Una verificación del diagnóstico, con su botón de acción directa si hay algo que arreglar."""
    clave: str
    titulo: str
    estado: str          # ok | advertencia | falta
    mensaje: str
    accion: Optional[str] = None      # texto del botón
    accion_id: Optional[str] = None   # identificador que la ventana sabe ejecutar


class Diagnostico:
    """Comprueba PostgreSQL, cultivos, configuración de relevancia y archivos JSON de entrada."""

    def __init__(self, modo_bd: str, probar_bd: Callable[[], bool], repo_cultivos: RepositorioCultivos,
                 gestor_relevancia: GestorRelevancia, carpeta_entrada: str) -> None:
        self.modo_bd, self.probar_bd = modo_bd, probar_bd
        self.repo_cultivos, self.gestor_relevancia, self.carpeta_entrada = repo_cultivos, gestor_relevancia, carpeta_entrada

    def ejecutar(self) -> List[ItemDiagnostico]:
        """Devuelve los cuatro ítems del panel de estado."""
        items: List[ItemDiagnostico] = []
        try:
            bd_ok = self.modo_bd == "PostgreSQL" and self.probar_bd()
        except Exception:
            bd_ok = False
        items.append(ItemDiagnostico("bd", "Base de datos", OK if bd_ok else ADVERTENCIA,
                                     "Conectado a PostgreSQL." if bd_ok else
                                     "Sin PostgreSQL: puedes trabajar, pero el historial se perderá al cerrar.",
                                     None if bd_ok else "Configurar BD", None if bd_ok else "configurar_bd"))
        try:
            n = len(self.repo_cultivos.listar())
        except Exception:
            n = 0
        items.append(ItemDiagnostico("cultivos", "Cultivos", OK if n else FALTA,
                                     f"{n} cultivo{'s' if n != 1 else ''} disponible{'s' if n != 1 else ''}." if n else
                                     "Aún no hay cultivos para elegir.",
                                     None if n else "Cargar cultivo por defecto", None if n else "cargar_cultivos"))
        n_rel = len(self.gestor_relevancia.listar())
        items.append(ItemDiagnostico("relevancia", "Factor de Relevancia", OK if n_rel else ADVERTENCIA,
                                     f"{n_rel} configuración guardada." if n_rel == 1 else
                                     f"{n_rel} configuraciones guardadas." if n_rel else
                                     "No hay configuración guardada: se usarán los valores sugeridos.",
                                     None if n_rel else "Crear Factor de Relevancia", None if n_rel else "crear_relevancia"))
        n_json = len(glob.glob(os.path.join(self.carpeta_entrada, "*.json"))) if os.path.isdir(self.carpeta_entrada) else 0
        items.append(ItemDiagnostico("json", "Archivos JSON de entrada", OK if n_json else ADVERTENCIA,
                                     f"{n_json} archivo{'s' if n_json != 1 else ''} listo{'s' if n_json != 1 else ''} para cargar." if n_json else
                                     "No hay archivos JSON (es opcional: sirve para datos de un simulador).",
                                     None if n_json else "Cargar JSON", None if n_json else "cargar_json"))
        return items

    @staticmethod
    def listo(items: List[ItemDiagnostico]) -> bool:
        """Se puede comenzar mientras no haya nada en rojo."""
        return all(i.estado != FALTA for i in items)

    @staticmethod
    def instrucciones_bd() -> str:
        """Pasos para activar PostgreSQL."""
        return ("1. Instala Docker (o PostgreSQL).\n"
                "2. Copia «.env.example» como «.env» y ajusta las credenciales si hace falta.\n"
                "3. En la carpeta del programa ejecuta:\n"
                "      docker compose -f docker/docker-compose.yml up -d\n"
                "4. Cierra y vuelve a abrir la aplicación.\n\n"
                "Mientras tanto puedes usar el programa: guardará todo en memoria temporal.")

    def cargar_cultivos_defecto(self) -> int:
        """Inserta el catálogo inicial de cultivos y devuelve cuántos agregó."""
        for c in CULTIVOS_POR_DEFECTO:
            self.repo_cultivos.guardar(dict(c))
        return len(CULTIVOS_POR_DEFECTO)

    def crear_relevancia_defecto(self) -> int:
        """Guarda la configuración de relevancia por defecto."""
        return self.gestor_relevancia.crear_defecto()
