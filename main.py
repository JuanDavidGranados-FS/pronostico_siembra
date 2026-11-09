#Pydroid run tkinter
"""Punto de entrada: compone las capas (PostgreSQL o memoria) y lanza la aplicación de escritorio."""
from __future__ import annotations

import logging
import os
import sys
import tkinter

from src.aplicacion.contexto import Contexto
from src.aplicacion.diagnostico import Diagnostico
from src.aplicacion.gestor_historial import GestorHistorial
from src.aplicacion.gestor_relevancia import GestorRelevancia
from src.aplicacion.orquestador import OrquestadorSimulacion
from src.infraestructura.adaptador_json import AdaptadorJSON
from src.infraestructura.config import cargar_config
from src.infraestructura.logger import configurar_logger
from src.infraestructura import repositorio_memoria as mem
from src.infraestructura.preferencias import Preferencias, carpeta_usuario

log = logging.getLogger("main")

# Archivo donde se guarda el error si la app se cae (útil en Pydroid, que no lo muestra).
ARCHIVO_ERROR = "/storage/emulated/0/Download/pronostico_siembra/error.txt"


def carpeta_entrada() -> str:
    """Carpeta que se vigila en busca de JSON externos ($SIEMBRA_ENTRADA o <datos del usuario>/entrada)."""
    ruta = os.environ.get("SIEMBRA_ENTRADA") or os.path.join(carpeta_usuario(), "entrada")
    os.makedirs(ruta, exist_ok=True)
    return ruta


def construir_contexto(forzar_memoria: bool = False, preferencias: Preferencias | None = None, entrada: str = "") -> Contexto:
    """Usa PostgreSQL si responde (y tiene datos); si no, repositorios en memoria."""
    repos, modo, probar = None, "memoria (sin persistencia)", (lambda: False)
    if not forzar_memoria:
        try:
            from src.infraestructura import repositorio_postgres as pg
            con = pg.ConexionPostgres(cargar_config())
            if con.probar():
                cultivos = pg.RepositorioCultivosPG(con)
                if not cultivos.listar():
                    raise RuntimeError("La tabla 'cultivos' está vacía: ejecuta db/init.sql")
                repos = (cultivos, pg.RepositorioConfiguracionesPG(con), pg.RepositorioHistorialPG(con), pg.RepositorioDatosExternosPG(con),
                         pg.RepositorioConfigRelevanciaPG(con), pg.RepositorioMatricesPG(con), pg.RepositorioRegistrosCampoPG(con))
                modo, probar = "PostgreSQL", con.probar
            else:
                log.warning("PostgreSQL no responde; se usa memoria.")
        except Exception as exc:
            log.warning("No se usará PostgreSQL (%s); se usa memoria.", exc)
    if repos is None:
        repos = (mem.RepositorioCultivosMemoria(), mem.RepositorioConfiguracionesMemoria(), mem.RepositorioHistorialMemoria(),
                 mem.RepositorioDatosExternosMemoria(), mem.RepositorioConfigRelevanciaMemoria(), mem.RepositorioMatricesMemoria(),
                 mem.RepositorioRegistrosCampoMemoria())
    cultivos, config, historial, externos, relev, matrices, registros = repos
    gestor_rel = GestorRelevancia(relev, registros)
    entrada = entrada or carpeta_entrada()
    return Contexto(orquestador=OrquestadorSimulacion(cultivos, config, historial), historial=GestorHistorial(historial), relevancia=gestor_rel,
                    diagnostico=Diagnostico(modo, probar, cultivos, gestor_rel, entrada), repo_config=config, repo_historial=historial,
                    repo_externos=externos, repo_matrices=matrices, adaptador=AdaptadorJSON(), preferencias=preferencias or Preferencias(),
                    modo_bd=modo, carpeta_entrada=entrada)


# Versión mínima de msgcat (sin traducciones) por si el Tcl del entorno no la trae (p. ej. Pydroid 3).
_MSGCAT_MINIMO = r"""
namespace eval ::msgcat {}
proc ::msgcat::mc {src args} { if {[llength $args]} { return [format $src {*}$args] }; return $src }
proc ::msgcat::mcmset {locale pairs} { return [expr {[llength $pairs] / 2}] }
proc ::msgcat::mcset {locale src {trans ""}} { return $src }
proc ::msgcat::mclocale {args} { return en }
proc ::msgcat::mcpreferences {} { return {en} }
proc ::msgcat::mcload {dir} { return 0 }
proc ::msgcat::mcmax {args} { set m 0; foreach s $args { set m [expr {max($m, [string length $s])}] }; return $m }
"""


def asegurar_msgcat() -> None:
    """Carga msgcat en Tcl antes de que ttkbootstrap la use; si no existe, instala una versión mínima."""
    try:
        from ttkbootstrap import localization
    except ImportError:
        return
    original = localization.initialize_localities

    def inicializar_seguro() -> None:
        root = tkinter._default_root
        if root is not None:
            try:
                root.tk.call("package", "require", "msgcat")
            except tkinter.TclError:
                log.warning("Tcl sin paquete msgcat; se usa una versión mínima sin traducciones.")
                root.tk.eval(_MSGCAT_MINIMO)
        original()

    localization.initialize_localities = inicializar_seguro


def main() -> int:
    """Arranca la aplicación."""
    configurar_logger()
    asegurar_msgcat()
    ctx = construir_contexto()
    from src.presentacion.main_window import VentanaPrincipal  # import tardío: requiere entorno gráfico
    VentanaPrincipal(ctx).mainloop()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        import traceback
        try:
            with open(ARCHIVO_ERROR, "w", encoding="utf-8") as f:
                traceback.print_exc(file=f)
        except OSError:
            pass
        raise
