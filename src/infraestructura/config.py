"""Carga de configuración desde variables de entorno (.env)."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class ConfigBD:
    """Parámetros de conexión a PostgreSQL."""
    host: str = "localhost"
    port: int = 5432
    dbname: str = "pronostico_siembra"
    user: str = "postgres"
    password: str = "postgres"


def cargar_config() -> ConfigBD:
    """Lee `.env` (si existe) y devuelve la configuración de base de datos."""
    load_dotenv()
    return ConfigBD(host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "5432")),
                    dbname=os.getenv("DB_NAME", "pronostico_siembra"), user=os.getenv("DB_USER", "postgres"),
                    password=os.getenv("DB_PASSWORD", "postgres"))
