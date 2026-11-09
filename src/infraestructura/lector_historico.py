"""Lectura de archivos históricos (CSV o Excel) para calcular la relevancia por correlación."""
from __future__ import annotations

import csv
import os
from typing import Any, Dict, List


def leer_historico(ruta: str) -> List[Dict[str, Any]]:
    """Lee un .csv, .xlsx o .xlsm y devuelve una lista de filas (diccionarios columna → valor).

    Lanza ValueError con un mensaje entendible si el archivo no existe, está vacío o tiene un formato no soportado.
    """
    if not os.path.isfile(ruta):
        raise ValueError("No encontré el archivo.")
    ext = os.path.splitext(ruta)[1].lower()
    if ext in (".csv", ".txt"):
        return _leer_csv(ruta)
    if ext in (".xlsx", ".xlsm"):
        return _leer_excel(ruta)
    raise ValueError("Formato no soportado: usa un archivo CSV o Excel (.xlsx).")


def _leer_csv(ruta: str) -> List[Dict[str, Any]]:
    """CSV con delimitador detectado (coma, punto y coma o tabulador) y codificación UTF-8 (con o sin BOM) o Latin-1."""
    for codificacion in ("utf-8-sig", "latin-1"):
        try:
            with open(ruta, "r", encoding=codificacion, newline="") as f:
                muestra = f.read(4096)
                f.seek(0)
                try:
                    dialecto = csv.Sniffer().sniff(muestra, delimiters=",;\t")
                except csv.Error:
                    dialecto = csv.excel
                filas = [dict(f) for f in csv.DictReader(f, dialect=dialecto)]
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("No pude leer el texto del archivo (codificación desconocida).")
    if not filas:
        raise ValueError("El archivo no tiene filas de datos.")
    return filas


def _leer_excel(ruta: str) -> List[Dict[str, Any]]:
    """Primera hoja de un libro de Excel; la primera fila son los encabezados."""
    try:
        from openpyxl import load_workbook
        libro = load_workbook(ruta, read_only=True, data_only=True)
    except ImportError as exc:
        raise ValueError("Falta la biblioteca openpyxl para leer Excel (pip install openpyxl).") from exc
    except Exception as exc:
        raise ValueError("No pude abrir el archivo de Excel; puede estar dañado o protegido.") from exc
    try:
        filas = list(libro.worksheets[0].iter_rows(values_only=True))
    finally:
        libro.close()
    if len(filas) < 2:
        raise ValueError("La hoja no tiene filas de datos.")
    encabezados = [str(c).strip() if c is not None else f"columna{i}" for i, c in enumerate(filas[0], 1)]
    return [dict(zip(encabezados, f)) for f in filas[1:] if any(c is not None for c in f)]
