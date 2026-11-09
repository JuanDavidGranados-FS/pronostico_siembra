"""Historial: buscar, abrir, renombrar, reutilizar la configuración y comparar dos simulaciones."""
from __future__ import annotations

import tkinter as tk
from tkinter import simpledialog

import ttkbootstrap as ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from src.aplicacion.reutilizacion import configuracion_de_simulacion
from src.infraestructura import graficas as g
from src.presentacion.paginas.comun import encabezado
from src.presentacion.tema import fuente
from src.presentacion.widgets.base import Boton, Pastilla, Tarjeta, etiqueta


class PaginaHistorial(tk.Frame):
    def __init__(self, master, app) -> None:
        super().__init__(master, background=app.p.fondo)
        self.app, p = app, app.p
        encabezado(self, app, "Historial", "Tus simulaciones guardadas. Elige una para abrirla o dos para compararlas.").pack(anchor="w", pady=(8, 14))
        f = tk.Frame(self, background=p.fondo)
        f.pack(fill="x", pady=(0, 10))
        self.v_texto, self.v_desde, self.v_hasta = tk.StringVar(), tk.StringVar(), tk.StringVar()
        etiqueta(f, p, "Buscar", 10, suave=True, fondo=p.fondo).pack(side="left", padx=(0, 6))
        e = ttk.Entry(f, textvariable=self.v_texto, width=24)
        e.pack(side="left", padx=(0, 16))
        e.bind("<KeyRelease>", lambda ev: self.al_mostrar())
        for v, rot in ((self.v_desde, "Desde"), (self.v_hasta, "Hasta")):
            etiqueta(f, p, rot, 10, suave=True, fondo=p.fondo).pack(side="left", padx=(0, 6))
            en = ttk.Entry(f, textvariable=v, width=12)
            en.pack(side="left", padx=(0, 12))
            en.bind("<KeyRelease>", lambda ev: self.al_mostrar())
        from src.presentacion.widgets.base import AyudaBoton
        AyudaBoton(f, p, "Escribe las fechas como AAAA-MM-DD (por ejemplo 2026-11-01).").pack(side="left")
        self.t = ttk.Treeview(self, columns=("n", "e", "f", "k", "p"), show="headings", selectmode="extended", height=12)
        for col, txt, w in (("n", "Nombre", 260), ("e", "Ejecutada", 150), ("f", "Fecha óptima", 110), ("k", "KPI", 70), ("p", "Éxito", 70)):
            self.t.heading(col, text=txt)
            self.t.column(col, width=w, anchor="w")
        self.t.pack(fill="both", expand=True)
        fila = tk.Frame(self, background=p.fondo)
        fila.pack(fill="x", pady=12)
        for txt, fn, var in (("Abrir", self._abrir, "primario"), ("Comparar dos", self._comparar, "secundario"), ("Reutilizar configuración", self._reutilizar, "secundario"),
                             ("Renombrar", self._renombrar, "secundario"), ("Eliminar", self._eliminar, "peligro")):
            Boton(fila, p, txt, fn, var, fondo=p.fondo, tam=10).pack(side="left", padx=(0, 8))
        self.vacio = etiqueta(self, p, "", 11, suave=True, fondo=p.fondo)
        self.vacio.pack(anchor="w")

    def al_mostrar(self) -> None:
        previa = self.t.selection()
        self.t.delete(*self.t.get_children())
        filas = self.app.ctx.historial.listar(texto=self.v_texto.get(), desde=self.v_desde.get().strip(), hasta=self.v_hasta.get().strip())
        for x in filas:
            self.t.insert("", "end", iid=str(x["id"]), values=(x.get("nombre", ""), str(x.get("fecha_ejecucion", ""))[:16].replace("T", " "), x.get("fecha_optima", ""),
                                                              f"{float(x.get('kpi_esperado', 0)):.2f}", f"{float(x.get('probabilidad_exito', 0)):.0f} %"))
        vivas = [i for i in previa if self.t.exists(i)]
        if vivas:
            self.t.selection_set(vivas)
        self.vacio.configure(text="" if filas else "Aún no hay simulaciones guardadas." if not self.v_texto.get() else "Ninguna coincide con tu búsqueda.")

    def _ids(self):
        return [int(i) for i in self.t.selection()]

    def _uno(self):
        ids = self._ids()
        if len(ids) != 1:
            self.app.aviso("Elige una sola simulación de la lista.", "aviso")
            return None
        return ids[0]

    def _abrir(self) -> None:
        i = self._uno()
        if i is None:
            return
        sim = self.app.ctx.historial.obtener(i)
        if sim:
            self.app.resultado = sim["resultado_completo"]
            self.app.id_resultado = i
            self.app.paginas.pop("resultados", None)
            self.app.ir("resultados")

    def _renombrar(self) -> None:
        i = self._uno()
        if i is None:
            return
        n = simpledialog.askstring("Renombrar", "Nuevo nombre:", parent=self)
        if n:
            try:
                self.app.ctx.historial.renombrar(i, n)
                self.al_mostrar()
            except ValueError as exc:
                self.app.aviso(str(exc), "error")

    def _eliminar(self) -> None:
        i = self._uno()
        if i is not None:
            self.app.ctx.historial.eliminar(i)
            self.al_mostrar()
            self.app.aviso("Simulación eliminada.")

    def _reutilizar(self) -> None:
        i = self._uno()
        if i is None:
            return
        datos = configuracion_de_simulacion(self.app.ctx.repo_historial, self.app.ctx.repo_config, i)
        if datos is None:
            self.app.aviso("Esa simulación no tiene configuración guardada.", "aviso")
            return
        self.app.reemplazar_datos(datos)
        self.app.aviso("Configuración cargada. Revísala en Datos o ejecútala de nuevo.")
        self.app.ir("simulacion")

    def _comparar(self) -> None:
        ids = self._ids()
        if len(ids) != 2:
            self.app.aviso("Elige exactamente dos simulaciones para compararlas.", "aviso")
            return
        c = self.app.ctx.historial.comparar_detallado(*ids)
        p = self.app.p
        v = tk.Toplevel(self)
        v.title("Comparación")
        v.configure(background=p.fondo)
        v.geometry("980x720")
        tk.Label(v, text="Comparación", font=fuente(20, "bold"), foreground=p.texto, background=p.fondo).pack(anchor="w", padx=24, pady=(18, 4))
        etiqueta(v, p, c["resumen"], 12, wraplength=900, fondo=p.fondo).pack(anchor="w", padx=24, pady=(0, 12))
        fila = tk.Frame(v, background=p.fondo)
        fila.pack(fill="x", padx=24)
        for k, lado in (("a", "A"), ("b", "B")):
            s = c[k]
            t = Tarjeta(fila, p, 16)
            t.pack(side="left", fill="both", expand=True, padx=(0 if k == "a" else 10, 0))
            if c["mejor"] == k:
                Pastilla(t.cuerpo, p, "Mejor KPI", "ok").pack(anchor="w", pady=(0, 6))
            etiqueta(t.cuerpo, p, s["nombre"], 13, "bold").pack(anchor="w")
            etiqueta(t.cuerpo, p, f"{s['cultivo']} · óptima {s['fecha_optima']}", 10, suave=True).pack(anchor="w", pady=(2, 8))
            etiqueta(t.cuerpo, p, f"KPI {s['kpi']:.2f}   ·   éxito {s['probabilidad_exito'] * 100:.0f} %   ·   {s['p10']:.1f}–{s['p90']:.1f} t/ha", 11).pack(anchor="w")
        for d in c["diferencias"]:
            etiqueta(v, p, "•  " + d, 11, wraplength=900, fondo=p.fondo).pack(anchor="w", padx=24, pady=2)
        fig = Figure(figsize=(8.5, 3.2), dpi=100)
        g.dibujar_comparacion(fig, c["resultado_a"], c["resultado_b"], g.TEMA_OSCURO if p.oscuro else g.TEMA_CLARO)
        lienzo = FigureCanvasTkAgg(fig, master=v)
        lienzo.get_tk_widget().pack(fill="both", expand=True, padx=24, pady=12)
        lienzo.draw()
