"""Resultados: primero la recomendación en una frase; el resto se ve solo si el usuario lo pide."""
from __future__ import annotations

import tkinter as tk
from datetime import date
from tkinter import filedialog

import ttkbootstrap as ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from src.aplicacion.explicador import fecha_larga
from src.infraestructura import exportador, graficas as g
from src.presentacion.paginas.comun import encabezado
from src.presentacion import tema
from src.presentacion.tema import fuente
from src.presentacion.widgets.base import Boton, Metrica, PaginaScroll, Pastilla, Segmentado, Tarjeta, etiqueta


class PaginaResultados(tk.Frame):
    def __init__(self, master, app) -> None:
        super().__init__(master, background=app.p.fondo)
        self.app, p = app, app.p
        self.r = app.resultado
        if not self.r:
            encabezado(self, app, "Resultados", "Aún no hay resultados.").pack(anchor="w", pady=(8, 12))
            etiqueta(self, p, "Ejecuta una simulación y aquí verás la fecha recomendada.", 12, suave=True, fondo=p.fondo).pack(anchor="w")
            Boton(self, p, "Ir a Simulación", lambda: app.ir("simulacion"), "primario", fondo=p.fondo).pack(anchor="w", pady=16)
            return
        r = self.r
        sc = PaginaScroll(self, p)
        sc.pack(fill="both", expand=True)
        cont = sc.interior
        fo, est = r["fecha_optima"], r["estadisticas_rendimiento"]
        f = date.fromisoformat(fo["fecha"])
        encabezado(cont, app, r.get("nombre") or "Resultados", f"{r.get('cultivo', '')}").pack(anchor="w", pady=(8, 14))
        # Recomendación
        t = Tarjeta(cont, p, 26)
        t.pack(fill="x", pady=(0, 14))
        cab = tk.Frame(t.cuerpo, background=p.tarjeta)
        cab.pack(fill="x")
        Pastilla(cab, p, "Recomendado" if fo["viable"] else "No viable", "ok" if fo["viable"] else "error").pack(side="left")
        if fo["viable"]:
            tk.Label(t.cuerpo, text=fecha_larga(f), font=fuente(26, "bold"), foreground=p.primario, background=p.tarjeta).pack(anchor="w", pady=(10, 4))
        else:
            tk.Label(t.cuerpo, text="No encontré una fecha segura", font=fuente(22, "bold"), foreground=p.error, background=p.tarjeta).pack(anchor="w", pady=(10, 4))
        etiqueta(t.cuerpo, p, r.get("justificacion", ""), 12, wraplength=640).pack(anchor="w", pady=(4, 12))
        fila = tk.Frame(t.cuerpo, background=p.tarjeta)
        fila.pack(anchor="w")
        self.btn_detalle = Boton(fila, p, "¿Por qué esta fecha?", self._alternar_detalle, "secundario", fondo=p.tarjeta)
        self.btn_detalle.pack(side="left")
        Boton(fila, p, "Preguntar al asistente", lambda: app.preguntar("¿Por qué esta fecha?"), "fantasma", fondo=p.tarjeta).pack(side="left", padx=8)
        self.detalle = tk.Frame(t.cuerpo, background=p.tarjeta)
        self._detalle_visible = False
        for d in r.get("justificacion_detalle", []):
            etiqueta(self.detalle, p, "•  " + d, 11, wraplength=620).pack(anchor="w", pady=3)
        # Tres números
        fila = tk.Frame(cont, background=p.fondo)
        fila.pack(fill="x", pady=(0, 14))
        datos = [("KPI", f"{r['kpi']['valor']:.2f}", "Puntaje de esta fecha (más alto es mejor).", "El KPI combina rendimiento, relevancia y esfuerzo."),
                 ("Probabilidad de éxito", f"{fo['probabilidad_exito'] * 100:.0f} %", "De los escenarios simulados, los que llegan a buena cosecha.", "Se considera éxito llegar al menos al 40 % del rendimiento base."),
                 ("Cosecha esperada", f"{est['p10']:.1f}–{est['p90']:.1f}", "toneladas por hectárea (8 de cada 10 casos).", "Va del percentil 10 al 90.")]
        for i, (rot, val, nota, ay) in enumerate(datos):
            c = Tarjeta(fila, p, 18)
            c.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 7, 7 if i < 2 else 0))
            fila.columnconfigure(i, weight=1, uniform="m")
            Metrica(c.cuerpo, p, rot, val, nota, ay).pack(anchor="w")
        # Vistas bajo demanda
        vistas = [("graficas", "Gráficas"), ("comparacion", "Comparación"), ("riesgos", "Riesgos")]
        if r.get("plan_temporadas"):
            vistas.append(("temporadas", "Temporadas"))
        vistas.append(("exportar", "Exportar"))
        etiqueta(cont, p, "¿Quieres ver más?", 12, "bold", fondo=p.fondo).pack(anchor="w", pady=(6, 8))
        self.seg = Segmentado(cont, p, vistas, self._vista)
        self.seg.pack(anchor="w")
        for b in self.seg.botones.values():
            b.configure(background=p.tarjeta_2, foreground=p.suave)
        self.seg.clave = None
        self.zona = tk.Frame(cont, background=p.fondo)
        self.zona.pack(fill="x", pady=12)
        self.fig = None

    def _alternar_detalle(self) -> None:
        if self._detalle_visible:
            self.detalle.pack_forget()
        else:
            self.detalle.pack(anchor="w", pady=(12, 0))
        self._detalle_visible = not self._detalle_visible

    def _vista(self, clave: str) -> None:
        for w in self.zona.winfo_children():
            w.destroy()
        getattr(self, "_v_" + clave)()

    def _card(self) -> tk.Frame:
        c = Tarjeta(self.zona, self.app.p, 20)
        c.pack(fill="x")
        return c.cuerpo

    def _v_graficas(self) -> None:
        p, r = self.app.p, self.r
        c = self._card()
        opciones = [(n, n) for n, d in g.GRAFICAS if d is not g.dibujar_poblacion or r.get("plan_temporadas")]
        self.fig = tema.figura(8, 4.2)
        lienzo = tema.lienzo(self.fig, c)
        paleta = {n: d for n, d in g.GRAFICAS}

        def dibujar(nombre: str) -> None:
            paleta[nombre](self.fig, r, g.TEMA_OSCURO if p.oscuro else g.TEMA_CLARO)
            lienzo.draw()
        Segmentado(c, p, opciones, dibujar).pack(anchor="w", pady=(0, 10))
        lienzo.get_tk_widget().pack(fill="x")
        lienzo.get_tk_widget().configure(background=p.tarjeta, highlightthickness=0)
        dibujar(opciones[0][0])

    def _v_comparacion(self) -> None:
        p, c = self.app.p, self._card()
        etiqueta(c, p, "¿Cuánto mejor es esta fecha que otras opciones?", 12, "bold").pack(anchor="w", pady=(0, 10))
        for x in self.r.get("comparaciones", []):
            f = tk.Frame(c, background=p.tarjeta)
            f.pack(fill="x", pady=6)
            etiqueta(f, p, x["etiqueta"], 11, "bold", width=22).pack(side="left")
            etiqueta(f, p, fecha_larga(date.fromisoformat(x["fecha"])), 11, width=24).pack(side="left")
            etiqueta(f, p, f"KPI {x['kpi']:.2f} · éxito {x['probabilidad_exito'] * 100:.0f} %", 10, suave=True).pack(side="left")
            if x.get("ventaja_pct") is not None:
                Pastilla(f, p, f"la óptima es {x['ventaja_pct']:.0f} % mejor", "ok" if x["ventaja_pct"] >= 0 else "aviso").pack(side="right")

    def _v_riesgos(self) -> None:
        p, c = self.app.p, self._card()
        etiqueta(c, p, "Riesgos identificados", 12, "bold").pack(anchor="w")
        etiqueta(c, p, "Probabilidad de que ocurra cada evento raro durante el ciclo del cultivo.", 10, suave=True).pack(anchor="w", pady=(0, 10))
        for x in self.r.get("riesgos", []):
            pr = x["probabilidades"]
            f = tk.Frame(c, background=p.tarjeta)
            f.pack(fill="x", pady=7)
            etiqueta(f, p, x["etiqueta"], 11, "bold", width=18).pack(side="left")
            etiqueta(f, p, f"Ninguno {pr['0'] * 100:.0f} % · 1 vez {pr['1'] * 100:.0f} % · 2 veces {pr['2'] * 100:.0f} % · 3 o más {pr['3+'] * 100:.0f} %", 10, suave=True).pack(side="left")
            per = x["perdida_esperada"] * 100
            Pastilla(f, p, f"pérdida esperada {per:.0f} %", "error" if per >= 15 else "aviso" if per >= 5 else "ok").pack(side="right")
        Boton(c, p, "¿Qué es Poisson?", lambda: self.app.preguntar("¿Qué es la distribución de Poisson?"), "fantasma", fondo=p.tarjeta, tam=10).pack(anchor="w", pady=(10, 0))

    def _v_temporadas(self) -> None:
        p, c, plan = self.app.p, self._card(), self.r["plan_temporadas"]
        riesgo = plan.get("riesgo_extincion")
        Pastilla(c, p, "Riesgo de extinción" if riesgo else "Se sostiene", "error" if riesgo else "ok").pack(anchor="w")
        etiqueta(c, p, plan["recomendacion"], 11, wraplength=640).pack(anchor="w", pady=10)
        if plan.get("aviso_largo_plazo"):
            etiqueta(c, p, "Más de 10 temporadas: las proyecciones son menos confiables.", 10, suave=True).pack(anchor="w", pady=(0, 8))
        t = ttk.Treeview(c, columns=("t", "f", "n", "c", "s"), show="headings", height=min(10, len(plan["filas"])))
        for col, txt, w in (("t", "Temporada", 90), ("f", "Siembra", 110), ("n", "Plantas", 90), ("c", "Cosecha (t/ha)", 120), ("s", "Semillas a guardar", 140)):
            t.heading(col, text=txt)
            t.column(col, width=w, anchor="w")
        for fl in plan["filas"]:
            t.insert("", "end", values=(fl["temporada"], fl["fecha_siembra"], f"{fl['poblacion_esperada']:.0f}", f"{fl['cosecha_estimada']:.2f}", fl["semillas_guardar"]))
        t.pack(fill="x")

    def _v_exportar(self) -> None:
        p, c = self.app.p, self._card()
        etiqueta(c, p, "Guarda tus resultados", 12, "bold").pack(anchor="w", pady=(0, 10))
        fila = tk.Frame(c, background=p.tarjeta)
        fila.pack(anchor="w")
        for ext, nombre in exportador.FORMATOS.items():
            Boton(fila, p, nombre.split(" (")[0], lambda e=ext: self.exportar(e), "secundario", fondo=p.tarjeta).pack(side="left", padx=(0, 8))

    def exportar(self, ext: str, ruta: str = "") -> None:
        ruta = ruta or filedialog.asksaveasfilename(defaultextension=ext, filetypes=[(exportador.FORMATOS[ext], "*" + ext)],
                                                    initialfile=f"pronostico_siembra{ext}")
        if not ruta:
            return
        try:
            exportador.exportar(ruta, self.r)
            self.app.aviso("Archivo guardado.")
        except Exception as exc:
            self.app.aviso(f"No se pudo exportar: {exc}", "error")
