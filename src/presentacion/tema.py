"""Tema visual: paleta, tipografía, registro de los temas claro/oscuro en ttkbootstrap y ajuste a pantallas de celular."""
from __future__ import annotations

import os
import sys
import tkinter.font as tkfont
from dataclasses import dataclass
from typing import Dict

import ttkbootstrap as ttk
from ttkbootstrap.style import Style, ThemeDefinition

# ----------------------------------------------------------------- modo celular
# Súbelo (p. ej. 1.2) si en el celular todo se ve pequeño; bájalo (0.85) si se ve muy grande.
AJUSTE_ESCALA_MOVIL = 1.0
# Puntos tipográficos que caben a lo ancho del lado corto de la pantalla (define el tamaño del texto en el celular).
_PUNTOS_LADO_CORTO = 330
_ESCALA_ESCRITORIO = 96 / 72  # píxeles por punto en un monitor normal

MOVIL = False   # True cuando la app corre en un celular (Android/Pydroid) o en una pantalla angosta
FACTOR = 1.0    # multiplica las medidas en píxeles pensadas para escritorio
ANCHO = 0       # ancho de la pantalla en píxeles
ALTO = 0        # alto de la pantalla en píxeles


def _es_android() -> bool:
    return hasattr(sys, "getandroidapilevel") or "ANDROID_ROOT" in os.environ or "ANDROID_DATA" in os.environ


def configurar_pantalla(ventana) -> None:
    """Detecta si es un celular y, si lo es, ajusta escala, tamaño de ventana y medidas.

    Se puede forzar con la variable de entorno SIEMBRA_MOVIL=1 (o desactivar con SIEMBRA_MOVIL=0).
    """
    global MOVIL, FACTOR, ANCHO, ALTO
    ANCHO, ALTO = ventana.winfo_screenwidth(), ventana.winfo_screenheight()
    forzado = os.environ.get("SIEMBRA_MOVIL", "").strip()
    MOVIL = forzado == "1" or (forzado != "0" and (_es_android() or ANCHO < 900))
    if not MOVIL:
        FACTOR = 1.0
        return
    try:
        ajuste = float(os.environ.get("SIEMBRA_ESCALA", AJUSTE_ESCALA_MOVIL))
    except ValueError:
        ajuste = AJUSTE_ESCALA_MOVIL
    escala = max(1.0, min(ANCHO, ALTO) / _PUNTOS_LADO_CORTO * ajuste)
    ventana.tk.call("tk", "scaling", escala)
    FACTOR = escala / _ESCALA_ESCRITORIO
    ventana.minsize(1, 1)
    ventana.geometry(f"{ANCHO}x{ALTO}+0+0")


def px(n: float) -> int:
    """Convierte una medida en píxeles de escritorio a la pantalla actual."""
    return int(round(n * FACTOR))


def ancho_texto(escritorio: int, margen: int = 48) -> int:
    """`wraplength` para textos fuera de las páginas (diálogos, globos): en el celular, el ancho de la pantalla."""
    if not MOVIL:
        return escritorio
    return max(px(120), min(px(escritorio), ANCHO - px(margen)))


def dialogo(v, tam_escritorio: str) -> None:
    """Tamaño de una ventana secundaria: el pedido en escritorio, pantalla completa en el celular."""
    v.geometry(f"{ANCHO}x{ALTO}+0+0" if MOVIL else tam_escritorio)


def lienzo(fig, master):
    """Lienzo Tk de una figura. En el celular se fija su tamaño en píxeles para que no se salga de la pantalla."""
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    c = FigureCanvasTkAgg(fig, master=master)
    if MOVIL:
        w = c.get_tk_widget()
        pw, ph = fig.get_size_inches()
        ancho = ANCHO - px(70)
        alto = int(ancho * ph / pw)

        def fijar(_e=None) -> None:
            if int(w.cget("width")) != ancho or int(w.cget("height")) != alto:
                w.configure(width=ancho, height=alto)
        w.bind("<Map>", fijar, add="+")
        fijar()
    return c


def figura(ancho_pulg: float, alto_pulg: float):
    """Figura de matplotlib del tamaño adecuado: en el celular ocupa el ancho de la pantalla con letra legible."""
    from matplotlib.figure import Figure
    if not MOVIL:
        return Figure(figsize=(ancho_pulg, alto_pulg), dpi=100)
    dpi = 100 * FACTOR * 0.8                 # densidad final deseada en pantalla
    ancho = max(2.5, (ANCHO - px(70)) / dpi)  # pulgadas para ocupar el ancho de la pantalla
    # En Linux, matplotlib ya multiplica por la escala de Tk (device pixel ratio); en otros sistemas no.
    ratio = FACTOR if sys.platform in ("linux", "win32") else 1.0
    return Figure(figsize=(ancho, ancho * max(alto_pulg / ancho_pulg, 0.75)), dpi=dpi / ratio)


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
    """Fuente de la interfaz (en el celular, los títulos grandes se reducen un poco)."""
    if MOVIL and tam >= 18:
        tam = round(tam * 0.8)
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
    est.configure("TEntry", padding=(px(10), px(7)), fieldbackground=paleta.tarjeta_2, foreground=paleta.texto,
                  bordercolor=paleta.borde, lightcolor=paleta.borde, darkcolor=paleta.borde, insertcolor=paleta.texto)
    est.configure("TCombobox", padding=(px(10), px(7)), fieldbackground=paleta.tarjeta_2, foreground=paleta.texto,
                  background=paleta.tarjeta_2, arrowcolor=paleta.suave, bordercolor=paleta.borde,
                  lightcolor=paleta.borde, darkcolor=paleta.borde)
    est.configure("TSpinbox", padding=(px(10), px(7)), fieldbackground=paleta.tarjeta_2, foreground=paleta.texto,
                  arrowcolor=paleta.suave, bordercolor=paleta.borde, lightcolor=paleta.borde, darkcolor=paleta.borde)
    est.configure("TScale", background=paleta.tarjeta, troughcolor=paleta.borde)
    est.configure("TCheckbutton", background=paleta.tarjeta, foreground=paleta.texto, font=fuente(11))
    est.configure("TRadiobutton", background=paleta.tarjeta, foreground=paleta.texto, font=fuente(11))
    est.configure("Treeview", background=paleta.tarjeta, fieldbackground=paleta.tarjeta, foreground=paleta.texto,
                  rowheight=px(34), borderwidth=0, font=fuente(10))
    est.configure("Treeview.Heading", background=paleta.tarjeta_2, foreground=paleta.suave, font=fuente(10, "bold"),
                  relief="flat", padding=(px(8), px(8)))
    est.map("Treeview", background=[("selected", paleta.acento_suave)], foreground=[("selected", paleta.texto)])
    est.configure("TProgressbar", thickness=px(8), troughcolor=paleta.borde, background=paleta.primario, borderwidth=0)
    est.configure("TNotebook", background=paleta.fondo, borderwidth=0)
    est.configure("TNotebook.Tab", padding=(px(14), px(8)), background=paleta.fondo, foreground=paleta.suave)
    est.map("TNotebook.Tab", foreground=[("selected", paleta.primario)], background=[("selected", paleta.fondo)])
    est.configure("Vertical.TScrollbar", background=paleta.borde, troughcolor=paleta.fondo, arrowsize=0, borderwidth=0)
    ventana.option_add("*TCombobox*Listbox.background", paleta.tarjeta)
    ventana.option_add("*TCombobox*Listbox.foreground", paleta.texto)
    ventana.option_add("*TCombobox*Listbox.selectBackground", paleta.acento_suave)
    ventana.option_add("*TCombobox*Listbox.selectForeground", paleta.texto)
    ventana.option_add("*Font", fuente(11))
