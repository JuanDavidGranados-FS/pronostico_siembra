"""Ayuda: recorrido, glosario, preguntas frecuentes y guía de integración, una a la vez."""
from __future__ import annotations

import os
import re
import tkinter as tk

import ttkbootstrap as ttk

from src.aplicacion import asistente
from src.presentacion.paginas.comun import encabezado
from src.presentacion.tema import fuente
from src.presentacion.widgets.base import Boton, PaginaScroll, Segmentado, Tarjeta, etiqueta

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
GUIA = os.path.join(RAIZ, "docs", "integration_guide.md")


class PaginaAyuda(tk.Frame):
    def __init__(self, master, app) -> None:
        super().__init__(master, background=app.p.fondo)
        self.app, p = app, app.p
        encabezado(self, app, "Ayuda", "Elige qué quieres consultar. También puedes preguntar al asistente en cualquier momento.").pack(anchor="w", pady=(8, 14))
        self.seg = Segmentado(self, p, [("recorrido", "Recorrido"), ("glosario", "Glosario"), ("faq", "Preguntas frecuentes"), ("integracion", "Guía de integración")], self.abrir)
        self.seg.pack(anchor="w", pady=(0, 14))
        self.zona = tk.Frame(self, background=p.fondo)
        self.zona.pack(fill="both", expand=True)
        self.abrir("recorrido", sincronizar=False)

    def abrir(self, clave: str, sincronizar: bool = True) -> None:
        if sincronizar:
            self.seg.elegir(clave, notificar=False)
        for w in self.zona.winfo_children():
            w.destroy()
        getattr(self, "_" + clave)()

    def _recorrido(self) -> None:
        p = self.app.p
        t = Tarjeta(self.zona, p, 22)
        t.pack(fill="x")
        etiqueta(t.cuerpo, p, "Recorrido guiado", 14, "bold").pack(anchor="w")
        etiqueta(t.cuerpo, p, "Un minuto para ver los pasos: datos, relevancia, simulación y resultados.", 11, suave=True).pack(anchor="w", pady=8)
        Boton(t.cuerpo, p, "Iniciar recorrido", self.app.reiniciar_tour, "primario", fondo=p.tarjeta).pack(anchor="w")

    def _glosario(self) -> None:
        p = self.app.p
        busca = tk.StringVar()
        e = ttk.Entry(self.zona, textvariable=busca, width=32)
        e.pack(anchor="w", pady=(0, 10))
        sc = PaginaScroll(self.zona, p)
        sc.pack(fill="both", expand=True)

        def pintar(*_):
            for w in sc.interior.winfo_children():
                w.destroy()
            q = busca.get().lower()
            for term, defin in asistente.glosario():
                if q and q not in term.lower() and q not in defin.lower():
                    continue
                t = Tarjeta(sc.interior, p, 14)
                t.pack(fill="x", pady=4)
                etiqueta(t.cuerpo, p, term, 12, "bold").pack(anchor="w")
                etiqueta(t.cuerpo, p, defin, 10, wraplength=640, suave=True).pack(anchor="w", pady=(2, 0))
        busca.trace_add("write", pintar)
        pintar()

    def _faq(self) -> None:
        p = self.app.p
        sc = PaginaScroll(self.zona, p)
        sc.pack(fill="both", expand=True)
        from src.presentacion.widgets.base import Seccion
        for q, a in asistente.PREGUNTAS_FRECUENTES:
            s = Seccion(sc.interior, p, q)
            s.pack(fill="x", pady=4)
            etiqueta(s.cuerpo, p, a, 11, wraplength=640).pack(anchor="w")

    def _integracion(self) -> None:
        p = self.app.p
        t = tk.Text(self.zona, wrap="word", relief="flat", background=p.tarjeta, foreground=p.texto, font=fuente(11), padx=22, pady=18,
                    highlightbackground=p.borde, highlightthickness=1, spacing3=4)
        t.tag_configure("h1", font=fuente(18, "bold"), spacing3=10)
        t.tag_configure("h2", font=fuente(14, "bold"), spacing1=12, spacing3=6)
        t.tag_configure("code", font=("DejaVu Sans Mono", 10), background=p.tarjeta_2)
        try:
            with open(GUIA, encoding="utf-8") as f:
                lineas = f.read().splitlines()
        except OSError:
            lineas = ["# Guía de integración", "No se encontró docs/integration_guide.md."]
        code = False
        for ln in lineas:
            if ln.startswith("```"):
                code = not code
                continue
            if code:
                t.insert("end", ln + "\n", "code")
            elif ln.startswith("# "):
                t.insert("end", ln[2:] + "\n", "h1")
            elif ln.startswith("## "):
                t.insert("end", ln[3:] + "\n", "h2")
            else:
                t.insert("end", re.sub(r"[*`]", "", ln) + "\n")
        t.configure(state="disabled")
        t.pack(fill="both", expand=True)
