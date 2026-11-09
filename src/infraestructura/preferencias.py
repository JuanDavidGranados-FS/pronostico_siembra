"""Preferencias locales del usuario (tour visto, tema, borrador del formulario) en un archivo JSON."""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

log = logging.getLogger(__name__)


def carpeta_usuario() -> str:
    """Carpeta de datos locales: $SIEMBRA_HOME o ~/.pronostico_siembra."""
    return os.environ.get("SIEMBRA_HOME") or os.path.join(os.path.expanduser("~"), ".pronostico_siembra")


class Preferencias:
    """Lectura/escritura tolerante a fallos: nunca lanza excepciones (si no puede guardar, lo registra)."""

    def __init__(self, carpeta: str = "") -> None:
        self.carpeta = carpeta or carpeta_usuario()
        self.ruta = os.path.join(self.carpeta, "preferencias.json")
        self._datos: Dict[str, Any] = self._cargar()

    def _cargar(self) -> Dict[str, Any]:
        try:
            with open(self.ruta, "r", encoding="utf-8") as f:
                d = json.load(f)
            return d if isinstance(d, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def obtener(self, clave: str, defecto: Any = None) -> Any:
        """Valor guardado o `defecto`."""
        return self._datos.get(clave, defecto)

    def guardar(self, clave: str, valor: Any) -> None:
        """Guarda un valor serializable en disco."""
        self._datos[clave] = valor
        try:
            os.makedirs(self.carpeta, exist_ok=True)
            with open(self.ruta, "w", encoding="utf-8") as f:
                json.dump(self._datos, f, ensure_ascii=False, indent=2)
        except (OSError, TypeError):
            log.exception("No se pudieron guardar las preferencias")

    def borrar(self, clave: str) -> None:
        """Elimina una clave."""
        if clave in self._datos:
            self._datos.pop(clave)
            try:
                with open(self.ruta, "w", encoding="utf-8") as f:
                    json.dump(self._datos, f, ensure_ascii=False, indent=2)
            except OSError:
                log.exception("No se pudieron guardar las preferencias")
