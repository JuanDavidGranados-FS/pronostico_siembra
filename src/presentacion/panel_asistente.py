"""Panel lateral del asistente: respuestas cortas, «Ver más» opcional y sugerencias para seguir preguntando."""
from __future__ import annotations

import tkinter as tk
from typing import Any, Dict, List, Optional

import ttkbootstrap as ttk

from src.aplicacion import asistente
from src.presentacion import tema
from src.presentacion.tema import fuente
from src.presentacion.widgets.base import Boton


class PanelAsistente(tk.Frame):
    """Conversación sencilla sin internet; cada respuesta ofrece ampliar o preguntar otra cosa."""

    def __init__(self, master, app) -> None:
        p = app.p
        super().__init__(master, background=p.tarjeta, width=340, highlightbackground=p.borde, highlightthickness=1)
        self.app, self.p = app, p
        self.pack_propagate(False)
        cab = tk.Frame(self, background=p.tarjeta)
        cab.pack(fill="x", padx=18, pady=(16, 6))
        tk.Label(cab, text="✦ Asistente", font=fuente(13, "bold"), foreground=p.texto, background=p.tarjeta).pack(side="left")
        Boton(cab, p, "✕", app.alternar_asistente, "fantasma", fondo=p.tarjeta, ancho=36, tam=10).pack(side="right")
        tk.Label(self, text="Pregunta lo que quieras: respondo en pocas líneas y, si quieres, amplío.",
                 font=fuente(10), foreground=p.suave, background=p.tarjeta, wraplength=tema.ancho_texto(300, 80), justify="left").pack(anchor="w", padx=18)
        self.chat = tk.Text(self, wrap="word", relief="flat", background=p.tarjeta, foreground=p.texto, font=fuente(11),
                            padx=18, pady=10, state="disabled", cursor="arrow", highlightthickness=0, spacing3=6)
        self.chat.tag_configure("yo", foreground=p.primario, font=fuente(11, "bold"))
        self.chat.tag_configure("tema", foreground=p.suave, font=fuente(9, "bold"))
        self.chat.pack(fill="both", expand=True)
        self.sugs = tk.Frame(self, background=p.tarjeta)
        self.sugs.pack(fill="x", padx=14)
        fila = tk.Frame(self, background=p.tarjeta)
        fila.pack(fill="x", padx=14, pady=14)
        self.var = tk.StringVar()
        self.entrada = ttk.Entry(fila, textvariable=self.var)
        self.entrada.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entrada.bind("<Return>", lambda e: self.enviar())
        Boton(fila, p, "Enviar", self.enviar, "primario", fondo=p.tarjeta, ancho=76).pack(side="right")
        self._ultimo: Optional[Dict[str, Any]] = None
        self._sugerir(asistente.SUGERENCIAS_INICIALES)

    def enviar(self) -> None:
        t = self.var.get().strip()
        if t:
            self.var.set("")
            self.preguntar(t)

    def preguntar(self, texto: str) -> None:
        r = asistente.responder(texto, self.app.contexto_asistente())
        self._ultimo = r
        self._escribir(texto, r)
        self._sugerir(r["sugerencias"], r.get("mas"))

    def _escribir(self, pregunta: str, r: Dict[str, Any]) -> None:
        c = self.chat
        c.configure(state="normal")
        c.insert("end", pregunta + "\n", "yo")
        if r.get("tema"):
            c.insert("end", r["tema"].upper() + "\n", "tema")
        c.insert("end", r["respuesta"] + "\n\n")
        c.configure(state="disabled")
        c.see("end")

    def _sugerir(self, sugerencias: List[str], mas: Optional[str] = None) -> None:
        for w in self.sugs.winfo_children():
            w.destroy()
        if mas:
            Boton(self.sugs, self.p, "Ver más detalle", lambda: self._ver_mas(mas), "primario", fondo=self.p.tarjeta, tam=10).pack(anchor="w", pady=3)
        for s in sugerencias[:3]:
            Boton(self.sugs, self.p, s, lambda s=s: self.preguntar(s), "secundario", fondo=self.p.tarjeta, tam=10).pack(anchor="w", pady=3)

    def _ver_mas(self, texto: str) -> None:
        c = self.chat
        c.configure(state="normal")
        c.insert("end", texto + "\n\n")
        c.configure(state="disabled")
        c.see("end")
        self._sugerir((self._ultimo or {}).get("sugerencias", []))
