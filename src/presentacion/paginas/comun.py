"""Piezas compartidas por las páginas."""
from __future__ import annotations

import tkinter as tk

from src.presentacion.tema import fuente


def encabezado(master, app, titulo: str, subtitulo: str = "") -> tk.Frame:
    """Título grande + una frase; nada más."""
    p = app.p
    f = tk.Frame(master, background=p.fondo)
    tk.Label(f, text=titulo, font=fuente(24, "bold"), foreground=p.texto, background=p.fondo).pack(anchor="w")
    if subtitulo:
        tk.Label(f, text=subtitulo, font=fuente(12), foreground=p.suave, background=p.fondo, wraplength=640, justify="left").pack(anchor="w", pady=(4, 0))
    return f


def numero(texto: str, defecto=None):
    """Convierte «1,5» o «1.5» a float; None si no es un número."""
    try:
        return float(str(texto).strip().replace(",", "."))
    except ValueError:
        return defecto
