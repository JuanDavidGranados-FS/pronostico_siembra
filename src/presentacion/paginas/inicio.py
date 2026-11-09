"""Inicio: una invitación clara a comenzar y, bajo demanda, el estado del sistema y los datos externos."""
from __future__ import annotations

import tkinter as tk

import ttkbootstrap as ttk

from src.aplicacion.diagnostico import ADVERTENCIA, FALTA, OK
from src.presentacion.paginas.comun import encabezado
from src.presentacion import tema
from src.presentacion.tema import fuente
from src.presentacion.widgets.base import Boton, GrupoAcordeon, PaginaScroll, Pastilla, Tarjeta, etiqueta

TONO = {OK: "ok", ADVERTENCIA: "aviso", FALTA: "error"}


class PaginaInicio(tk.Frame):
    def __init__(self, master, app) -> None:
        super().__init__(master, background=app.p.fondo)
        self.app, p = app, app.p
        sc = PaginaScroll(self, p)
        sc.pack(fill="both", expand=True)
        cont = sc.interior
        h = tk.Frame(cont, background=p.fondo)
        h.pack(fill="x", pady=(8, 20))
        encabezado(h, app, "¿Cuándo es mejor sembrar?",
                   "Responde en unos pasos y te recomendamos una fecha, con el motivo y el riesgo.").pack(anchor="w")
        fila = tk.Frame(h, background=p.fondo)
        fila.pack(anchor="w", pady=18)
        Boton(fila, p, "Comenzar simulación", lambda: app.ir("datos"), "primario", fondo=p.fondo, ancho=210).pack(side="left")
        Boton(fila, p, "Ejecutar con valores sugeridos", app.ejecutar, "secundario", fondo=p.fondo).pack(side="left", padx=10)
        Boton(fila, p, "Recorrido de 1 minuto", app.reiniciar_tour, "fantasma", fondo=p.fondo).pack(side="left")
        grupo = GrupoAcordeon()
        self.s_estado = grupo.crear(cont, p, "Estado del sistema", resumen="", ayuda="Comprueba que la base de datos, los cultivos y la relevancia estén listos.",
                                    al_preguntar=lambda: app.preguntar("¿Funciona sin PostgreSQL?"))
        self.s_estado.pack(fill="x", pady=5)
        self.s_json = grupo.crear(cont, p, "Datos de un simulador (JSON)", resumen="Opcional",
                                  ayuda="Un simulador o mod puede enviarte datos como archivo JSON.", al_preguntar=lambda: app.preguntar("¿Puedo usar datos de un simulador?"))
        self.s_json.pack(fill="x", pady=5)
        self._armar_estado()
        self._armar_json()
        self.refrescar_registro()

    def al_mostrar(self) -> None:
        self._armar_estado()

    def _armar_estado(self) -> None:
        p, app = self.app.p, self.app
        c = self.s_estado.cuerpo
        for w in c.winfo_children():
            w.destroy()
        items = app.ctx.diagnostico.ejecutar()
        for it in items:
            f = tk.Frame(c, background=p.tarjeta)
            f.pack(fill="x", pady=6)
            Pastilla(f, p, {OK: "Listo", ADVERTENCIA: "Opcional", FALTA: "Falta"}[it.estado], TONO[it.estado]).pack(side="left")
            tk.Label(f, text=it.titulo, font=fuente(11, "bold"), foreground=p.texto, background=p.tarjeta, padx=12).pack(side="left")
            tk.Label(f, text=it.mensaje, font=fuente(10), foreground=p.suave, background=p.tarjeta, wraplength=440, justify="left").pack(side="left")
            if it.accion:
                Boton(f, p, it.accion, lambda i=it: self._accion(i.accion_id), "secundario", fondo=p.tarjeta, tam=10).pack(side="right")
        listo = app.ctx.diagnostico.listo(items)
        self.s_estado.poner_resumen("Todo listo" if listo else "Hay algo por arreglar")

    def _accion(self, ident: str) -> None:
        app = self.app
        if ident == "configurar_bd":
            self._dialogo("Activar PostgreSQL", app.ctx.diagnostico.instrucciones_bd())
        elif ident == "cargar_cultivos":
            n = app.ctx.diagnostico.cargar_cultivos_defecto()
            app.aviso(f"Se cargaron {n} cultivos.")
        elif ident == "crear_relevancia":
            app.ctx.diagnostico.crear_relevancia_defecto()
            app.aviso("Se creó la configuración de relevancia por defecto.")
        elif ident == "cargar_json":
            app.cargar_json()
        self._armar_estado()

    def _dialogo(self, titulo: str, texto: str) -> None:
        p = self.app.p
        v = tk.Toplevel(self)
        v.title(titulo)
        v.configure(background=p.tarjeta)
        tema.dialogo(v, "520x330")
        tk.Label(v, text=titulo, font=fuente(14, "bold"), foreground=p.texto, background=p.tarjeta).pack(anchor="w", padx=22, pady=(20, 8))
        tk.Label(v, text=texto, font=fuente(11), foreground=p.texto, background=p.tarjeta, justify="left", wraplength=tema.ancho_texto(470)).pack(anchor="w", padx=22)
        Boton(v, p, "Entendido", v.destroy, "primario", fondo=p.tarjeta).pack(anchor="e", padx=22, pady=18)

    def _armar_json(self) -> None:
        p, app = self.app.p, self.app
        c = self.s_json.cuerpo
        etiqueta(c, p, f"Carpeta de entrada: {app.ctx.carpeta_entrada}", 10, suave=True, wraplength=620).pack(anchor="w")
        fila = tk.Frame(c, background=p.tarjeta)
        fila.pack(fill="x", pady=10)
        Boton(fila, p, "Cargar JSON", app.cargar_json, "primario", fondo=p.tarjeta).pack(side="left")
        Boton(fila, p, "Guía de integración", lambda: app.ir("ayuda") or app.paginas["ayuda"].abrir("integracion"), "fantasma", fondo=p.tarjeta).pack(side="left", padx=8)
        self.tabla = ttk.Treeview(c, columns=("hora", "archivo", "estado", "detalle"), show="headings", height=5)
        for col, txt, w in (("hora", "Hora", 80), ("archivo", "Archivo", 160), ("estado", "Estado", 80), ("detalle", "Detalle", 320)):
            self.tabla.heading(col, text=txt)
            self.tabla.column(col, width=w, anchor="w")
        self.tabla.pack(fill="x")

    def refrescar_registro(self) -> None:
        self.tabla.delete(*self.tabla.get_children())
        for r in self.app.registro_json[:20]:
            self.tabla.insert("", "end", values=(f"{r['hora']:%H:%M:%S}", r["archivo"], "Válido" if r["valido"] else "Inválido", r["detalle"]))
        n = len(self.app.registro_json)
        self.s_json.poner_resumen(f"{n} recibido{'s' if n != 1 else ''}" if n else "Opcional")

    def abrir_registro(self) -> None:
        self.s_json.abrir()
