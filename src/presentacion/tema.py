"""Tema visual: paleta, tipografía y registro de los temas claro/oscuro en ttkbootstrap."""
from __future__ import annotations

import tkinter.font as tkfont
from dataclasses import dataclass
from typing import Dict

import ttkbootstrap as ttk
from ttkbootstrap.style import Style, ThemeDefinition


@dataclass(frozen=True)
class Paleta:
    """Colores semánticos de la interfaz."""
    nombre: str
    oscuro: bool
    fondo: str        # lienzo de la ventana
    tarjeta: str      # superficies elevadas
    tarjeta_2: str    # superficies hundidas / campos
    borde: str
    texto: str
    suave: str        # texto secundario
    primario: str
    primario_h: str
    sobre_primario: str
    acento_suave: str  # fondo de pastillas / selección
    ok: str
    aviso: str
    error: str
    info: str


CLARO = Paleta("siembra_claro", False, "#f4f6f3", "#ffffff", "#eef1ed", "#dfe5df", "#1b2420", "#66726b",
               "#1f7a4d", "#186640", "#ffffff", "#e3f2e9", "#1f9d63", "#d98a00", "#d03b3b", "#2a78d6")
OSCURO = Paleta("siembra_oscuro", True, "#0f1613", "#18221d", "#202c26", "#2b3a33", "#eaf0ec", "#98a69e",
                "#3ecf8e", "#5adba2", "#06251a", "#1d3a2d", "#3ecf8e", "#f0b429", "#ef6b6b", "#5aa2f0")

FAMILIAS = ("Inter", "Segoe UI Variable", "Segoe UI", "SF Pro Text", "Helvetica Neue", "Ubuntu", "DejaVu Sans")


def familia() -> str:
    """Primera tipografía moderna instalada."""
    try:
        instaladas = set(tkfont.families())
    except Exception:
        return "TkDefaultFont"
    return next((f for f in FAMILIAS if f in instaladas), "TkDefaultFont")


def fuente(tam: int = 11, peso: str = "normal") -> tuple:
    """Fuente de la interfaz."""
    return (_FAMILIA[0], tam, peso)


_FAMILIA = ["TkDefaultFont"]


def _definicion(p: Paleta) -> ThemeDefinition:
    colores = dict(primary=p.primario, secondary=p.suave, success=p.ok, info=p.info, warning=p.aviso, danger=p.error,
                   light=p.tarjeta_2, dark=p.texto, bg=p.fondo, fg=p.texto, selectbg=p.acento_suave, selectfg=p.texto,
                   border=p.borde, inputfg=p.texto, inputbg=p.tarjeta_2, active=p.acento_suave)
    try:
        return ThemeDefinition(p.nombre, colores, mode="dark" if p.oscuro else "light")
    except TypeError:  # ttkbootstrap 1.x
        return ThemeDefinition(p.nombre, colores, themetype="dark" if p.oscuro else "light")


def registrar_temas() -> None:
    """Registra los dos temas (idempotente)."""
    estilo = Style.get_instance() or Style()
    for p in (CLARO, OSCURO):
        if p.nombre not in estilo.theme_names():
            estilo.register_theme(_definicion(p))


def aplicar(ventana, paleta: Paleta) -> None:
    """Activa el tema y ajusta los estilos de ttk usados en la aplicación."""
    _FAMILIA[0] = familia()
    registrar_temas()
    est = ttk.Style()
    est.theme_use(paleta.nombre)
    for nombre in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
        try:
            tkfont.nametofont(nombre).configure(family=_FAMILIA[0], size=11)
        except Exception:
            pass
    ventana.configure(background=paleta.fondo)
    est.configure("TFrame", background=paleta.fondo)
    est.configure("Tarjeta.TFrame", background=paleta.tarjeta)
    est.configure("Hundido.TFrame", background=paleta.tarjeta_2)
    est.configure("TLabel", background=paleta.fondo, foreground=paleta.texto, font=fuente(11))
    for nombre, fondo in (("Tarjeta.TLabel", paleta.tarjeta), ("Hundido.TLabel", paleta.tarjeta_2)):
        est.configure(nombre, background=fondo, foreground=paleta.texto, font=fuente(11))
    est.configure("Suave.TLabel", foreground=paleta.suave, font=fuente(10))
    est.configure("TarjetaSuave.TLabel", background=paleta.tarjeta, foreground=paleta.suave, font=fuente(10))
    est.configure("Titulo.TLabel", font=fuente(22, "bold"))
    est.configure("TarjetaTitulo.TLabel", background=paleta.tarjeta, font=fuente(14, "bold"))
    est.configure("Seccion.TLabel", font=fuente(15, "bold"))
    est.configure("Grande.TLabel", background=paleta.tarjeta, font=fuente(26, "bold"))
    est.configure("TEntry", padding=(10, 7), fieldbackground=paleta.tarjeta_2, foreground=paleta.texto,
                  bordercolor=paleta.borde, lightcolor=paleta.borde, darkcolor=paleta.borde, insertcolor=paleta.texto)
    est.configure("TCombobox", padding=(10, 7), fieldbackground=paleta.tarjeta_2, foreground=paleta.texto,
                  background=paleta.tarjeta_2, arrowcolor=paleta.suave, bordercolor=paleta.borde,
                  lightcolor=paleta.borde, darkcolor=paleta.borde)
    est.configure("TSpinbox", padding=(10, 7), fieldbackground=paleta.tarjeta_2, foreground=paleta.texto,
                  arrowcolor=paleta.suave, bordercolor=paleta.borde, lightcolor=paleta.borde, darkcolor=paleta.borde)
    est.configure("TScale", background=paleta.tarjeta, troughcolor=paleta.borde)
    est.configure("TCheckbutton", background=paleta.tarjeta, foreground=paleta.texto, font=fuente(11))
    est.configure("TRadiobutton", background=paleta.tarjeta, foreground=paleta.texto, font=fuente(11))
    est.configure("Treeview", background=paleta.tarjeta, fieldbackground=paleta.tarjeta, foreground=paleta.texto,
                  rowheight=34, borderwidth=0, font=fuente(10))
    est.configure("Treeview.Heading", background=paleta.tarjeta_2, foreground=paleta.suave, font=fuente(10, "bold"),
                  relief="flat", padding=(8, 8))
    est.map("Treeview", background=[("selected", paleta.acento_suave)], foreground=[("selected", paleta.texto)])
    est.configure("TProgressbar", thickness=8, troughcolor=paleta.borde, background=paleta.primario, borderwidth=0)
    est.configure("TNotebook", background=paleta.fondo, borderwidth=0)
    est.configure("TNotebook.Tab", padding=(14, 8), background=paleta.fondo, foreground=paleta.suave)
    est.map("TNotebook.Tab", foreground=[("selected", paleta.primario)], background=[("selected", paleta.fondo)])
    est.configure("Vertical.TScrollbar", background=paleta.borde, troughcolor=paleta.fondo, arrowsize=0, borderwidth=0)
    ventana.option_add("*TCombobox*Listbox.background", paleta.tarjeta)
    ventana.option_add("*TCombobox*Listbox.foreground", paleta.texto)
    ventana.option_add("*TCombobox*Listbox.selectBackground", paleta.acento_suave)
    ventana.option_add("*TCombobox*Listbox.selectForeground", paleta.texto)
    ventana.option_add("*Font", fuente(11))
