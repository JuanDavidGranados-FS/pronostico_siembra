"""Reacomodo automático para pantallas angostas (celular).

Las páginas están diseñadas para escritorio: filas con varios elementos lado a lado, rejillas de dos o tres
columnas y textos con ancho fijo. En el celular, en vez de reescribir cada página, este módulo recorre los
widgets visibles y, solo donde algo NO cabe a lo ancho:

* parte las filas (`pack(side="left"/"right")`) en varias líneas, como texto que salta de renglón;
* pasa las rejillas (`grid`) de varias columnas a una sola columna;
* ajusta el `wraplength` de las etiquetas al ancho disponible;
* encoge las columnas de las tablas (`Treeview`) para que quepan.

Un widget puede excluirse poniéndole el atributo `_sin_reflujo = True` (p. ej. la matriz de Márkov, que es una
tabla y se lee mejor arrastrándola de lado).
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk as tkttk
from typing import List, Tuple

from src.presentacion import tema
from src.presentacion.tema import px

_LADOS = {"left", "right"}


def _num(v) -> int:
    try:
        return int(float(str(v)))
    except (TypeError, ValueError):
        return 0


def _pad(v) -> int:
    """Suma de un padx/pady de pack/grid (puede venir como 8, '8', (0, 8) o '0 8')."""
    if isinstance(v, (tuple, list)):
        return sum(_num(x) for x in v)
    return sum(_num(x) for x in str(v).split()) if isinstance(v, str) and " " in v else _num(v) * 2


class _Referencia:
    """Zona visible contra la que se mide si algo cabe: x de su borde izquierdo y ancho."""

    def __init__(self, x: int, ancho: int) -> None:
        self.x, self.ancho = x, ancho

    def disponible(self, w) -> Tuple[int, int]:
        """(posición x del widget dentro de la zona, ancho que le queda hasta el borde derecho con margen)."""
        x = max(0, w.winfo_rootx() - self.x)
        margen = min(x, px(24))  # suponemos un margen derecho parecido al izquierdo (tarjetas, secciones)
        return x, self.ancho - x - margen


def _arbol(raiz, ref: _Referencia, profundidad: int, salida: List) -> None:
    """Lista (profundidad, widget, referencia) de todo lo visible, cambiando de referencia dentro de cada PaginaScroll."""
    from src.presentacion.widgets.base import PaginaScroll
    for w in raiz.winfo_children():
        if isinstance(w, tk.Toplevel) or not w.winfo_ismapped():
            continue
        r = ref
        if isinstance(w, PaginaScroll):
            r = _Referencia(w.canvas.winfo_rootx(), w.canvas.winfo_width())
        salida.append((profundidad, w, r))
        _arbol(w, r, profundidad + 1, salida)


def _no_cabe(w, ref: _Referencia) -> bool:
    x, disp = ref.disponible(w)
    return w.winfo_reqwidth() > disp + px(2)


# ---------------------------------------------------------------- filas lado a lado
def _es_fila(w) -> bool:
    from src.presentacion.widgets.base import PaginaScroll
    if not isinstance(w, tk.Frame) or isinstance(w, PaginaScroll):
        return False
    if getattr(w, "_sin_reflujo", False) or getattr(w, "_partida", False):
        return False
    hijos = w.pack_slaves()
    return len(hijos) >= 2 and all(h.pack_info().get("side") in _LADOS for h in hijos)


def _partir_fila(f, ref: _Referencia) -> None:
    """Reparte los hijos de una fila en renglones que quepan en el ancho disponible."""
    _, disp = ref.disponible(f)
    hijos = f.pack_slaves()
    infos = [h.pack_info() for h in hijos]
    for h in hijos:
        h.pack_forget()
    fondo = f.cget("background")
    renglon, usado = None, 0
    for h, info in zip(hijos, infos):
        ancho = h.winfo_reqwidth() + _pad(info.get("padx", 0))
        if renglon is None or (usado > 0 and usado + ancho > disp):
            renglon = tk.Frame(f, background=fondo)
            renglon.pack(side="top", anchor="w", fill="x", pady=(0, px(4)))
            usado = 0
        h.pack(in_=renglon, side="left", padx=info.get("padx", 0), pady=info.get("pady", 0),
               ipadx=info.get("ipadx", 0), ipady=info.get("ipady", 0), anchor=info.get("anchor", "center"),
               fill="y" if info.get("fill") in ("y", "both") else "none")
        h.tk.call("raise", h._w, renglon._w)  # que el hijo quede por encima del renglón (si no, no se ve)
        usado += ancho
    f._partida = True


# ---------------------------------------------------------------- rejillas
def _es_rejilla(w) -> bool:
    if not isinstance(w, tk.Frame) or getattr(w, "_sin_reflujo", False) or getattr(w, "_una_columna", False):
        return False
    hijos = w.grid_slaves()
    return len({_num(h.grid_info().get("column")) for h in hijos}) > 1


def _una_columna(g) -> None:
    hijos = sorted(g.grid_slaves(), key=lambda h: (_num(h.grid_info()["row"]), _num(h.grid_info()["column"])))
    columnas = {_num(h.grid_info()["column"]) for h in hijos}
    for i, h in enumerate(hijos):
        info = h.grid_info()
        pegado = info.get("sticky", "") or "w"
        h.grid_configure(row=i, column=0, columnspan=1, rowspan=1, sticky=pegado, padx=(0, 0))
    for c in columnas:
        g.grid_columnconfigure(c, weight=1 if c == 0 else 0, uniform="", minsize=0)
    g._una_columna = True


# ---------------------------------------------------------------- textos y tablas
def _ajustar_texto(lbl, ref: _Referencia) -> bool:
    x, disp = ref.disponible(lbl)
    disp = max(px(120), disp)
    actual = _num(lbl.cget("wraplength"))
    if actual <= 0 and lbl.winfo_reqwidth() <= disp + px(2):
        return False
    if abs(actual - disp) <= px(3):
        return False
    lbl.configure(wraplength=disp, justify="left")
    return True


def _ajustar_tabla(t, ref: _Referencia) -> bool:
    cols = list(t["columns"])
    if not cols:
        return False
    if not getattr(t, "_escalada", False):  # primero, a la escala del celular
        for c in cols:
            t.column(c, width=px(_num(t.column(c, "width"))))
        t._escalada = True
    _, disp = ref.disponible(t)
    total = sum(_num(t.column(c, "width")) for c in cols)
    if total <= disp or total <= 0:
        return False
    k = disp / total
    for c in cols:
        t.column(c, width=max(px(40), int(_num(t.column(c, "width")) * k)), minwidth=px(30))
    return True


# ---------------------------------------------------------------- recorrido
def reacomodar(raiz, ref_x: int, ref_ancho: int) -> bool:
    """Reacomoda lo que no cabe dentro de `raiz`. Devuelve True si cambió algo."""
    if not tema.MOVIL:
        return False
    cambio = False
    for _ronda in range(2):
        raiz.update_idletasks()
        ref = _Referencia(ref_x, ref_ancho)
        items: List = [(0, raiz, ref)]
        _arbol(raiz, ref, 1, items)
        # 1) rejillas de varias columnas que no caben → una columna (de afuera hacia adentro)
        for _, w, r in items:
            try:
                if _es_rejilla(w) and _no_cabe(w, r):
                    _una_columna(w)
                    cambio = True
                    raiz.update_idletasks()
            except tk.TclError:
                pass
        if cambio:
            items = [(0, raiz, ref)]
            _arbol(raiz, ref, 1, items)
        # 2) filas lado a lado que no caben → renglones (de los más profundos a los de afuera:
        #    así cada nivel ya conoce el tamaño final de sus hijos)
        for prof in sorted({p for p, _, _ in items}, reverse=True):
            tocado = False
            for w, r in [(w, r) for p, w, r in items if p == prof]:
                try:
                    if _es_fila(w) and _no_cabe(w, r):
                        _partir_fila(w, r)
                        tocado = True
                except tk.TclError:
                    pass
            if tocado:
                cambio = True
                raiz.update_idletasks()
        # 3) textos y tablas, ya con las posiciones finales
        raiz.update_idletasks()
        items = [(0, raiz, ref)]
        _arbol(raiz, ref, 1, items)
        ronda_cambio = False
        for _, w, r in items:
            try:
                if isinstance(w, tk.Label) and not isinstance(w, tk.Canvas) and w.cget("text"):
                    ronda_cambio |= _ajustar_texto(w, r)
                elif isinstance(w, tkttk.Treeview):
                    ronda_cambio |= _ajustar_tabla(w, r)
            except tk.TclError:
                pass
        cambio |= ronda_cambio
        if not ronda_cambio:
            break
    return cambio
