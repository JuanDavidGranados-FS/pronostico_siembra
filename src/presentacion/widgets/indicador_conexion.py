"""Semáforo de conexión con un simulador externo: verde, amarillo (más de 5 min sin datos) y rojo (último archivo inválido)."""
from __future__ import annotations

import tkinter as tk
from datetime import datetime
from typing import Callable, Optional

from src.presentacion.tema import Paleta, fuente
from src.presentacion.widgets.base import Tooltip

MINUTOS_VIGENCIA = 5
TEXTOS = {"conectado": "Datos recibidos", "sin_datos": "Sin datos recientes", "error": "Último archivo inválido",
          "espera": "Sin conexión"}


class IndicadorConexion(tk.Frame):
    """Punto de color + texto. Clic: abre el registro de recepciones."""

    def __init__(self, master, p: Paleta, al_clic: Optional[Callable[[], None]] = None, vigencia_min: float = MINUTOS_VIGENCIA) -> None:
        super().__init__(master, background=p.fondo, cursor="hand2")
        self.p, self.vigencia, self.estado, self.marca = p, vigencia_min, "espera", None
        self._punto = tk.Canvas(self, width=14, height=14, highlightthickness=0, background=p.fondo)
        self._punto.pack(side="left")
        self._circulo = self._punto.create_oval(2, 2, 12, 12, outline="")
        self._texto = tk.Label(self, font=fuente(10), foreground=p.suave, background=p.fondo, padx=6)
        self._texto.pack(side="left")
        Tooltip(self, "Estado de la conexión con un simulador o mod externo. Clic para ver el registro.", p)
        if al_clic:
            for w in (self, self._punto, self._texto):
                w.bind("<Button-1>", lambda e: al_clic())
        self.actualizar("espera")
        self.after(30_000, self._vigilar)

    def _color(self) -> str:
        return {"conectado": self.p.ok, "sin_datos": self.p.aviso, "error": self.p.error}.get(self.estado, self.p.suave)

    def actualizar(self, estado: str, marca: Optional[datetime] = None) -> None:
        """Estados: 'conectado', 'sin_datos', 'error' o 'espera' (todavía no ha llegado nada)."""
        self.estado = estado
        if marca is not None:
            self.marca = marca
        self._punto.itemconfigure(self._circulo, fill=self._color())
        hora = f" · {self.marca:%H:%M}" if self.marca else ""
        self._texto.configure(text=TEXTOS[estado] + hora)

    def _vigilar(self) -> None:
        if self.estado == "conectado" and self.marca and (datetime.now() - self.marca).total_seconds() > self.vigencia * 60:
            self.actualizar("sin_datos")
        try:
            self.after(30_000, self._vigilar)
        except tk.TclError:
            pass
