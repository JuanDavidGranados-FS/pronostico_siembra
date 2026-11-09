"""Componentes visuales reutilizables: botones redondeados, tarjetas, pastillas, ayuda contextual, acordeón y scroll."""
from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from typing import Callable, Dict, List, Optional

import ttkbootstrap as ttk

from src.presentacion.tema import Paleta, fuente


def _rect_redondeado(c: tk.Canvas, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r,
           x1, y1 + r, x1, y1]
    return c.create_polygon(pts, smooth=True, **kw)


class Boton(tk.Canvas):
    """Botón redondeado. variante: primario | secundario | fantasma | peligro."""

    def __init__(self, master, p: Paleta, texto: str, comando: Optional[Callable] = None, variante: str = "secundario",
                 fondo: Optional[str] = None, ancho: Optional[int] = None, tam: int = 11, **kw) -> None:
        self.p, self.texto, self.comando, self.variante = p, texto, comando, variante
        self._f = fuente(tam, "bold" if variante == "primario" else "normal")
        w = ancho or tkfont.Font(font=self._f).measure(texto) + 36
        super().__init__(master, width=w, height=38 if tam >= 11 else 32, highlightthickness=0, bd=0, cursor="hand2",
                         background=fondo or master.cget("background") if "background" in master.keys() else p.fondo, **kw)
        self._ancho, self._alto = w, 38 if tam >= 11 else 32
        self._activo, self._sobre = True, False
        self.bind("<Enter>", lambda e: self._estado(sobre=True))
        self.bind("<Leave>", lambda e: self._estado(sobre=False))
        self.bind("<Button-1>", self._clic)
        self.bind("<Return>", self._clic)
        self.bind("<space>", self._clic)
        self.bind("<FocusIn>", lambda e: self._dibujar())
        self.bind("<FocusOut>", lambda e: self._dibujar())
        self.configure(takefocus=1)
        self._dibujar()

    def _colores(self):
        p, v = self.p, self.variante
        if not self._activo:
            return p.borde, p.suave, p.borde
        if v == "primario":
            return (p.primario_h if self._sobre else p.primario), p.sobre_primario, (p.primario_h if self._sobre else p.primario)
        if v == "peligro":
            return (p.error if self._sobre else p.tarjeta), (p.sobre_primario if self._sobre else p.error), p.error
        if v == "fantasma":
            return (p.acento_suave if self._sobre else self.cget("background")), p.primario, self.cget("background")
        return (p.acento_suave if self._sobre else p.tarjeta), p.texto, p.borde

    def _dibujar(self) -> None:
        self.delete("all")
        fondo, texto, borde = self._colores()
        _rect_redondeado(self, 1, 1, self._ancho - 1, self._alto - 1, 12, fill=borde, outline=borde)
        _rect_redondeado(self, 2, 2, self._ancho - 2, self._alto - 2, 11, fill=fondo, outline=fondo)
        if self.focus_get() is self:
            _rect_redondeado(self, 0, 0, self._ancho, self._alto, 13, fill="", outline=self.p.primario, width=2)
        self.create_text(self._ancho / 2, self._alto / 2, text=self.texto, fill=texto, font=self._f)

    def _estado(self, sobre: bool) -> None:
        self._sobre = sobre and self._activo
        self._dibujar()

    def _clic(self, _e=None) -> None:
        if self._activo and self.comando:
            self.comando()

    def activar(self, activo: bool) -> None:
        """Habilita o deshabilita el botón."""
        self._activo = activo
        self.configure(cursor="hand2" if activo else "arrow")
        self._dibujar()

    def poner_texto(self, texto: str) -> None:
        """Cambia el texto (ancho fijo)."""
        self.texto = texto
        self._dibujar()


class Tarjeta(tk.Frame):
    """Superficie con borde fino y relleno; contiene `.cuerpo`."""

    def __init__(self, master, p: Paleta, relleno: int = 20, **kw) -> None:
        super().__init__(master, background=p.tarjeta, highlightbackground=p.borde, highlightcolor=p.borde,
                         highlightthickness=1, **kw)
        self.p = p
        self.cuerpo = tk.Frame(self, background=p.tarjeta)
        self.cuerpo.pack(fill="both", expand=True, padx=relleno, pady=relleno)


class Pastilla(tk.Label):
    """Etiqueta redondeada de estado: tono ok | aviso | error | info | neutro."""

    def __init__(self, master, p: Paleta, texto: str, tono: str = "neutro", **kw) -> None:
        colores = {"ok": (p.ok, p.sobre_primario), "aviso": (p.aviso, "#1b1300"), "error": (p.error, "#ffffff"),
                   "info": (p.info, "#ffffff"), "neutro": (p.acento_suave, p.texto)}
        bg, fg = colores[tono]
        super().__init__(master, text=texto, background=bg, foreground=fg, font=fuente(9, "bold"), padx=10, pady=3, **kw)


class Tooltip:
    """Globo de ayuda que aparece al pasar el ratón o al enfocar."""

    def __init__(self, widget, texto: str, p: Paleta) -> None:
        self.widget, self.texto, self.p, self.ventana = widget, texto, p, None
        widget.bind("<Enter>", self._mostrar, add="+")
        widget.bind("<FocusIn>", self._mostrar, add="+")
        widget.bind("<Leave>", self._ocultar, add="+")
        widget.bind("<FocusOut>", self._ocultar, add="+")
        widget.bind("<Destroy>", self._ocultar, add="+")

    def _mostrar(self, _e=None) -> None:
        if self.ventana or not self.texto:
            return
        x, y = self.widget.winfo_rootx() + 12, self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.ventana = v = tk.Toplevel(self.widget)
        v.wm_overrideredirect(True)
        v.wm_geometry(f"+{x}+{y}")
        tk.Label(v, text=self.texto, justify="left", wraplength=300, background=self.p.texto, foreground=self.p.fondo,
                 font=fuente(10), padx=12, pady=8).pack()

    def _ocultar(self, _e=None) -> None:
        if self.ventana:
            self.ventana.destroy()
            self.ventana = None


class AyudaBoton(tk.Label):
    """Círculo «?» con globo de ayuda; si se pulsa, llama a `al_preguntar` para ampliar con el asistente."""

    def __init__(self, master, p: Paleta, texto: str, al_preguntar: Optional[Callable[[], None]] = None, fondo: Optional[str] = None) -> None:
        super().__init__(master, text="?", font=fuente(9, "bold"), foreground=p.primario, background=p.acento_suave,
                         width=2, cursor="question_arrow", takefocus=1)
        self.configure(padx=0, pady=0)
        Tooltip(self, texto, p)
        if al_preguntar:
            self.bind("<Button-1>", lambda e: al_preguntar())
            self.bind("<Return>", lambda e: al_preguntar())


class PaginaScroll(tk.Frame):
    """Zona desplazable vertical; los hijos se ponen en `.interior`."""

    def __init__(self, master, p: Paleta, **kw) -> None:
        super().__init__(master, background=p.fondo, **kw)
        self.canvas = tk.Canvas(self, background=p.fondo, highlightthickness=0, bd=0)
        self.barra = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.barra.set)
        self.interior = tk.Frame(self.canvas, background=p.fondo)
        self._id = self.canvas.create_window((0, 0), window=self.interior, anchor="nw")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.barra.pack(side="right", fill="y")
        self.interior.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._id, width=e.width))
        for w in (self.canvas, self.interior):
            w.bind("<Enter>", self._enlazar_rueda)
            w.bind("<Leave>", self._soltar_rueda)

    def _enlazar_rueda(self, _e=None) -> None:
        self.canvas.bind_all("<MouseWheel>", self._rueda)
        self.canvas.bind_all("<Button-4>", lambda e: self.canvas.yview_scroll(-2, "units"))
        self.canvas.bind_all("<Button-5>", lambda e: self.canvas.yview_scroll(2, "units"))

    def _soltar_rueda(self, _e=None) -> None:
        for s in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.canvas.unbind_all(s)

    def _rueda(self, e) -> None:
        self.canvas.yview_scroll(int(-e.delta / 60) or (-1 if e.delta > 0 else 1), "units")


class Seccion(tk.Frame):
    """Sección desplegable. Solo se muestra el encabezado y un resumen hasta que el usuario la abre."""

    def __init__(self, master, p: Paleta, titulo: str, resumen: str = "", ayuda: str = "",
                 al_abrir: Optional[Callable[["Seccion"], None]] = None, al_preguntar: Optional[Callable[[], None]] = None) -> None:
        super().__init__(master, background=p.tarjeta, highlightbackground=p.borde, highlightthickness=1)
        self.p, self.abierta, self.al_abrir = p, False, al_abrir
        self.cab = tk.Frame(self, background=p.tarjeta, cursor="hand2")
        self.cab.pack(fill="x", padx=18, pady=14)
        self.flecha = tk.Label(self.cab, text="›", font=fuente(16, "bold"), foreground=p.suave, background=p.tarjeta)
        self.flecha.pack(side="left", padx=(0, 10))
        tk.Label(self.cab, text=titulo, font=fuente(12, "bold"), foreground=p.texto, background=p.tarjeta,
                 cursor="hand2").pack(side="left")
        if ayuda:
            AyudaBoton(self.cab, p, ayuda, al_preguntar).pack(side="left", padx=8)
        self.resumen = tk.Label(self.cab, text=resumen, font=fuente(10), foreground=p.suave, background=p.tarjeta)
        self.resumen.pack(side="right")
        self.cuerpo = tk.Frame(self, background=p.tarjeta)
        for w in (self.cab, *self.cab.winfo_children()):
            if not isinstance(w, AyudaBoton):
                w.bind("<Button-1>", lambda e: self.alternar())

    def poner_resumen(self, texto: str) -> None:
        self.resumen.configure(text=texto)

    def alternar(self) -> None:
        self.cerrar() if self.abierta else self.abrir()

    def abrir(self) -> None:
        if self.abierta:
            return
        if self.al_abrir:
            self.al_abrir(self)
        self.abierta = True
        self.flecha.configure(text="⌄")
        self.cuerpo.pack(fill="x", padx=18, pady=(0, 18))

    def cerrar(self) -> None:
        self.abierta = False
        self.flecha.configure(text="›")
        self.cuerpo.pack_forget()


class GrupoAcordeon:
    """Mantiene una sola sección abierta a la vez (así la pantalla nunca se llena de información)."""

    def __init__(self) -> None:
        self.secciones: List[Seccion] = []

    def crear(self, master, p: Paleta, titulo: str, **kw) -> Seccion:
        s = Seccion(master, p, titulo, al_abrir=self._cerrar_otras, **kw)
        self.secciones.append(s)
        return s

    def _cerrar_otras(self, actual: Seccion) -> None:
        for s in self.secciones:
            if s is not actual:
                s.cerrar()


class Segmentado(tk.Frame):
    """Selector de pestañas tipo «píldora»: llama a `al_cambiar(clave)`."""

    def __init__(self, master, p: Paleta, opciones: List[tuple], al_cambiar: Callable[[str], None], inicial: Optional[str] = None) -> None:
        super().__init__(master, background=p.tarjeta_2, highlightbackground=p.borde, highlightthickness=1)
        self.p, self.al_cambiar, self.botones, self.clave = p, al_cambiar, {}, None
        for clave, texto in opciones:
            b = tk.Label(self, text=texto, font=fuente(10, "bold"), padx=14, pady=6, cursor="hand2", takefocus=1)
            b.pack(side="left", padx=3, pady=3)
            b.bind("<Button-1>", lambda e, c=clave: self.elegir(c))
            b.bind("<Return>", lambda e, c=clave: self.elegir(c))
            self.botones[clave] = b
        self.elegir(inicial or opciones[0][0], notificar=False)

    def elegir(self, clave: str, notificar: bool = True) -> None:
        self.clave = clave
        for c, b in self.botones.items():
            sel = c == clave
            b.configure(background=self.p.tarjeta if sel else self.p.tarjeta_2,
                        foreground=self.p.primario if sel else self.p.suave)
        if notificar:
            self.al_cambiar(clave)


class Metrica(tk.Frame):
    """Número grande con su rótulo y una frase corta debajo."""

    def __init__(self, master, p: Paleta, rotulo: str, valor: str, nota: str = "", ayuda: str = "") -> None:
        super().__init__(master, background=p.tarjeta)
        fila = tk.Frame(self, background=p.tarjeta)
        fila.pack(anchor="w")
        tk.Label(fila, text=rotulo, font=fuente(10), foreground=p.suave, background=p.tarjeta).pack(side="left")
        if ayuda:
            AyudaBoton(fila, p, ayuda).pack(side="left", padx=6)
        self.valor = tk.Label(self, text=valor, font=fuente(24, "bold"), foreground=p.texto, background=p.tarjeta)
        self.valor.pack(anchor="w", pady=(2, 0))
        self.nota = tk.Label(self, text=nota, font=fuente(10), foreground=p.suave, background=p.tarjeta,
                             wraplength=170, justify="left")
        self.nota.pack(anchor="w")


class Deslizador(tk.Frame):
    """Control 0–100 con etiqueta, valor y «?»: el slider del Factor de Relevancia."""

    def __init__(self, master, p: Paleta, rotulo: str, valor: float, ayuda: str = "", al_cambiar: Optional[Callable] = None,
                 desde: float = 0, hasta: float = 100) -> None:
        super().__init__(master, background=p.tarjeta)
        self.var = tk.DoubleVar(value=valor)
        self._cb = al_cambiar
        fila = tk.Frame(self, background=p.tarjeta)
        fila.pack(fill="x")
        tk.Label(fila, text=rotulo, font=fuente(11), foreground=p.texto, background=p.tarjeta).pack(side="left")
        if ayuda:
            AyudaBoton(fila, p, ayuda).pack(side="left", padx=8)
        self.etiqueta = tk.Label(fila, text=f"{valor:.0f}", font=fuente(11, "bold"), foreground=p.primario,
                                 background=p.tarjeta, width=4, anchor="e")
        self.etiqueta.pack(side="right")
        ttk.Scale(self, from_=desde, to=hasta, variable=self.var, command=self._mover, style="TScale").pack(fill="x", pady=(4, 0))

    def _mover(self, _v=None) -> None:
        self.etiqueta.configure(text=f"{self.var.get():.0f}")
        if self._cb:
            self._cb()

    def poner(self, v: float) -> None:
        self.var.set(v)
        self._mover()

    def obtener(self) -> float:
        return round(float(self.var.get()), 1)


def etiqueta(master, p: Paleta, texto: str, tam: int = 11, peso: str = "normal", suave: bool = False, **kw) -> tk.Label:
    """Etiqueta con el color de tarjeta, tipografía y ajuste de línea de la interfaz."""
    kw.setdefault("anchor", "w")
    kw.setdefault("justify", "left")
    return tk.Label(master, text=texto, font=fuente(tam, peso), foreground=p.suave if suave else p.texto,
                    background=kw.pop("fondo", p.tarjeta), **kw)
