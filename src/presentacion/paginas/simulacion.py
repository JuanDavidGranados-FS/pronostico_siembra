"""Simulación: resumen de lo elegido, un botón grande y, escondidos, los ajustes avanzados."""
from __future__ import annotations

import tkinter as tk

import ttkbootstrap as ttk

from src.presentacion import tema
from src.presentacion.paginas.comun import encabezado, numero
from src.presentacion.widgets.base import Boton, GrupoAcordeon, PaginaScroll, Tarjeta, etiqueta


class PaginaSimulacion(tk.Frame):
    def __init__(self, master, app) -> None:
        super().__init__(master, background=app.p.fondo)
        self.app, p = app, app.p
        sc = PaginaScroll(self, p)
        sc.pack(fill="both", expand=True)
        cont = sc.interior
        encabezado(cont, app, "Simulación", "Todo listo cuando quieras. Tarda unos segundos.").pack(anchor="w", pady=(8, 16))
        self.tarjeta = Tarjeta(cont, p)
        self.tarjeta.pack(fill="x", pady=(0, 14))
        self.resumen = etiqueta(self.tarjeta.cuerpo, p, "", 12, wraplength=720)
        self.resumen.pack(anchor="w")
        fila = tk.Frame(self.tarjeta.cuerpo, background=p.tarjeta)
        fila.pack(fill="x", pady=(16, 0))
        self.boton = Boton(fila, p, "Ejecutar simulación", app.ejecutar, "primario", fondo=p.tarjeta, ancho=220)
        self.boton.pack(side="left")
        self.barra = ttk.Progressbar(fila, mode="determinate", length=260)
        self.estado = etiqueta(fila, p, "", 10, suave=True)
        grupo = GrupoAcordeon()
        self.s = grupo.crear(cont, p, "Ajustes avanzados", resumen="Opcional",
                             ayuda="Cuántos escenarios simular, la ventana de fechas y el nombre de esta simulación.",
                             al_preguntar=lambda: app.preguntar("¿Qué es Montecarlo?"))
        self.s.pack(fill="x")
        c = self.s.cuerpo
        self.vars = {}
        campos = [("nombre", "Nombre (opcional)", "Para encontrarla luego en el Historial.", "¿Qué es el historial?"),
                  ("iteraciones", "Escenarios a simular", "Más escenarios dan resultados más estables, pero tardan más.", "¿Qué es Montecarlo?"),
                  ("semilla", "Semilla aleatoria (opcional)", "Con la misma semilla obtienes el mismo resultado.", "¿Qué es la semilla aleatoria?"),
                  ("ventana_dias", "Ventana de fechas (días)", "Cuántos días explorar desde la fecha inicial.", "¿Qué es la ventana y el paso?"),
                  ("paso_dias", "Paso entre fechas (días)", "Cada cuántos días se prueba una fecha.", "¿Qué es la ventana y el paso?"),
                  ("esfuerzo", "Esfuerzo o costo relativo", "0 o más. Más esfuerzo baja el KPI.", "¿Qué es el esfuerzo?")]
        from src.presentacion.widgets.base import AyudaBoton
        for i, (k, rot, ayuda, preg) in enumerate(campos):
            f = tk.Frame(c, background=p.tarjeta)
            f.grid(row=i, column=0, sticky="ew", pady=5)
            if tema.MOVIL:  # celular: rótulo arriba, campo y «?» debajo
                etiqueta(f, p, rot, 11).pack(anchor="w")
                f = tk.Frame(f, background=p.tarjeta)
                f.pack(anchor="w", pady=(2, 0))
            else:
                etiqueta(f, p, rot, 11, width=26).pack(side="left")
            v = tk.StringVar()
            self.vars[k] = v
            ttk.Entry(f, textvariable=v, width=18).pack(side="left")
            AyudaBoton(f, p, ayuda, lambda q=preg: app.preguntar(q)).pack(side="left", padx=8)
        self.refrescar()

    def refrescar(self) -> None:
        d = self.app.datos
        for k, v in self.vars.items():
            val = getattr(d, k)
            v.set("" if val in (None, "") else (f"{val:g}" if isinstance(val, float) else str(val)))
        self._resumen()

    def _resumen(self) -> None:
        d = self.app.datos
        plan = int(d.plan.get("temporadas", 1))
        self.resumen.configure(text=f"Cultivo: {d.cultivo.nombre}  ·  Siembra desde: {d.deterministas['fecha']}  ·  "
                                    f"Temporadas: {plan}  ·  Relevancia: {self.app.pesos_origen}")

    def al_mostrar(self) -> None:
        self.app.volcar()
        self._resumen()

    def volcar(self):
        d, errs = self.app.datos, []
        for k, v in self.vars.items():
            t = v.get().strip()
            if k == "nombre":
                d.nombre = t
            elif k == "semilla":
                d.semilla = int(numero(t)) if numero(t) is not None else None
            else:
                n = numero(t)
                if n is None:
                    errs.append(f"«{k}» debe ser un número.")
                else:
                    setattr(d, k, int(n) if k in ("iteraciones", "ventana_dias", "paso_dias") else float(n))
        return errs

    def al_iniciar(self) -> None:
        self.boton.activar(False)
        self.barra.configure(value=0)
        self.barra.pack(side="left", padx=16)
        self.estado.pack(side="left")
        self.estado.configure(text="Empezando…")

    def al_progreso(self, i: int, n: int) -> None:
        self.barra.configure(value=i / n * 100)
        self.estado.configure(text=f"Probando fecha {i} de {n}")

    def al_terminar(self) -> None:
        self.boton.activar(True)
        self.barra.pack_forget()
        self.estado.pack_forget()
