"""Adaptador de intercambio JSON con simuladores externos, y exportación de resultados."""
from __future__ import annotations

import csv
import json
from typing import Any, Dict, List

from src.dominio.entidades import DatosEntrada
from src.dominio.interfaces import AdaptadorDatosExternos


class AdaptadorJSON(AdaptadorDatosExternos):
    """Lee/valida JSON externo, lo convierte a DatosEntrada y exporta resultados."""

    CAMPOS_OBLIGATORIOS = ("cultivo", "deterministas", "estocasticos")

    def leer_json(self, ruta: str) -> Dict[str, Any]:
        """Lee un archivo JSON (UTF-8); lanza ValueError si no es un objeto JSON válido."""
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                datos = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSON inválido: {exc}") from exc
        if not isinstance(datos, dict):
            raise ValueError("El JSON debe contener un objeto en la raíz.")
        return datos

    def validar(self, datos: Dict[str, Any]) -> List[str]:
        """Verifica campos obligatorios y que el contenido pueda convertirse a DatosEntrada."""
        errores = [f"Falta el campo obligatorio '{c}'." for c in self.CAMPOS_OBLIGATORIOS if c not in datos]
        if errores:
            return errores
        try:
            self.a_datos_entrada(datos)
        except (KeyError, TypeError, ValueError) as exc:
            errores.append(f"Contenido inválido: {exc!r}")
        return errores

    def a_datos_entrada(self, datos: Dict[str, Any]) -> DatosEntrada:
        """Convierte el diccionario externo en DatosEntrada (completa con valores por defecto)."""
        return DatosEntrada.desde_dict(datos)

    def escribir_json(self, ruta: str, datos: Dict[str, Any]) -> None:
        """Escribe un diccionario como JSON legible."""
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)

    def exportar_csv(self, ruta: str, resultado: Dict[str, Any]) -> None:
        """Exporta los resultados por fecha a CSV (una fila por fecha candidata)."""
        filas = resultado["resultados_por_fecha"]
        columnas = ["fecha"] + list(next(iter(filas.values())).keys())
        with open(ruta, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(columnas)
            for fecha, reg in filas.items():
                w.writerow([fecha] + [reg[c] for c in columnas[1:]])
