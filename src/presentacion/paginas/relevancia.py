"""Relevancia: deslizadores siempre a la vista; los métodos de cálculo y los perfiles, uno a la vez."""
from __future__ import annotations

import json
import tkinter as tk
from tkinter import filedialog
from typing import Any, Dict

import ttkbootstrap as ttk

from src.aplicacion.asistente import FUENTE_DEFECTO
from src.dominio.entidades import PESOS_POR_DEFECTO
from src.dominio.metodos_relevancia import ETIQUETAS, VARIABLES
from src.infraestructura.lector_historico import leer_historico
from src.presentacion.paginas.comun import encabezado
from src.presentacion.widgets.base import Boton, Deslizador, GrupoAcordeon, PaginaScroll, Segmentado, Tarjeta, etiqueta

AYUDAS = {"agua": "Cuánto te importa que el agua sea la adecuada.", "temperatura": "Cuánto te importa la temperatura.",
          "humedad": "Cuánto te importa la humedad del aire.", "ph": "Cuánto te importa la acidez del suelo.",
          "nutrientes": "Cuánto te importan nitrógeno, fósforo y potasio. Pon 0 si tu simulador no los usa."}
METODOS = [("manual", "Sugeridos"), ("minimo", "Ley del Mínimo"), ("historico", "Mi histórico"), ("experto", "Modo experto"), ("campo", "Diario de campo")]
ESCALA = [("a es mucho más importante", 9.0), ("a es más importante", 5.0), ("a es algo más importante", 3.0), ("Igual", 1.0),
          ("b es algo más importante", 1 / 3), ("b es más importante", 1 / 5), ("b es mucho más importante", 1 / 9)]


class PaginaRelevancia(tk.Frame):
    def __init__(self, master, app) -> None:
        super().__init__(master, background=app.p.fondo)
        self.app, p = app, app.p
        sc = PaginaScroll(self, p)
        sc.pack(fill="both", expand=True)
        cont = sc.interior
        encabezado(cont, app, "¿Qué te importa más?", "Cuánto pesa cada variable en tu caso, de 0 (se ignora) a 100 (máxima importancia).").pack(anchor="w", pady=(8, 14))
        t = Tarjeta(cont, p, 22)
        t.pack(fill="x", pady=(0, 12))
        self.sl: Dict[str, Deslizador] = {}
        for v in VARIABLES:
            s = Deslizador(t.cuerpo, p, ETIQUETAS[v], app.datos.pesos.get(v, PESOS_POR_DEFECTO.get(v, 50)), AYUDAS[v], self._cambio)
            s.pack(fill="x", pady=7)
            self.sl[v] = s
        self.origen = etiqueta(t.cuerpo, p, "", 10, suave=True)
        self.origen.pack(anchor="w", pady=(8, 0))
        self._cambio(solo_texto=True)
        grupo = GrupoAcordeon()
        self.s_met = grupo.crear(cont, p, "Calcularlo automáticamente", resumen="Opcional", ayuda="Ley del Mínimo, tu histórico, comparaciones de experto o tu diario de campo.",
                                 al_preguntar=lambda: app.preguntar("¿Qué es la Ley del Mínimo?"))
        self.s_met.pack(fill="x", pady=5)
        self.s_perf = grupo.crear(cont, p, "Mis configuraciones guardadas", resumen="", ayuda="Guarda, carga, duplica y comparte tus pesos.",
                                  al_preguntar=lambda: app.preguntar("¿Cómo comparto mi configuración de relevancia?"))
        self.s_perf.pack(fill="x", pady=5)
        self.seg = Segmentado(self.s_met.cuerpo, p, METODOS, self._metodo)
        self.seg.pack(anchor="w", pady=(0, 12))
        self.panel = tk.Frame(self.s_met.cuerpo, background=p.tarjeta)
        self.panel.pack(fill="x")
        self._metodo("manual")
        self._perfiles()
        fila = tk.Frame(cont, background=p.fondo)
        fila.pack(fill="x", pady=16)
        Boton(fila, p, "Continuar → Simulación", lambda: app.ir("simulacion"), "primario", fondo=p.fondo, ancho=220).pack(side="left")

    # ------------------------------------------------------------ pesos
    def _cambio(self, solo_texto: bool = False) -> None:
        if not solo_texto:
            self.app.pesos_origen = "Ajuste manual"
        self.origen.configure(text=f"Origen: {self.app.pesos_origen}")

    def _poner(self, pesos: Dict[str, float], origen: str) -> None:
        for v, s in self.sl.items():
            if v in pesos:
                s.poner(float(pesos[v]))
        self.app.pesos_origen = origen
        self._cambio(solo_texto=True)
        self.volcar()

    def volcar(self):
        self.app.datos.pesos = {**self.app.datos.pesos, **{v: s.obtener() for v, s in self.sl.items()}}
        return []

    def refrescar(self) -> None:
        for v, s in self.sl.items():
            s.poner(self.app.datos.pesos.get(v, 50))

    # ---------------------------------------------------------- métodos
    def _limpiar(self) -> tk.Frame:
        for w in self.panel.winfo_children():
            w.destroy()
        return self.panel

    def _metodo(self, clave: str) -> None:
        p, c = self.app.p, self._limpiar()
        getattr(self, "_m_" + clave)(c, p)

    def _m_manual(self, c, p) -> None:
        etiqueta(c, p, "Mueve los deslizadores a tu gusto. Los valores iniciales son sugerencias para agricultura real.", 11, wraplength=640).pack(anchor="w")
        etiqueta(c, p, FUENTE_DEFECTO, 9, suave=True, wraplength=640).pack(anchor="w", pady=8)
        Boton(c, p, "Restaurar valores sugeridos", lambda: self._poner(dict(PESOS_POR_DEFECTO), "Valores sugeridos"), "secundario", fondo=p.tarjeta).pack(anchor="w")

    def _resultado(self, c, p, res: Dict[str, Any], origen: str) -> None:
        for v, txt in (res.get("justificaciones") or {}).items():
            etiqueta(c, p, f"•  {txt}", 10, wraplength=640).pack(anchor="w", pady=2)
        if res.get("resumen_consistencia"):
            etiqueta(c, p, res["resumen_consistencia"], 10, "bold", wraplength=640).pack(anchor="w", pady=6)
        Boton(c, p, "Usar estos pesos", lambda: self._poner(res["pesos"], origen), "primario", fondo=p.tarjeta).pack(anchor="w", pady=8)

    def _m_minimo(self, c, p) -> None:
        etiqueta(c, p, "Calcula la relevancia sola: lo que está más lejos de su valor ideal pesa más.", 11, wraplength=640).pack(anchor="w", pady=(0, 8))
        self.app.volcar()
        pesos, textos = self.app.ctx.relevancia.ley_del_minimo(self.app.datos)
        self._resultado(c, p, {"pesos": pesos, "justificaciones": textos}, "Ley del Mínimo")

    def _m_historico(self, c, p) -> None:
        etiqueta(c, p, "Sube un CSV o Excel con tus temporadas pasadas (columna «rendimiento», al menos 10 filas).", 11, wraplength=640).pack(anchor="w", pady=(0, 8))
        Boton(c, p, "Elegir archivo…", lambda: self._leer(c, p), "secundario", fondo=p.tarjeta).pack(anchor="w")
        self.zona_h = tk.Frame(c, background=p.tarjeta)
        self.zona_h.pack(fill="x", pady=8)

    def _leer(self, c, p) -> None:
        ruta = filedialog.askopenfilename(filetypes=[("Histórico", "*.csv *.xlsx *.xlsm")])
        if not ruta:
            return
        for w in self.zona_h.winfo_children():
            w.destroy()
        try:
            res = self.app.ctx.relevancia.desde_historico(leer_historico(ruta))
        except Exception as exc:
            etiqueta(self.zona_h, p, f"No pude leer el archivo: {exc}", 10, wraplength=640).pack(anchor="w")
            return
        if not res.get("valido"):
            etiqueta(self.zona_h, p, res.get("motivo", "El archivo no sirve."), 10, wraplength=640).pack(anchor="w")
            return
        self._resultado(self.zona_h, p, res, "Mi histórico (Spearman)")

    def _m_experto(self, c, p) -> None:
        etiqueta(c, p, "Compara las variables de dos en dos. Si dudas, deja «Igual».", 11, wraplength=640).pack(anchor="w", pady=(0, 8))
        self.cmp: Dict = {}
        for a, b in self.app.ctx.relevancia.pares_experto():
            f = tk.Frame(c, background=p.tarjeta)
            f.pack(fill="x", pady=3)
            etiqueta(f, p, f"{ETIQUETAS[a]} (a) frente a {ETIQUETAS[b]} (b)", 10, width=34).pack(side="left")
            v = tk.StringVar(value="Igual")
            ttk.Combobox(f, textvariable=v, values=[e[0] for e in ESCALA], state="readonly", width=26).pack(side="left")
            self.cmp[(a, b)] = v
        self.zona_e = tk.Frame(c, background=p.tarjeta)
        Boton(c, p, "Calcular", lambda: self._calc_experto(p), "secundario", fondo=p.tarjeta).pack(anchor="w", pady=8)
        self.zona_e.pack(fill="x")

    def _calc_experto(self, p) -> None:
        for w in self.zona_e.winfo_children():
            w.destroy()
        esc = dict(ESCALA)
        res = self.app.ctx.relevancia.desde_experto({k: esc[v.get()] for k, v in self.cmp.items()})
        if not res["consistente"]:
            a = " y ".join(f"{ETIQUETAS[x]}-{ETIQUETAS[y]}" for x, y in res["parejas_a_revisar"])
            res["resumen_consistencia"] += f" Revisa: {a}."
        self._resultado(self.zona_e, p, res, "Modo experto (AHP)")

    def _m_campo(self, c, p) -> None:
        g = self.app.ctx.relevancia
        etiqueta(c, p, "Prueba una variable a la vez en tu terreno y anota lo que pase. Con 5 registros calculo tu relevancia.", 11, wraplength=640).pack(anchor="w", pady=(0, 8))
        f = tk.Frame(c, background=p.tarjeta)
        f.pack(fill="x", pady=4)
        self.v_var = tk.StringVar(value="agua")
        cb = ttk.Combobox(f, textvariable=self.v_var, values=list(VARIABLES), state="readonly", width=14)
        cb.pack(side="left")
        self.l_exp = etiqueta(c, p, g.experimento("agua"), 10, suave=True, wraplength=640)
        cb.bind("<<ComboboxSelected>>", lambda e: self.l_exp.configure(text=g.experimento(self.v_var.get())))
        self.l_exp.pack(anchor="w", pady=4)
        r = tk.Frame(c, background=p.tarjeta)
        r.pack(fill="x", pady=6)
        self.rv = {k: tk.StringVar() for k in ("temporada", "valor", "rendimiento")}
        for k, rot, w in (("temporada", "Temporada", 10), ("valor", "Valor de la variable", 10), ("rendimiento", "Rendimiento", 10)):
            etiqueta(r, p, rot, 10, suave=True).pack(side="left", padx=(0, 4))
            ttk.Entry(r, textvariable=self.rv[k], width=w).pack(side="left", padx=(0, 12))
        Boton(r, p, "Anotar", self._anotar, "secundario", fondo=p.tarjeta, tam=10).pack(side="left")
        self.l_n = etiqueta(c, p, "", 10, suave=True)
        self.l_n.pack(anchor="w", pady=4)
        self.zona_c = tk.Frame(c, background=p.tarjeta)
        Boton(c, p, "Calcular con mis registros", lambda: self._calc_campo(p), "primario", fondo=p.tarjeta).pack(anchor="w", pady=6)
        self.zona_c.pack(fill="x")
        self._n_registros()

    def _n_registros(self) -> None:
        self.l_n.configure(text=f"Registros guardados: {len(self.app.ctx.relevancia.registros())}")

    def _anotar(self) -> None:
        try:
            self.app.ctx.relevancia.agregar_registro(self.rv["temporada"].get(), self.v_var.get(), self.rv["valor"].get(), self.rv["rendimiento"].get())
            for v in self.rv.values():
                v.set("")
            self._n_registros()
        except ValueError as exc:
            self.app.aviso(str(exc), "error")

    def _calc_campo(self, p) -> None:
        for w in self.zona_c.winfo_children():
            w.destroy()
        res = self.app.ctx.relevancia.desde_campo(self.app.datos)
        if res.get("motivo"):
            etiqueta(self.zona_c, p, res["motivo"], 10, wraplength=640).pack(anchor="w")
        self._resultado(self.zona_c, p, res, "Ley del Mínimo (pocos registros)" if res.get("usa_ley_minimo") else "Mi diario de campo")

    # ---------------------------------------------------------- perfiles
    def _perfiles(self) -> None:
        p, c, g = self.app.p, self.s_perf.cuerpo, self.app.ctx.relevancia
        self.v_nombre = tk.StringVar()
        f = tk.Frame(c, background=p.tarjeta)
        f.pack(fill="x", pady=(0, 10))
        etiqueta(f, p, "Nombre", 11, width=10).pack(side="left")
        ttk.Entry(f, textvariable=self.v_nombre, width=28).pack(side="left")
        Boton(f, p, "Guardar", self._guardar, "primario", fondo=p.tarjeta, tam=10).pack(side="left", padx=10)
        self.lista = ttk.Treeview(c, columns=("n", "m"), show="headings", height=4, selectmode="browse")
        self.lista.heading("n", text="Configuración")
        self.lista.heading("m", text="Método")
        self.lista.column("n", width=300)
        self.lista.column("m", width=140)
        self.lista.pack(fill="x")
        fila = tk.Frame(c, background=p.tarjeta)
        fila.pack(fill="x", pady=10)
        for txt, fn in (("Cargar", self._cargar), ("Duplicar", self._duplicar), ("Eliminar", self._eliminar),
                        ("Descargar", self._exportar), ("Importar", self._importar)):
            Boton(fila, p, txt, fn, "secundario", fondo=p.tarjeta, tam=10).pack(side="left", padx=(0, 8))
        self._listar()

    def _listar(self) -> None:
        self.lista.delete(*self.lista.get_children())
        cfg = self.app.ctx.relevancia.listar()
        for x in cfg:
            self.lista.insert("", "end", iid=str(x["id"]), values=(x["nombre"], x.get("metodo", "")))
        self.s_perf.poner_resumen(f"{len(cfg)} guardada{'s' if len(cfg) != 1 else ''}")

    def _sel(self):
        s = self.lista.selection()
        if not s:
            self.app.aviso("Elige una configuración de la lista.", "aviso")
            return None
        return int(s[0])

    def _guardar(self) -> None:
        self.volcar()
        try:
            self.app.ctx.relevancia.guardar(self.v_nombre.get(), self.app.datos.pesos, "manual")
            self._listar()
            self.app.aviso("Configuración guardada.")
        except ValueError as exc:
            self.app.aviso(str(exc), "error")

    def _cargar(self) -> None:
        i = self._sel()
        if i is not None:
            try:
                c = self.app.ctx.relevancia.cargar(i)
                self._poner(c["pesos"], f"Guardada: {c['nombre']}")
            except ValueError as exc:
                self.app.aviso(str(exc), "error")

    def _duplicar(self) -> None:
        i = self._sel()
        if i is not None:
            self.app.ctx.relevancia.duplicar(i)
            self._listar()

    def _eliminar(self) -> None:
        i = self._sel()
        if i is not None:
            self.app.ctx.relevancia.eliminar(i)
            self._listar()

    def _exportar(self) -> None:
        i = self._sel()
        ruta = i is not None and filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")], initialfile="relevancia.json")
        if ruta:
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(self.app.ctx.relevancia.exportar(i), f, ensure_ascii=False, indent=2)
            self.app.aviso("Configuración descargada.")

    def _importar(self) -> None:
        ruta = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not ruta:
            return
        try:
            with open(ruta, encoding="utf-8") as f:
                self.app.ctx.relevancia.importar(json.load(f))
            self._listar()
            self.app.aviso("Configuración importada.")
        except (ValueError, OSError) as exc:
            self.app.aviso(f"No se pudo importar: {exc}", "error")
