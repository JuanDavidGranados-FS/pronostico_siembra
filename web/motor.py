"""Puente entre la versión web (JavaScript + Pyodide) y la aplicación en Python.

Corre dentro del navegador y reutiliza sin cambios `src/dominio`, `src/aplicacion` y parte de `src/infraestructura`
(repositorios en memoria, gráficas, exportador, lector de históricos). Cumple el mismo papel que `main.py` + la
ventana de escritorio: arma el contexto y ofrece las operaciones que usan las páginas.

Todo se guarda en el propio dispositivo: `instantanea()` devuelve el contenido de los repositorios para que la página
lo guarde en el navegador (localStorage) y `restaurar()` lo carga al volver a abrir la página.

Convención: cada función pública recibe y devuelve texto JSON (o bytes en `exportar`).
"""
from __future__ import annotations

import io
import json
import os
from datetime import date, datetime
from typing import Any, Callable, Dict, List, Optional

from src.aplicacion import asistente
from src.aplicacion.explicador import fecha_larga
from src.aplicacion.gestor_historial import GestorHistorial
from src.aplicacion.gestor_relevancia import GestorRelevancia
from src.aplicacion.orquestador import OrquestadorSimulacion
from src.aplicacion.reutilizacion import configuracion_de_simulacion
from src.aplicacion.validador import ErrorValidacion
from src.dominio import matrices as mx
from src.dominio import metodos_relevancia as mr
from src.dominio.entidades import PESOS_POR_DEFECTO, Cultivo, DatosEntrada, datos_por_defecto
from src.infraestructura.adaptador_json import AdaptadorJSON
from src.infraestructura.repositorio_memoria import (RepositorioConfigRelevanciaMemoria, RepositorioConfiguracionesMemoria,
                                                     RepositorioCultivosMemoria, RepositorioHistorialMemoria,
                                                     RepositorioMatricesMemoria, RepositorioRegistrosCampoMemoria)

os.environ.setdefault("MPLBACKEND", "Agg")  # en el navegador no hay ventana: matplotlib solo dibuja a archivos

# Igual que exportador.FORMATOS (ese módulo importa matplotlib, que se carga solo cuando hace falta).
FORMATOS = {".pdf": "Informe PDF", ".xlsx": "Excel", ".csv": "CSV (datos por fecha)", ".json": "JSON (resultados)",
            ".png": "Imagen PNG (gráficas)"}
NOMBRES_GRAFICAS = ["Rendimiento", "Fechas", "Estados", "Riesgos", "Temporadas"]
MAX_HISTORIAL = 40  # el almacenamiento del navegador es limitado

repos = {
    "cultivos": RepositorioCultivosMemoria(),
    "config": RepositorioConfiguracionesMemoria(),
    "historial": RepositorioHistorialMemoria(),
    "relevancia": RepositorioConfigRelevanciaMemoria(),
    "registros": RepositorioRegistrosCampoMemoria(),
    "matrices": RepositorioMatricesMemoria(),
}
PERSISTENTES = ("config", "historial", "relevancia", "registros", "matrices")
orquestador = OrquestadorSimulacion(repos["cultivos"], repos["config"], repos["historial"])
historial = GestorHistorial(repos["historial"])
relevancia = GestorRelevancia(repos["relevancia"], repos["registros"])
adaptador = AdaptadorJSON()
_ultimo: Optional[Dict[str, Any]] = None


# ------------------------------------------------------------------ utilidades
def _a_json(valor: Any) -> str:
    def convertir(x: Any) -> Any:
        if hasattr(x, "tolist"):
            return x.tolist()
        if hasattr(x, "item"):
            return x.item()
        if isinstance(x, (date, datetime)):
            return x.isoformat()
        if isinstance(x, (set, tuple)):
            return list(x)
        return str(x)
    return json.dumps(valor, ensure_ascii=False, default=convertir)


def _ok(valor: Any = None) -> str:
    return _a_json({"ok": True, "valor": valor})


def _error(mensaje: str) -> str:
    return _a_json({"ok": False, "error": mensaje})


def _seguro(fn: Callable) -> Callable:
    """Envuelve una operación: devuelve {"ok": True, "valor": …} o {"ok": False, "error": "mensaje legible"}."""
    def envoltura(*args, **kwargs) -> str:
        try:
            return _ok(fn(*args, **kwargs))
        except ErrorValidacion as exc:
            return _error(list(exc.errores)[0])
        except ValueError as exc:
            return _error(str(exc))
        except Exception as exc:  # nunca dejar la página sin respuesta
            return _error(f"Ocurrió un error inesperado: {exc}")
    envoltura.__name__ = fn.__name__
    envoltura.__doc__ = fn.__doc__
    return envoltura


def _datos(texto: str) -> DatosEntrada:
    return DatosEntrada.desde_dict(json.loads(texto))


def _con_textos(r: Dict[str, Any]) -> Dict[str, Any]:
    """Agrega las fechas en lenguaje natural que la página muestra."""
    fo = r.get("fecha_optima") or {}
    if fo.get("fecha"):
        fo["fecha_larga"] = fecha_larga(date.fromisoformat(fo["fecha"]))
    for x in r.get("comparaciones", []):
        x["fecha_larga"] = fecha_larga(date.fromisoformat(x["fecha"]))
    return r


# ------------------------------------------------------------------ persistencia en el dispositivo
def instantanea() -> str:
    """Contenido de los repositorios para guardarlo en el navegador."""
    h = repos["historial"]
    for id_viejo in sorted(h._filas)[:-MAX_HISTORIAL]:
        cfg = h._filas[id_viejo].get("configuracion_id")
        h.eliminar(id_viejo)
        if cfg:
            repos["config"].eliminar(cfg)
    return _a_json({k: {"filas": list(repos[k]._filas.values()), "sig": repos[k]._sig} for k in PERSISTENTES})


def restaurar(texto: str) -> None:
    """Carga lo guardado en el navegador (ignora datos dañados en lugar de fallar)."""
    try:
        guardado = json.loads(texto or "{}")
    except ValueError:
        return
    for k in PERSISTENTES:
        tabla = guardado.get(k) or {}
        try:
            filas = {int(f["id"]): f for f in tabla.get("filas", [])}
            repos[k]._filas = filas
            repos[k]._sig = max([int(tabla.get("sig", 1))] + [i + 1 for i in filas])
        except (TypeError, ValueError, KeyError):
            continue


# ------------------------------------------------------------------ arranque
@_seguro
def iniciar(guardado: str = "") -> Dict[str, Any]:
    """Restaura lo guardado y devuelve todo lo que la interfaz necesita para dibujarse."""
    restaurar(guardado)
    return {
        "datos": datos_por_defecto().a_dict(),
        "cultivos": [Cultivo.desde_dict(c).a_dict() for c in repos["cultivos"].listar()],
        "pesos_defecto": dict(PESOS_POR_DEFECTO),
        "fuente_defecto": asistente.FUENTE_DEFECTO,
        "sugerencias": list(asistente.SUGERENCIAS_INICIALES),
        "glosario": [list(x) for x in asistente.glosario()],
        "faq": [list(x) for x in asistente.PREGUNTAS_FRECUENTES],
        "variables": list(mr.VARIABLES),
        "etiquetas": dict(mr.ETIQUETAS),
        "pares_experto": [list(p) for p in relevancia.pares_experto()],
        "graficas": NOMBRES_GRAFICAS,
        "formatos": FORMATOS,
        "guia_integracion": _guia(),
    }


def _guia() -> str:
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "integration_guide.md")
    try:
        with open(ruta, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return "# Guía de integración\nNo se encontró la guía."


@_seguro
def diagnostico(n_json: int = 0) -> List[Dict[str, Any]]:
    """Los mismos cuatro ítems del panel «Estado del sistema» de escritorio, adaptados al navegador."""
    n_rel = len(relevancia.listar())
    n_cul = len(repos["cultivos"].listar())
    return [
        {"titulo": "Base de datos", "estado": "ok",
         "mensaje": "Tus simulaciones se guardan en este dispositivo (en el navegador)."},
        {"titulo": "Cultivos", "estado": "ok" if n_cul else "falta",
         "mensaje": f"{n_cul} cultivos disponibles." if n_cul else "Aún no hay cultivos para elegir."},
        {"titulo": "Factor de Relevancia", "estado": "ok" if n_rel else "advertencia",
         "mensaje": (f"{n_rel} configuración guardada." if n_rel == 1 else f"{n_rel} configuraciones guardadas." if n_rel
                     else "No hay configuración guardada: se usarán los valores sugeridos."),
         "accion": None if n_rel else "Crear Factor de Relevancia", "accion_id": None if n_rel else "crear_relevancia"},
        {"titulo": "Archivos JSON de entrada", "estado": "ok" if n_json else "advertencia",
         "mensaje": (f"{n_json} archivo{'s' if n_json != 1 else ''} recibido{'s' if n_json != 1 else ''}." if n_json else
                     "No hay archivos JSON (es opcional: sirve para datos de un simulador)."),
         "accion": None if n_json else "Cargar JSON", "accion_id": None if n_json else "cargar_json"},
    ]


@_seguro
def crear_relevancia_defecto() -> int:
    return relevancia.crear_defecto()


# ------------------------------------------------------------------ simulación
def simular(datos_json: str, progreso: Optional[Callable[[int, int], None]] = None) -> str:
    """Ejecuta la simulación (y la guarda en el historial). Devuelve {"ok", "valor": resultado} o {"ok": False, "error"}."""
    global _ultimo
    try:
        datos = _datos(datos_json)
        r = orquestador.ejecutar_simulacion(datos, (lambda i, n: progreso(i, n)) if progreso else None).a_dict()
    except ErrorValidacion as exc:
        return _error(list(exc.errores)[0])
    except (ValueError, KeyError, TypeError) as exc:
        return _error(f"Revisa tus datos: {exc}")
    except Exception as exc:
        return _error(f"No se pudo completar la simulación: {exc}")
    r["id"] = r.get("id_historial")
    _ultimo = _con_textos(r)
    return _ok(_ultimo)


# ------------------------------------------------------------------ relevancia
@_seguro
def ley_minimo(datos_json: str) -> Dict[str, Any]:
    pesos, textos = relevancia.ley_del_minimo(_datos(datos_json))
    return {"pesos": pesos, "justificaciones": textos}


@_seguro
def historico(ruta: str) -> Dict[str, Any]:
    from src.infraestructura.lector_historico import leer_historico
    return relevancia.desde_historico(leer_historico(ruta))


@_seguro
def experto(comparaciones_json: str) -> Dict[str, Any]:
    comparaciones = {(a, b): float(v) for a, b, v in json.loads(comparaciones_json)}
    res = relevancia.desde_experto(comparaciones)
    if not res["consistente"]:
        pares = " y ".join(f"{mr.ETIQUETAS[x]}-{mr.ETIQUETAS[y]}" for x, y in res["parejas_a_revisar"])
        res["resumen_consistencia"] += f" Revisa: {pares}."
    return res


@_seguro
def experimento(variable: str) -> str:
    return relevancia.experimento(variable)


@_seguro
def agregar_registro(temporada: str, variable: str, valor: str, rendimiento: str) -> int:
    relevancia.agregar_registro(temporada, variable, valor, rendimiento)
    return len(relevancia.registros())


@_seguro
def n_registros() -> int:
    return len(relevancia.registros())


@_seguro
def desde_campo(datos_json: str) -> Dict[str, Any]:
    return relevancia.desde_campo(_datos(datos_json))


@_seguro
def perfiles() -> List[Dict[str, Any]]:
    return [{"id": x["id"], "nombre": x["nombre"], "metodo": x.get("metodo", "")} for x in relevancia.listar()]


@_seguro
def guardar_perfil(nombre: str, pesos_json: str) -> int:
    return relevancia.guardar(nombre, json.loads(pesos_json), "manual")


@_seguro
def cargar_perfil(id_: int) -> Dict[str, Any]:
    return relevancia.cargar(int(id_))


@_seguro
def duplicar_perfil(id_: int) -> int:
    return relevancia.duplicar(int(id_))


@_seguro
def eliminar_perfil(id_: int) -> bool:
    return relevancia.eliminar(int(id_))


@_seguro
def exportar_perfil(id_: int) -> Dict[str, Any]:
    return relevancia.exportar(int(id_))


@_seguro
def importar_perfil(texto: str) -> int:
    try:
        doc = json.loads(texto)
    except ValueError:
        raise ValueError("El archivo no es un JSON válido.")
    return relevancia.importar(doc)


# ------------------------------------------------------------------ matrices de Márkov
@_seguro
def normalizar(matriz_json: str) -> List[List[float]]:
    return mx.normalizar_filas(json.loads(matriz_json))


@_seguro
def filas_invalidas(matriz_json: str) -> List[int]:
    return mx.filas_invalidas(json.loads(matriz_json))


@_seguro
def agregar_estado(estados_json: str, matriz_json: str, nombre: str) -> Dict[str, Any]:
    est, m = mx.agregar_estado(json.loads(estados_json), json.loads(matriz_json), nombre)
    return {"estados": est, "matriz": m}


@_seguro
def quitar_estado(estados_json: str, matriz_json: str, nombre: str) -> Dict[str, Any]:
    est, m = mx.quitar_estado(json.loads(estados_json), json.loads(matriz_json), nombre)
    return {"estados": est, "matriz": m}


@_seguro
def guardar_matriz(nombre: str, cadena: str, estados_json: str, matriz_json: str) -> int:
    return repos["matrices"].guardar(nombre, cadena, json.loads(estados_json), json.loads(matriz_json))


@_seguro
def cargar_matriz(cadena: str) -> Optional[Dict[str, Any]]:
    ms = repos["matrices"].listar(cadena)
    return ms[-1] if ms else None


# ------------------------------------------------------------------ historial
@_seguro
def listar_historial(texto: str = "", desde: str = "", hasta: str = "") -> List[Dict[str, Any]]:
    return historial.listar(texto=texto, desde=desde, hasta=hasta)


@_seguro
def abrir_simulacion(id_: int) -> Dict[str, Any]:
    global _ultimo
    sim = historial.obtener(int(id_))
    if not sim:
        raise ValueError("Esa simulación ya no existe.")
    r = sim["resultado_completo"]
    r["id"] = int(id_)
    _ultimo = _con_textos(r)
    return _ultimo


@_seguro
def renombrar(id_: int, nombre: str) -> bool:
    return historial.renombrar(int(id_), nombre)


@_seguro
def eliminar_simulacion(id_: int) -> bool:
    return historial.eliminar(int(id_))


@_seguro
def reutilizar(id_: int) -> Dict[str, Any]:
    datos = configuracion_de_simulacion(repos["historial"], repos["config"], int(id_))
    if datos is None:
        raise ValueError("Esa simulación no tiene configuración guardada.")
    return datos.a_dict()


@_seguro
def comparar(id_a: int, id_b: int) -> Dict[str, Any]:
    c = historial.comparar_detallado(int(id_a), int(id_b))
    c.pop("resultado_a", None)
    c.pop("resultado_b", None)
    return c


# ------------------------------------------------------------------ datos externos (JSON)
@_seguro
def recibir_json(texto: str, nombre: str) -> Dict[str, Any]:
    """Valida un JSON de un simulador (mismas reglas que la carpeta de entrada de escritorio)."""
    try:
        doc = json.loads(texto)
        if not isinstance(doc, dict):
            raise ValueError("El JSON debe contener un objeto en la raíz.")
        errores = adaptador.validar(doc)
    except ValueError as exc:
        doc, errores = None, [f"JSON inválido: {exc}"]
    if errores:
        return {"valido": False, "detalle": errores[0], "datos": None}
    return {"valido": True, "detalle": "Datos aplicados.", "datos": adaptador.a_datos_entrada(doc).a_dict()}


# ------------------------------------------------------------------ gráficas y exportes (usan matplotlib)
def _tema(oscuro: bool) -> Dict[str, Any]:
    from src.infraestructura import graficas as g
    return g.TEMA_OSCURO if oscuro else g.TEMA_CLARO


def _svg(fig) -> str:
    buf = io.StringIO()
    fig.savefig(buf, format="svg", facecolor=fig.get_facecolor())
    return buf.getvalue()


@_seguro
def grafica(nombre: str, oscuro: bool = False, movil: bool = False) -> str:
    """La misma gráfica de la app de escritorio (matplotlib), en SVG."""
    from matplotlib.figure import Figure
    from src.infraestructura import graficas as g
    if not _ultimo:
        raise ValueError("Aún no hay resultados.")
    dibujos = dict(g.GRAFICAS)
    fig = Figure(figsize=(6.4, 5.0) if movil else (8, 4.2), dpi=100)
    dibujos[nombre](fig, _ultimo, _tema(oscuro))
    return _svg(fig)


@_seguro
def grafica_comparacion(id_a: int, id_b: int, oscuro: bool = False, movil: bool = False) -> str:
    from matplotlib.figure import Figure
    from src.infraestructura import graficas as g
    c = historial.comparar_detallado(int(id_a), int(id_b))
    fig = Figure(figsize=(6.4, 4.4) if movil else (8.5, 3.2), dpi=100)
    g.dibujar_comparacion(fig, c["resultado_a"], c["resultado_b"], _tema(oscuro))
    return _svg(fig)


def exportar(ext: str) -> str:
    """Escribe el último resultado en /tmp con el formato pedido. Devuelve {"ok", "valor": ruta}."""
    try:
        if not _ultimo:
            raise ValueError("Aún no hay resultados para exportar.")
        if ext not in FORMATOS:
            raise ValueError("Formato no disponible.")
        from src.infraestructura import exportador
        ruta = f"/tmp/pronostico_siembra{ext}"
        exportador.exportar(ruta, _ultimo)
        return _ok(ruta)
    except ValueError as exc:
        return _error(str(exc))
    except Exception as exc:
        return _error(f"No se pudo exportar: {exc}")


# ------------------------------------------------------------------ asistente
@_seguro
def preguntar(texto: str, pagina: str = "inicio") -> Dict[str, Any]:
    return asistente.responder(texto, {"pagina": pagina, "resultado": _ultimo})
