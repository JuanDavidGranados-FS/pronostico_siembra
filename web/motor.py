"""Puente entre la versión web (JavaScript + Pyodide) y el motor de simulación en Python.

Corre dentro del navegador. Reutiliza sin cambios `src/dominio` y `src/aplicacion`: la web solo arma los datos de
entrada, llama al orquestador y devuelve el resultado como JSON. No usa base de datos (nada sale del dispositivo).
"""
from __future__ import annotations

import json
from datetime import date
from typing import Any, Callable, Dict, Optional

from src.aplicacion import asistente
from src.aplicacion.explicador import fecha_larga
from src.aplicacion.orquestador import OrquestadorSimulacion
from src.aplicacion.validador import ErrorValidacion
from src.dominio.entidades import CULTIVOS_POR_DEFECTO, Cultivo, datos_por_defecto

_orquestador = OrquestadorSimulacion()  # sin repositorios: no guarda nada
_ultimo: Optional[Dict[str, Any]] = None


def catalogo() -> str:
    """Cultivos disponibles y valores sugeridos para llenar el formulario."""
    d = datos_por_defecto()
    cultivos = [Cultivo.desde_dict(c).a_dict() for c in CULTIVOS_POR_DEFECTO]
    return json.dumps({
        "cultivos": cultivos,
        "deterministas": d.deterministas,
        "clima": {k: v["parametros"] for k, v in d.estocasticos.items()},
        "pesos": d.pesos,
        "iteraciones": d.iteraciones,
        "temporadas": d.plan["temporadas"],
        "hoy": date.today().isoformat(),
    }, ensure_ascii=False)


def _numero(v: Any, defecto: float) -> float:
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return defecto


def _armar_datos(entrada: Dict[str, Any]):
    """Convierte lo que envía el formulario web en `DatosEntrada`, completando con los valores sugeridos."""
    d = datos_por_defecto()
    c = entrada.get("cultivo") or {}
    base = next((x for x in CULTIVOS_POR_DEFECTO if x["nombre"] == c.get("nombre")), CULTIVOS_POR_DEFECTO[0])
    cultivo = Cultivo.desde_dict(base)
    for campo in ("dias_crecimiento", "temp_min", "temp_max", "requerimiento_agua", "resistencia_plagas", "rendimiento_base"):
        if campo in c:
            setattr(cultivo, campo, type(getattr(cultivo, campo))(_numero(c[campo], getattr(cultivo, campo))))
    d.cultivo = cultivo
    for k, v in (entrada.get("deterministas") or {}).items():
        if k in d.deterministas:
            d.deterministas[k] = v if k == "fecha" else _numero(v, d.deterministas[k])
    for var, params in (entrada.get("clima") or {}).items():
        if var in d.estocasticos:
            actual = d.estocasticos[var]["parametros"]
            for p, v in params.items():
                if p in actual:
                    actual[p] = _numero(v, actual[p])
    for k, v in (entrada.get("pesos") or {}).items():
        if k in d.pesos:
            d.pesos[k] = max(0.0, min(100.0, _numero(v, d.pesos[k])))
    d.iteraciones = int(max(200, min(20000, _numero(entrada.get("iteraciones"), 5000))))
    d.plan["temporadas"] = int(max(1, min(10, _numero(entrada.get("temporadas"), 1))))
    d.semilla = None
    d.nombre = f"Simulación web · {cultivo.nombre}"
    return d


def simular(entrada_json: str, progreso: Optional[Callable[[int, int], None]] = None) -> str:
    """Ejecuta la simulación. Devuelve JSON con {"ok": True, "resultado": …} o {"ok": False, "errores": […]}."""
    global _ultimo
    try:
        datos = _armar_datos(json.loads(entrada_json))
        r = _orquestador.ejecutar_simulacion(datos, (lambda i, n: progreso(i, n)) if progreso else None).a_dict()
    except ErrorValidacion as exc:
        return json.dumps({"ok": False, "errores": list(exc.errores)}, ensure_ascii=False)
    except Exception as exc:  # nunca dejar la página sin respuesta
        return json.dumps({"ok": False, "errores": [f"No se pudo completar la simulación: {exc}"]}, ensure_ascii=False)
    # Textos listos para mostrar
    r["fecha_optima"]["fecha_larga"] = fecha_larga(date.fromisoformat(r["fecha_optima"]["fecha"]))
    for x in r.get("comparaciones", []):
        x["fecha_larga"] = fecha_larga(date.fromisoformat(x["fecha"]))
    _ultimo = r
    return json.dumps({"ok": True, "resultado": r}, ensure_ascii=False, default=str)


def preguntar(texto: str) -> str:
    """Asistente sin internet: responde sobre conceptos y sobre el último resultado."""
    r = asistente.responder(texto, {"pagina": "resultados" if _ultimo else "inicio", "resultado": _ultimo})
    return json.dumps(r, ensure_ascii=False, default=str)


def sugerencias_iniciales() -> str:
    return json.dumps(list(asistente.SUGERENCIAS_INICIALES), ensure_ascii=False)
