"""Recorrido guiado: una tarjeta flotante que lleva al usuario por las pantallas, un paso a la vez."""
from __future__ import annotations

import tkinter as tk

from src.presentacion.tema import fuente
from src.presentacion.widgets.base import Boton

PASOS = [
    ("inicio", "Bienvenido", "Esta aplicación te dice cuándo sembrar. Aquí empiezas y ves si todo está listo."),
    ("datos", "1. Tus datos", "Elige el cultivo y revisa el suelo y el clima. Ya traen valores sugeridos: puedes cambiarlos o no."),
    ("relevancia", "2. Qué te importa", "Con los deslizadores dices cuánto pesa cada variable. Puedes dejar que el programa lo calcule."),
    ("simulacion", "3. Simular", "Pulsa «Ejecutar simulación». Tarda unos segundos y no necesitas internet."),
    ("resultados", "4. Resultados", "Ves la fecha recomendada y por qué. Puedes pedir más detalle y exportar un informe."),
    ("ayuda", "¿Dudas?", "En cualquier momento pulsa «✦ Preguntar» o el «?» junto a un término. Puedes repetir este recorrido desde Ayuda."),
]


class Tour:
    def __init__(self, app) -> None:
        self.app, self.i, self.v = app, 0, None

    def iniciar(self) -> None:
        self.i = 0
        self._paso()

    def _paso(self) -> None:
        a, p = self.app, self.app.p
        if self.v is not None:
            self.v.destroy()
        pagina, titulo, texto = PASOS[self.i]
        a.ir(pagina)
        self.v = v = tk.Frame(a, background=p.tarjeta, highlightbackground=p.primario, highlightthickness=2)
        v.place(relx=1.0, rely=1.0, anchor="se", x=-32, y=-32)
        tk.Label(v, text=f"Paso {self.i + 1} de {len(PASOS)}", font=fuente(9, "bold"), foreground=p.primario, background=p.tarjeta).pack(anchor="w", padx=18, pady=(16, 0))
        tk.Label(v, text=titulo, font=fuente(14, "bold"), foreground=p.texto, background=p.tarjeta).pack(anchor="w", padx=18)
        tk.Label(v, text=texto, font=fuente(11), foreground=p.texto, background=p.tarjeta, wraplength=300, justify="left").pack(anchor="w", padx=18, pady=8)
        fila = tk.Frame(v, background=p.tarjeta)
        fila.pack(fill="x", padx=14, pady=(0, 14))
        Boton(fila, p, "Saltar", self.cerrar, "fantasma", fondo=p.tarjeta, ancho=70).pack(side="left")
        ultimo = self.i == len(PASOS) - 1
        Boton(fila, p, "Terminar" if ultimo else "Siguiente", self._siguiente, "primario", fondo=p.tarjeta).pack(side="right")
        v.lift()

    def _siguiente(self) -> None:
        if self.i == len(PASOS) - 1:
            self.cerrar()
        else:
            self.i += 1
            self._paso()

    def cerrar(self) -> None:
        if self.v is not None:
            self.v.destroy()
            self.v = None
        self.app.ctx.preferencias.guardar("tour_visto", True)
        self.app.ir("inicio")
