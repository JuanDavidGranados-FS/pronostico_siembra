"""Configuración de logging a archivo y consola."""
from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler


def configurar_logger(nivel: int = logging.INFO, archivo: str = "logs/app.log") -> logging.Logger:
    """Configura el logger raíz con salida a consola y archivo rotativo."""
    raiz = logging.getLogger()
    if getattr(raiz, "_siembra_configurado", False):
        return raiz
    raiz.setLevel(nivel)
    formato = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    consola = logging.StreamHandler()
    consola.setFormatter(formato)
    raiz.addHandler(consola)
    try:
        os.makedirs(os.path.dirname(archivo) or ".", exist_ok=True)
        fh = RotatingFileHandler(archivo, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        fh.setFormatter(formato)
        raiz.addHandler(fh)
    except OSError:
        raiz.warning("No se pudo crear el archivo de log %s; se usa solo la consola.", archivo)
    raiz._siembra_configurado = True  # type: ignore[attr-defined]
    return raiz
