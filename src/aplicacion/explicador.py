"""Redacta en lenguaje cotidiano la recomendación y compara fechas (sin lógica numérica propia)."""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Tuple

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]
ETIQUETA_VARIABLE = {"agua": "el agua", "temperatura": "la temperatura", "humedad": "la humedad",
                     "ph": "el pH del suelo", "nutrientes": "los nutrientes"}
ETIQUETA_EVENTO = {"plagas": "las plagas", "heladas": "las heladas", "lluvias_intensas": "las lluvias intensas"}


def fecha_larga(d: date) -> str:
    """15 de abril de 2027."""
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def fecha_corta(d: date) -> str:
    """15 de abril."""
    return f"{d.day} de {MESES[d.month - 1]}"


def construir_comparaciones(registros: Dict[date, Dict[str, float]], fecha_opt: date, fecha0: date,
                            hoy: date, paso: int) -> List[Dict[str, Any]]:
    """Compara la fecha óptima con «sembrar hoy» (la fecha inicial) y con «sembrar en 30 días»."""
    def item(etiqueta: str, f: date, optima: bool = False) -> Dict[str, Any]:
        r = registros[f]
        base = registros[fecha_opt]["kpi"]
        dif = None if optima or r["kpi"] <= 0 else (base - r["kpi"]) / r["kpi"] * 100.0
        return {"etiqueta": etiqueta, "fecha": f.isoformat(), "kpi": r["kpi"],
                "probabilidad_exito": r["probabilidad_exito"], "optima": optima, "ventaja_pct": dif}

    salida = [item("Fecha óptima", fecha_opt, True)]
    if fecha0 != fecha_opt:
        salida.append(item("Sembrar hoy" if fecha0 == hoy else f"Sembrar el {fecha_corta(fecha0)}", fecha0))
    objetivo = date.fromordinal(fecha0.toordinal() + 30)
    candidatas = [f for f in registros if f not in (fecha0, fecha_opt)]
    if candidatas:
        cercana = min(candidatas, key=lambda f: abs((f - objetivo).days))
        if abs((cercana - objetivo).days) <= max(paso, 15):
            salida.append(item("Sembrar en 30 días", cercana))
    return salida


def justificar(cultivo: Any, fecha_opt: date, reg: Dict[str, float], registros: Dict[date, Dict[str, float]],
               pesos: Dict[str, float], comparaciones: List[Dict[str, Any]], riesgos: List[Dict[str, Any]],
               viable: bool, riego: float) -> Tuple[str, List[str]]:
    """Devuelve (párrafo breve, lista de razones de detalle) que justifican la recomendación."""
    prob = reg["probabilidad_exito"] * 100
    if not viable:
        mejor = max(r["probabilidad_exito"] for r in registros.values()) * 100
        return (f"No encontré una fecha segura para sembrar {cultivo.nombre.lower()}: en el mejor caso la "
                f"probabilidad de éxito es de solo {mejor:.0f} %. Prueba con otra ventana de fechas, otro cultivo "
                f"o más riego.",
                ["Las condiciones de clima esperadas quedan fuera del rango que tolera el cultivo."])
    agua_total = reg["lluvia_media"] + riego
    if agua_total >= 0.9 * cultivo.requerimiento_agua:
        agua = "el agua disponible alcanza para lo que necesita la planta"
    elif agua_total >= 0.6 * cultivo.requerimiento_agua:
        agua = "el agua alcanza a medias; conviene reforzar el riego"
    else:
        agua = "el agua escasea; conviene regar más"
    parrafo = (f"Se recomienda sembrar el {fecha_corta(fecha_opt)} porque en esa fecha la temperatura media esperada "
               f"es de {reg['temperatura_media']:.0f} °C (el cultivo tolera de {cultivo.temp_min:g} a "
               f"{cultivo.temp_max:g} °C) y {agua}. Hay {prob:.0f} % de probabilidad de éxito y se espera una "
               f"cosecha de entre {reg['rendimiento_p10']:.1f} y {reg['rendimiento_p90']:.1f} t/ha "
               f"(80 % de confianza).")
    for c in comparaciones[1:]:
        if c["ventaja_pct"] is None or c["ventaja_pct"] < 1:
            continue
        parrafo += f" Es {c['ventaja_pct']:.0f} % mejor que «{c['etiqueta'].lower()}»."
        break
    detalle: List[str] = []
    claves = {"agua": "p_agua", "temperatura": "p_temperatura", "humedad": "p_humedad", "ph": "p_ph",
              "nutrientes": "p_nutrientes"}
    for var in sorted(pesos, key=lambda v: -pesos[v])[:2]:
        if pesos[var] <= 0 or var not in claves:
            continue
        detalle.append(f"Lo que más pesa en tu configuración es {ETIQUETA_VARIABLE.get(var, var)} "
                       f"(peso {pesos[var]:.0f}): en esta fecha queda cubierto al {reg[claves[var]] * 100:.0f} %.")
    otras = [r["p_temperatura"] for f, r in registros.items() if f != fecha_opt]
    if otras and reg["p_temperatura"] >= max(otras):
        detalle.append("Es la fecha con la temperatura más cercana al rango ideal entre todas las probadas.")
    if riesgos:
        mayor = max(riesgos, key=lambda r: r["perdida_esperada"])
        if mayor["perdida_esperada"] > 0:
            detalle.append(f"El mayor riesgo son {ETIQUETA_EVENTO.get(mayor['clave'], mayor['etiqueta'].lower())}: "
                           f"se espera perder cerca de {mayor['perdida_esperada'] * 100:.0f} % de la cosecha por "
                           f"esa causa.")
    return parrafo, detalle
