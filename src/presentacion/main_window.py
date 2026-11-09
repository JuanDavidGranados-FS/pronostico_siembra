"""Ventana principal: barra superior, páginas una a la vez, panel del asistente, avisos y ejecución en segundo plano."""
from __future__ import annotations

import glob
import logging
import os
import queue
import threading
import tkinter as tk
from datetime import datetime
from tkinter import filedialog
from typing import Any, Dict, List, Optional

import ttkbootstrap as ttk

from src.aplicacion.contexto import Contexto
from src.aplicacion.validador import ErrorValidacion
from src.dominio.entidades import DatosEntrada, datos_por_defecto
from src.presentacion import movil, tema
from src.presentacion.panel_asistente import PanelAsistente
from src.presentacion.paginas import PAGINAS
from src.presentacion.tour import Tour
from src.presentacion.widgets.base import Boton, Segmentado
from src.presentacion.widgets.indicador_conexion import IndicadorConexion

log = logging.getLogger(__name__)
NAV = [("inicio", "Inicio"), ("datos", "Datos"), ("relevancia", "Relevancia"), ("simulacion", "Simulación"),
       ("resultados", "Resultados"), ("historial", "Historial"), ("ayuda", "Ayuda")]
INTERVALO_CARPETA_MS = 3000


class VentanaPrincipal(ttk.Window):
    """Coordina páginas y servicios. Las páginas se comunican con la aplicación solo a través de esta clase."""

    def __init__(self, ctx: Contexto) -> None:
        super().__init__(title="Siembra · Pronóstico de siembra adaptable", themename="flatly", size=(1180, 800))
        tema.configurar_pantalla(self)
        if not tema.MOVIL:
            self.minsize(960, 660)
        self._reflujo_id = None
        self._reflujos_seguidos = 0
        self._ancho_visto = 0
        self.ctx = ctx
        self.datos: DatosEntrada = datos_por_defecto()
        self.resultado: Optional[Dict[str, Any]] = None
        self.id_resultado: Optional[int] = None
        self.pesos_origen = "Valores sugeridos"
        self.registro_json: List[Dict[str, Any]] = []
        self._cola: queue.Queue = queue.Queue()
        self.ejecutando = False
        self._vistos: Dict[str, float] = {}
        modo = ctx.preferencias.obtener("tema", "claro")
        self.p = tema.OSCURO if modo == "oscuro" else tema.CLARO
        self.pagina_actual = "inicio"
        self._construir()
        self.after(150, self._consultar_cola)
        self.after(INTERVALO_CARPETA_MS, self._vigilar_carpeta)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        if tema.MOVIL:
            self.bind("<Configure>", self._al_redimensionar, add="+")
        if not ctx.preferencias.obtener("tour_visto", False):
            self.after(700, lambda: Tour(self).iniciar())

    # ------------------------------------------------------------ construcción
    def _construir(self) -> None:
        tema.aplicar(self, self.p)
        p, m = self.p, tema.MOVIL
        margen = tema.px(6) if m else 24
        self.cabecera = tk.Frame(self, background=p.fondo)
        self.cabecera.pack(fill="x", padx=margen, pady=(tema.px(6), tema.px(4)) if m else (16, 8))
        tk.Label(self.cabecera, text="✿", font=tema.fuente(20, "bold"), foreground=p.primario, background=p.fondo).pack(side="left")
        tk.Label(self.cabecera, text="Siembra", font=tema.fuente(15, "bold"), foreground=p.texto, background=p.fondo,
                 padx=8).pack(side="left", padx=(0, 18))
        # En el celular, el menú va en su propia franja debajo (y salta de renglón si no cabe).
        self.nav = Segmentado(self if m else self.cabecera, p, NAV, self.ir, inicial=self.pagina_actual)
        if m:
            self.nav.pack(fill="x", padx=margen, pady=(0, tema.px(6)))
        else:
            self.nav.pack(side="left")
        self.btn_asistente = Boton(self.cabecera, p, "✦ Preguntar", self.alternar_asistente, "primario", fondo=p.fondo)
        self.btn_asistente.pack(side="right")
        self.btn_tema = Boton(self.cabecera, p, "☾" if not p.oscuro else "☀", self.cambiar_tema, "fantasma", fondo=p.fondo, ancho=44)
        self.btn_tema.pack(side="right", padx=8)
        self.semaforo = IndicadorConexion(self.cabecera, p, self.mostrar_registro, compacto=m)
        self.semaforo.pack(side="right", padx=8)
        cuerpo = tk.Frame(self, background=p.fondo)
        cuerpo.pack(fill="both", expand=True)
        self.zona = tk.Frame(cuerpo, background=p.fondo)
        self._pack_zona = dict(side="left", fill="both", expand=True, padx=(margen, margen) if m else (24, 12),
                               pady=(0, tema.px(6)) if m else (0, 20))
        self.zona.pack(**self._pack_zona)
        self.asistente = PanelAsistente(cuerpo, self)
        self.asistente_visible = False
        self.paginas: Dict[str, tk.Frame] = {}
        self.aviso_lbl = tk.Label(self, text="", font=tema.fuente(10, "bold"), padx=16, pady=10)
        self.mostrar(self.pagina_actual)

    def _reconstruir(self) -> None:
        """Vuelve a crear la interfaz (cambio de tema) conservando los datos y el resultado."""
        pagina, visible = self.pagina_actual, self.asistente_visible
        for w in self.winfo_children():
            w.destroy()
        self.paginas = {}
        self._construir()
        self.mostrar(pagina)
        self.nav.elegir(pagina, notificar=False)
        if visible:
            self.alternar_asistente()

    # --------------------------------------------------------------- navegación
    def ir(self, clave: str) -> None:
        """Muestra una página; antes guarda lo que el usuario haya editado en la actual."""
        if tema.MOVIL and self.asistente_visible:
            self.alternar_asistente()
        self.volcar()
        self.mostrar(clave)
        if self.nav.clave != clave:
            self.nav.elegir(clave, notificar=False)

    def mostrar(self, clave: str) -> None:
        for pg in self.paginas.values():
            pg.pack_forget()
        if clave not in self.paginas:
            self.paginas[clave] = PAGINAS[clave](self.zona, self)
        self.pagina_actual = clave
        pg = self.paginas[clave]
        pg.pack(fill="both", expand=True)
        if hasattr(pg, "al_mostrar"):
            pg.al_mostrar()
        self._reflujos_seguidos = 0
        self.programar_reflujo()

    # ------------------------------------------------------------------- celular
    def programar_reflujo(self) -> None:
        """Celular: pide reacomodar lo que no quepa a lo ancho (agrupa varias peticiones seguidas en una)."""
        if not tema.MOVIL or self._reflujo_id is not None or self._reflujos_seguidos > 6:
            return
        self._reflujo_id = self.after(40, self._reflujo)

    def _reflujo(self) -> None:
        self._reflujo_id = None
        try:
            ancho = self.winfo_width()
            cambio = movil.reacomodar(self.cabecera, self.cabecera.winfo_rootx(), self.cabecera.winfo_width())
            cambio |= movil.reacomodar(self.nav, self.nav.winfo_rootx(), self.nav.winfo_width()) if self.nav.winfo_ismapped() else False
            zona = self.asistente if self.asistente_visible else self.zona
            cambio |= movil.reacomodar(zona, zona.winfo_rootx(), zona.winfo_width())
            self._ancho_visto = ancho
        except tk.TclError:
            return
        self._reflujos_seguidos = self._reflujos_seguidos + 1 if cambio else 0

    def _al_redimensionar(self, e) -> None:
        if e.widget is self and e.width != self._ancho_visto:
            self._reflujos_seguidos = 0
            self.programar_reflujo()

    def volcar(self) -> List[str]:
        """Pide a las páginas creadas que escriban sus campos en `self.datos`. Devuelve los errores de formato."""
        errores: List[str] = []
        for pg in self.paginas.values():
            if hasattr(pg, "volcar"):
                errores += pg.volcar() or []
        return errores

    def reemplazar_datos(self, datos: DatosEntrada) -> None:
        """Carga unos datos nuevos (JSON, historial…) y refresca las páginas ya creadas."""
        self.datos = datos
        for pg in self.paginas.values():
            if hasattr(pg, "refrescar"):
                pg.refrescar()

    # ----------------------------------------------------------------- asistente
    def alternar_asistente(self) -> None:
        if tema.MOVIL:  # en el celular el asistente ocupa toda la pantalla en lugar de la página
            if self.asistente_visible:
                self.asistente.pack_forget()
                self.zona.pack(**self._pack_zona)
            else:
                self.zona.pack_forget()
                self.asistente.pack(fill="both", expand=True, padx=self._pack_zona["padx"], pady=self._pack_zona["pady"])
            self.asistente_visible = not self.asistente_visible
            self.programar_reflujo()
            return
        if self.asistente_visible:
            self.asistente.pack_forget()
        else:
            self.asistente.pack(side="right", fill="y", padx=(0, 24), pady=(0, 20), before=self.zona)
        self.asistente_visible = not self.asistente_visible

    def preguntar(self, texto: str) -> None:
        """Abre el asistente y le hace una pregunta (lo usan los botones «?»)."""
        if not self.asistente_visible:
            self.alternar_asistente()
        self.asistente.preguntar(texto)

    def contexto_asistente(self) -> Dict[str, Any]:
        return {"pagina": self.pagina_actual, "resultado": self.resultado}

    # --------------------------------------------------------------------- avisos
    def aviso(self, texto: str, tono: str = "ok", ms: int = 4200) -> None:
        """Mensaje breve en la parte inferior (no bloquea)."""
        p = self.p
        bg, fg = {"ok": (p.primario, p.sobre_primario), "error": (p.error, "#ffffff"), "aviso": (p.aviso, "#1b1300")}[tono]
        self.aviso_lbl.configure(text=texto, background=bg, foreground=fg, wraplength=tema.ancho_texto(900, 60) if tema.MOVIL else 0)
        self.aviso_lbl.place(relx=0.5, rely=1.0, anchor="s", y=-22)
        self.aviso_lbl.lift()
        if getattr(self, "_aviso_id", None):
            self.after_cancel(self._aviso_id)
        self._aviso_id = self.after(ms, self.aviso_lbl.place_forget)

    def cambiar_tema(self) -> None:
        self.p = tema.CLARO if self.p.oscuro else tema.OSCURO
        self.ctx.preferencias.guardar("tema", "oscuro" if self.p.oscuro else "claro")
        self._reconstruir()

    # ------------------------------------------------------------------ simulación
    def ejecutar(self) -> None:
        """Valida y lanza la simulación en un hilo; el resultado llega por la cola."""
        if self.ejecutando:
            return
        errores = self.volcar()
        if errores:
            self.aviso(errores[0], "error")
            self.ir("datos")
            return
        self.ejecutando = True
        datos = self.datos
        pg = self.paginas.get("simulacion")

        def trabajo() -> None:
            try:
                r = self.ctx.orquestador.ejecutar_simulacion(
                    datos, lambda i, n: self._cola.put(("progreso", (i, n))))
                self._cola.put(("listo", r))
            except ErrorValidacion as exc:
                self._cola.put(("invalido", exc.errores))
            except Exception as exc:  # nunca dejar el hilo morir en silencio
                log.exception("Falló la simulación")
                self._cola.put(("error", str(exc)))

        if pg is not None and hasattr(pg, "al_iniciar"):
            pg.al_iniciar()
        threading.Thread(target=trabajo, daemon=True).start()

    def _consultar_cola(self) -> None:
        try:
            while True:
                tipo, carga = self._cola.get_nowait()
                pg = self.paginas.get("simulacion")
                if tipo == "progreso" and pg is not None:
                    pg.al_progreso(*carga)
                    continue
                self.ejecutando = False
                if pg is not None:
                    pg.al_terminar()
                if tipo == "listo":
                    self.resultado = carga.a_dict() if hasattr(carga, "a_dict") else carga
                    self.id_resultado = self.resultado.get("id")
                    viejo = self.paginas.pop("resultados", None)
                    if viejo is not None:  # si no se destruye, la página anterior queda visible encima de la nueva
                        viejo.destroy()
                    self.ir("resultados")
                    self.aviso("Listo: ya tienes tu recomendación.")
                elif tipo == "invalido":
                    self.aviso(carga[0], "error")
                else:
                    self.aviso("No se pudo completar la simulación. Revisa los datos e inténtalo de nuevo.", "error")
        except queue.Empty:
            pass
        self.after(120, self._consultar_cola)

    # ---------------------------------------------------------------- datos externos
    def cargar_json(self, ruta: Optional[str] = None) -> None:
        """Botón «Cargar JSON»: pide un archivo y lo procesa igual que la carpeta de entrada."""
        ruta = ruta or filedialog.askopenfilename(title="Elige un archivo JSON", filetypes=[("JSON", "*.json")])
        if ruta:
            self.recibir_json(ruta, "manual")

    def recibir_json(self, ruta: str, origen: str = "carpeta") -> bool:
        """Lee, valida y aplica un JSON externo; actualiza semáforo y registro. Devuelve True si fue válido."""
        ahora = datetime.now()
        nombre = os.path.basename(ruta)
        try:
            doc = self.ctx.adaptador.leer_json(ruta)
            errores = self.ctx.adaptador.validar(doc)
        except Exception as exc:
            doc, errores = None, [str(exc)]
        valido = not errores
        try:
            self.ctx.repo_externos.guardar(f"{origen}:{nombre}", doc or {}, valido)
        except Exception:
            log.exception("No se pudo guardar el dato externo")
        self.registro_json.insert(0, {"hora": ahora, "archivo": nombre, "valido": valido,
                                      "detalle": "Datos aplicados." if valido else errores[0]})
        del self.registro_json[100:]
        self.semaforo.actualizar("conectado" if valido else "error", ahora)
        if valido:
            self.reemplazar_datos(self.ctx.adaptador.a_datos_entrada(doc))
            self.aviso(f"Datos de «{nombre}» cargados.")
        else:
            self.aviso(f"«{nombre}» no es válido: {errores[0]}", "error", 7000)
        pg = self.paginas.get("inicio")
        if pg is not None and hasattr(pg, "refrescar_registro"):
            pg.refrescar_registro()
        return valido

    def _vigilar_carpeta(self) -> None:
        """Mira la carpeta de entrada y procesa los JSON nuevos o modificados."""
        try:
            for ruta in glob.glob(os.path.join(self.ctx.carpeta_entrada, "*.json")):
                m = os.path.getmtime(ruta)
                if self._vistos.get(ruta) != m:
                    primera = ruta not in self._vistos
                    self._vistos[ruta] = m
                    if True:
                        self.recibir_json(ruta, "carpeta")
        except Exception:
            log.exception("Error vigilando la carpeta de entrada")
        self.after(INTERVALO_CARPETA_MS, self._vigilar_carpeta)

    def mostrar_registro(self) -> None:
        self.ir("inicio")
        pg = self.paginas.get("inicio")
        if pg is not None and hasattr(pg, "abrir_registro"):
            pg.abrir_registro()

    def reiniciar_tour(self) -> None:
        Tour(self).iniciar()
