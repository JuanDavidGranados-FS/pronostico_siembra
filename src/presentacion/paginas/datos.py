"""Datos: cultivo, suelo, clima, estado de la planta (Márkov), eventos raros y plan de temporadas, por secciones."""
from __future__ import annotations

import tkinter as tk
from datetime import date
from typing import Dict, List

import ttkbootstrap as ttk

from src.dominio import matrices as mx
from src.dominio.entidades import Cultivo
from src.presentacion.paginas.comun import encabezado, numero
from src.presentacion.tema import fuente
from src.presentacion.widgets.base import AyudaBoton, Boton, GrupoAcordeon, PaginaScroll, Pastilla, etiqueta

PARAMS = {"normal": [("media", "Media"), ("std", "Desviación")], "uniforme": [("min", "Mínimo"), ("max", "Máximo")],
          "triangular": [("min", "Mínimo"), ("moda", "Más probable"), ("max", "Máximo")]}
VARS_CLIMA = {"temperatura": "Temperatura (°C)", "lluvia": "Lluvia (mm/día)", "humedad": "Humedad (%)"}
CADENAS = {"salud": "Salud de la planta", "enfermedad": "Enfermedad", "crecimiento": "Crecimiento"}


class PaginaDatos(tk.Frame):
    def __init__(self, master, app) -> None:
        super().__init__(master, background=app.p.fondo)
        self.app, p = app, app.p
        sc = PaginaScroll(self, p)
        sc.pack(fill="both", expand=True)
        cont = sc.interior
        encabezado(cont, app, "Tus datos", "Abre cada sección solo si quieres cambiar algo: ya traen valores sugeridos.").pack(anchor="w", pady=(8, 16))
        self.grupo = GrupoAcordeon()
        self.vars: Dict[str, tk.StringVar] = {}
        self.sec = {}
        defs = [("cultivo", "Cultivo", "Qué vas a sembrar y qué necesita.", "¿Qué es el rango de cosecha?"),
                ("suelo", "Suelo y manejo", "pH, nutrientes (N, P, K), resistencia y riego.", "¿Qué es el pH del suelo?"),
                ("clima", "Clima", "Cuánto puede variar la temperatura, la lluvia y la humedad.", "¿Qué son las distribuciones?"),
                ("estado", "Estado de la planta", "Probabilidades de pasar de un estado a otro cada semana (cadena de Márkov).", "¿Qué es una cadena de Márkov?"),
                ("eventos", "Eventos raros", "Plagas, heladas y lluvias intensas que ocurren pocas veces.", "¿Qué es la distribución de Poisson?"),
                ("plan", "Plan de temporadas", "Cuántas temporadas planear seguidas.", "¿Qué es Galton-Watson?")]
        for k, tit, ayuda, preg in defs:
            s = self.grupo.crear(cont, p, tit, ayuda=ayuda, al_preguntar=lambda q=preg: app.preguntar(q))
            s.pack(fill="x", pady=5)
            self.sec[k] = s
        self._cultivo()
        self._suelo()
        self._clima()
        self._estado()
        self._eventos()
        self._plan()
        fila = tk.Frame(cont, background=p.fondo)
        fila.pack(fill="x", pady=18)
        Boton(fila, p, "Continuar → Relevancia", lambda: app.ir("relevancia"), "primario", fondo=p.fondo, ancho=220).pack(side="left")
        self._resumenes()

    # -------------------------------------------------------------- helpers
    def _var(self, clave: str, valor) -> tk.StringVar:
        v = tk.StringVar(value="" if valor is None else (f"{valor:g}" if isinstance(valor, float) else str(valor)))
        self.vars[clave] = v
        return v

    def _fila(self, c, rot: str, clave: str, valor, ayuda: str = "", ancho: int = 14, fila: int = 0, col: int = 0) -> None:
        p = self.app.p
        f = tk.Frame(c, background=p.tarjeta)
        f.grid(row=fila, column=col, sticky="w", padx=(0, 28), pady=5)
        etiqueta(f, p, rot, 11, width=18).pack(side="left")
        ttk.Entry(f, textvariable=self._var(clave, valor), width=ancho).pack(side="left")
        if ayuda:
            AyudaBoton(f, p, ayuda).pack(side="left", padx=8)

    # -------------------------------------------------------------- secciones
    def _cultivo(self) -> None:
        p, d, c = self.app.p, self.app.datos, self.sec["cultivo"].cuerpo
        cultivos = self.app.ctx.orquestador.listar_cultivos()
        self.cultivos = {x.nombre: x for x in cultivos}
        f = tk.Frame(c, background=p.tarjeta)
        f.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        etiqueta(f, p, "Cultivo", 11, width=18).pack(side="left")
        self.var_cultivo = tk.StringVar(value=d.cultivo.nombre)
        cb = ttk.Combobox(f, textvariable=self.var_cultivo, values=list(self.cultivos) or [d.cultivo.nombre], state="readonly", width=22)
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda e: self._elegir_cultivo())
        c2 = tk.Frame(c, background=p.tarjeta)
        c2.grid(row=1, column=0, columnspan=2, sticky="w")
        self.c_cult = c2
        self._campos_cultivo()

    def _campos_cultivo(self) -> None:
        for w in self.c_cult.winfo_children():
            w.destroy()
        cu = self.app.datos.cultivo
        campos = [("dias_crecimiento", "Días de crecimiento", cu.dias_crecimiento, ""), ("temp_min", "Temperatura mínima (°C)", cu.temp_min, "Por debajo, la planta sufre."),
                  ("temp_max", "Temperatura máxima (°C)", cu.temp_max, "Por encima, la planta sufre."), ("requerimiento_agua", "Agua que pide (mm/día)", cu.requerimiento_agua, ""),
                  ("resistencia_plagas", "Resistencia a plagas (0–100)", cu.resistencia_plagas, "Qué tan bien aguanta plagas y enfermedades."),
                  ("rendimiento_base", "Rendimiento base (t/ha)", cu.rendimiento_base, "Cosecha ideal en condiciones perfectas.")]
        for i, (k, rot, v, ay) in enumerate(campos):
            self._fila(self.c_cult, rot, "c_" + k, v, ay, fila=i // 2, col=i % 2)

    def _elegir_cultivo(self) -> None:
        c = self.cultivos.get(self.var_cultivo.get())
        if c:
            self.app.datos.cultivo = c
            self._campos_cultivo()
            self._resumenes()

    def _suelo(self) -> None:
        d, c = self.app.datos.deterministas, self.sec["suelo"].cuerpo
        campos = [("fecha", "Fecha inicial (AAAA-MM-DD)", d["fecha"], "Desde qué día se exploran fechas de siembra."), ("ph", "pH del suelo", d["ph"], "0 a 14; ideal cerca de 6,5."),
                  ("nitrogeno", "Nitrógeno (kg/ha)", d["nitrogeno"], ""), ("fosforo", "Fósforo (kg/ha)", d["fosforo"], ""), ("potasio", "Potasio (kg/ha)", d["potasio"], ""),
                  ("resistencia", "Resistencia de la semilla (0–100)", d["resistencia"], ""), ("agua", "Riego (mm/día)", d["agua"], "Agua que tú aportas, además de la lluvia.")]
        for i, (k, rot, v, ay) in enumerate(campos):
            self._fila(c, rot, "d_" + k, v, ay, fila=i // 2, col=i % 2)

    def _clima(self) -> None:
        p, c = self.app.p, self.sec["clima"].cuerpo
        self.clima_vars: Dict[str, tk.StringVar] = {}
        self.clima_param_frames: Dict[str, tk.Frame] = {}
        for i, (k, rot) in enumerate(VARS_CLIMA.items()):
            e = self.app.datos.estocasticos[k]
            caja = tk.Frame(c, background=p.tarjeta_2, highlightbackground=p.borde, highlightthickness=1)
            caja.pack(fill="x", pady=6)
            interior = tk.Frame(caja, background=p.tarjeta_2)
            interior.pack(fill="x", padx=14, pady=12)
            etiqueta(interior, p, rot, 12, "bold", fondo=p.tarjeta_2).pack(anchor="w")
            fila = tk.Frame(interior, background=p.tarjeta_2)
            fila.pack(fill="x", pady=6)
            etiqueta(fila, p, "Cómo varía", 11, fondo=p.tarjeta_2, width=14).pack(side="left")
            v = tk.StringVar(value=e["tipo"])
            self.clima_vars[k] = v
            cb = ttk.Combobox(fila, textvariable=v, values=list(PARAMS), state="readonly", width=12)
            cb.pack(side="left")
            cb.bind("<<ComboboxSelected>>", lambda ev, k=k: self._params_clima(k))
            AyudaBoton(fila, p, "Normal: media y desviación. Uniforme: entre un mínimo y un máximo. Triangular: mínimo, más probable y máximo.").pack(side="left", padx=8)
            pf = tk.Frame(interior, background=p.tarjeta_2)
            pf.pack(fill="x")
            self.clima_param_frames[k] = pf
            self._params_clima(k, inicial=True)

    def _params_clima(self, k: str, inicial: bool = False) -> None:
        p = self.app.p
        pf = self.clima_param_frames[k]
        for w in pf.winfo_children():
            w.destroy()
        e = self.app.datos.estocasticos[k]
        tipo = self.clima_vars[k].get()
        vals = e["parametros"] if (inicial or tipo == e["tipo"]) else {}
        defectos = {"media": 20.0, "std": 3.0, "min": 0.0, "max": 10.0, "moda": 5.0}
        for i, (pk, rot) in enumerate(PARAMS[tipo]):
            f = tk.Frame(pf, background=p.tarjeta_2)
            f.grid(row=0, column=i, padx=(0, 20), pady=4)
            etiqueta(f, p, rot, 10, suave=True, fondo=p.tarjeta_2).pack(anchor="w")
            ttk.Entry(f, textvariable=self._var(f"e_{k}_{pk}", vals.get(pk, defectos[pk])), width=10).pack()
        for i, (ek, rot) in enumerate((("amplitud_estacional", "Cambio por estación"), ("dia_pico", "Día pico del año"))):
            f = tk.Frame(pf, background=p.tarjeta_2)
            f.grid(row=1, column=i, padx=(0, 20), pady=4, sticky="w")
            etiqueta(f, p, rot, 10, suave=True, fondo=p.tarjeta_2).pack(anchor="w")
            ttk.Entry(f, textvariable=self._var(f"e_{k}_{ek}", e.get(ek, 0)), width=10).pack()

    # ---- Márkov
    def _estado(self) -> None:
        p, c = self.app.p, self.sec["estado"].cuerpo
        top = tk.Frame(c, background=p.tarjeta)
        top.pack(fill="x", pady=(0, 10))
        self.var_cadena = tk.StringVar(value="salud")
        from src.presentacion.widgets.base import Segmentado
        Segmentado(top, p, list(CADENAS.items()), self._cambiar_cadena).pack(side="left")
        self.mk = tk.Frame(c, background=p.tarjeta)
        self.mk.pack(fill="x")
        self.mk_cadena = "salud"
        self.mk_entradas: Dict[str, Dict] = {}
        self._pintar_matriz()
        acc = tk.Frame(c, background=p.tarjeta)
        acc.pack(fill="x", pady=(12, 0))
        for txt, fn in (("Normalizar filas", self._normalizar), ("Agregar estado", self._agregar), ("Quitar estado", self._quitar),
                        ("Guardar matriz", self._guardar_matriz), ("Cargar guardada", self._cargar_matriz)):
            Boton(acc, p, txt, fn, "secundario", fondo=p.tarjeta, tam=10).pack(side="left", padx=(0, 8))
        self.msg_mk = etiqueta(c, p, "", 10, suave=True, wraplength=640)
        self.msg_mk.pack(anchor="w", pady=(8, 0))

    def _cambiar_cadena(self, clave: str) -> None:
        self._leer_matriz()
        self.mk_cadena = clave
        self._pintar_matriz()

    def _pintar_matriz(self) -> None:
        p = self.app.p
        for w in self.mk.winfo_children():
            w.destroy()
        ch = self.app.datos.estado[self.mk_cadena]
        est = ch["estados"]
        self.mk_entradas = {"m": [], "r": [], "suma": []}
        etiqueta(self.mk, p, "De ↓ / A →", 9, suave=True).grid(row=0, column=0, padx=4)
        for j, e in enumerate(est):
            etiqueta(self.mk, p, e, 10, "bold").grid(row=0, column=j + 1, padx=4)
        etiqueta(self.mk, p, "Suma", 10, "bold").grid(row=0, column=len(est) + 1, padx=4)
        etiqueta(self.mk, p, "Rinde (0–1)", 10, "bold").grid(row=0, column=len(est) + 2, padx=4)
        for i, e in enumerate(est):
            etiqueta(self.mk, p, e, 10, "bold").grid(row=i + 1, column=0, sticky="w", padx=4)
            fila = []
            for j in range(len(est)):
                v = tk.StringVar(value=f"{ch['matriz'][i][j]:g}")
                en = ttk.Entry(self.mk, textvariable=v, width=7, justify="center")
                en.grid(row=i + 1, column=j + 1, padx=3, pady=3)
                v.trace_add("write", lambda *a, i=i: self._suma(i))
                fila.append(v)
            self.mk_entradas["m"].append(fila)
            s = etiqueta(self.mk, p, "", 10, "bold")
            s.grid(row=i + 1, column=len(est) + 1, padx=6)
            self.mk_entradas["suma"].append(s)
            rv = tk.StringVar(value=f"{ch['rendimiento_por_estado'].get(e, 0.5):g}")
            ttk.Entry(self.mk, textvariable=rv, width=7, justify="center").grid(row=i + 1, column=len(est) + 2, padx=3)
            self.mk_entradas["r"].append(rv)
            self._suma(i)
        f = tk.Frame(self.mk, background=p.tarjeta)
        f.grid(row=len(est) + 1, column=0, columnspan=len(est) + 3, sticky="w", pady=(10, 0))
        etiqueta(f, p, "Estado inicial", 11, width=14).pack(side="left")
        self.var_inicial = tk.StringVar(value=ch["estado_inicial"])
        ttk.Combobox(f, textvariable=self.var_inicial, values=est, state="readonly", width=14).pack(side="left")

    def _suma(self, i: int) -> None:
        p = self.app.p
        try:
            s = sum(float(v.get().replace(",", ".")) for v in self.mk_entradas["m"][i])
        except ValueError:
            self.mk_entradas["suma"][i].configure(text="?", foreground=p.error)
            return
        ok = abs(s - 1) < 1e-6
        self.mk_entradas["suma"][i].configure(text=f"{s:.3g}", foreground=p.ok if ok else p.error)

    def _leer_matriz(self) -> List[str]:
        """Pasa lo escrito a los datos. Devuelve errores (vacío si todo bien)."""
        ch = self.app.datos.estado[self.mk_cadena]
        est = ch["estados"]
        try:
            m = [[float(v.get().replace(",", ".")) for v in fila] for fila in self.mk_entradas["m"]]
            r = {e: float(v.get().replace(",", ".")) for e, v in zip(est, self.mk_entradas["r"])}
        except ValueError:
            return [f"Hay un valor que no es número en la matriz de «{CADENAS[self.mk_cadena]}»."]
        ch["matriz"], ch["rendimiento_por_estado"] = m, r
        ch["estado_inicial"] = self.var_inicial.get() or est[0]
        malas = mx.filas_invalidas(m)
        return [f"En «{CADENAS[self.mk_cadena]}», la fila «{est[malas[0]]}» no suma 1. Usa «Normalizar filas»."] if malas else []

    def _normalizar(self) -> None:
        ch = self.app.datos.estado[self.mk_cadena]
        self._leer_matriz()
        ch["matriz"] = mx.normalizar_filas(ch["matriz"])
        self._pintar_matriz()
        self.msg_mk.configure(text="Filas normalizadas: ahora todas suman 1.")

    def _agregar(self) -> None:
        from tkinter import simpledialog
        nombre = simpledialog.askstring("Agregar estado", "Nombre del nuevo estado:", parent=self)
        if not nombre:
            return
        ch = self.app.datos.estado[self.mk_cadena]
        self._leer_matriz()
        try:
            ch["estados"], ch["matriz"] = mx.agregar_estado(ch["estados"], ch["matriz"], nombre)
            ch["rendimiento_por_estado"][nombre.strip()] = 0.5
        except ValueError as exc:
            self.msg_mk.configure(text=str(exc))
            return
        self._pintar_matriz()
        self.msg_mk.configure(text=f"Estado «{nombre.strip()}» agregado (absorbente). Ajusta sus probabilidades.")

    def _quitar(self) -> None:
        ch = self.app.datos.estado[self.mk_cadena]
        self._leer_matriz()
        nombre = ch["estados"][-1]
        try:
            ch["estados"], ch["matriz"] = mx.quitar_estado(ch["estados"], ch["matriz"], nombre)
        except ValueError as exc:
            self.msg_mk.configure(text=str(exc))
            return
        ch["rendimiento_por_estado"].pop(nombre, None)
        if ch["estado_inicial"] == nombre:
            ch["estado_inicial"] = ch["estados"][0]
        self._pintar_matriz()
        self.msg_mk.configure(text=f"Estado «{nombre}» quitado (el último de la lista).")

    def _guardar_matriz(self) -> None:
        errs = self._leer_matriz()
        if errs:
            self.msg_mk.configure(text=errs[0])
            return
        ch = self.app.datos.estado[self.mk_cadena]
        try:
            self.app.ctx.repo_matrices.guardar(f"{CADENAS[self.mk_cadena]} {date.today():%d/%m/%Y}", self.mk_cadena, ch["estados"], ch["matriz"])
            self.msg_mk.configure(text="Matriz guardada.")
        except Exception as exc:
            self.msg_mk.configure(text=f"No se pudo guardar: {exc}")

    def _cargar_matriz(self) -> None:
        ms = self.app.ctx.repo_matrices.listar(self.mk_cadena)
        if not ms:
            self.msg_mk.configure(text="Aún no hay matrices guardadas para esta cadena.")
            return
        m = ms[-1]
        ch = self.app.datos.estado[self.mk_cadena]
        ch["estados"], ch["matriz"] = list(m["estados"]), m["matriz_transicion"]
        ch["rendimiento_por_estado"] = {e: ch["rendimiento_por_estado"].get(e, 0.5) for e in ch["estados"]}
        if ch["estado_inicial"] not in ch["estados"]:
            ch["estado_inicial"] = ch["estados"][0]
        self._pintar_matriz()
        self.msg_mk.configure(text=f"Cargada: {m['nombre']}.")

    # ---- eventos y plan
    def _eventos(self) -> None:
        c = self.sec["eventos"].cuerpo
        for i, (k, ev) in enumerate(self.app.datos.eventos_raros.items()):
            et = {"plagas": "Plagas", "heladas": "Heladas", "lluvias_intensas": "Lluvias intensas"}.get(k, k)
            self._fila(c, f"{et}: por mes", f"ev_{k}_tasa_mensual", ev["tasa_mensual"], "Cuántas veces ocurre en promedio cada mes.", fila=i, col=0)
            self._fila(c, "Pérdida por evento", f"ev_{k}_perdida", ev["perdida"], "Fracción de cosecha que se pierde (0 a 1).", fila=i, col=1)

    def _plan(self) -> None:
        c, pl = self.sec["plan"].cuerpo, self.app.datos.plan
        campos = [("temporadas", "Temporadas (1–10)", pl["temporadas"], "Con más de 10 el programa avisa que es menos confiable."),
                  ("media_descendientes", "Descendientes por planta", pl["media_descendientes"], "Si es menor que 1, el cultivo se extingue."),
                  ("plantas_iniciales", "Plantas iniciales", pl["plantas_iniciales"], ""), ("capacidad", "Capacidad del terreno", pl["capacidad"], "Máximo de plantas que caben."),
                  ("agotamiento_suelo", "Agotamiento del suelo", pl["agotamiento_suelo"], "Cuánto empeora el suelo cada temporada (0 a 1).")]
        for i, (k, rot, v, ay) in enumerate(campos):
            self._fila(c, rot, "p_" + k, v, ay, fila=i // 2, col=i % 2)

    # -------------------------------------------------------------- datos <-> pantalla
    def volcar(self) -> List[str]:
        d, errs = self.app.datos, []

        def n(clave, etq):
            x = numero(self.vars[clave].get())
            if x is None:
                errs.append(f"«{etq}» debe ser un número.")
            return x
        cu = d.cultivo
        nuevos = {}
        for k in ("dias_crecimiento", "temp_min", "temp_max", "requerimiento_agua", "resistencia_plagas", "rendimiento_base"):
            x = n("c_" + k, k.replace("_", " "))
            if x is not None:
                nuevos[k] = int(x) if k == "dias_crecimiento" else x
        if len(nuevos) == 6:
            d.cultivo = Cultivo(nombre=cu.nombre, id=cu.id, **nuevos)
        for k in ("ph", "nitrogeno", "fosforo", "potasio", "resistencia", "agua"):
            x = n("d_" + k, k)
            if x is not None:
                d.deterministas[k] = x
        d.deterministas["fecha"] = self.vars["d_fecha"].get().strip()
        for k in VARS_CLIMA:
            e = d.estocasticos[k]
            e["tipo"] = self.clima_vars[k].get()
            e["parametros"] = {pk: n(f"e_{k}_{pk}", f"{k} {pk}") for pk, _ in PARAMS[e["tipo"]]}
            for ek in ("amplitud_estacional", "dia_pico"):
                x = n(f"e_{k}_{ek}", f"{k} {ek}")
                e[ek] = (int(x) if ek == "dia_pico" else x) if x is not None else e.get(ek, 0)
        for k, ev in d.eventos_raros.items():
            for ek in ("tasa_mensual", "perdida"):
                x = n(f"ev_{k}_{ek}", f"{k} {ek}")
                if x is not None:
                    ev[ek] = x
        for k in ("temporadas", "media_descendientes", "plantas_iniciales", "capacidad", "agotamiento_suelo"):
            x = n("p_" + k, k.replace("_", " "))
            if x is not None:
                d.plan[k] = int(x) if k in ("temporadas", "plantas_iniciales", "capacidad") else x
        errs += self._leer_matriz()
        errs = [e for e in errs if e]
        self._resumenes()
        return errs[:1] if errs else errs

    def refrescar(self) -> None:
        for w in self.winfo_children():
            w.destroy()
        self.__init__(self.master, self.app)
        self.pack(fill="both", expand=True)

    def _resumenes(self) -> None:
        d = self.app.datos
        self.sec["cultivo"].poner_resumen(d.cultivo.nombre)
        self.sec["suelo"].poner_resumen(f"pH {d.deterministas['ph']:g} · {d.deterministas['fecha']}")
        self.sec["clima"].poner_resumen("3 variables")
        self.sec["estado"].poner_resumen(f"{len(d.estado)} cadenas")
        self.sec["eventos"].poner_resumen(f"{len(d.eventos_raros)} eventos")
        t = int(d.plan.get("temporadas", 1))
        self.sec["plan"].poner_resumen(f"{t} temporada{'s' if t != 1 else ''}")
