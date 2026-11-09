"""Gráficas de resultados con matplotlib (sin dependencia de Tkinter): se usan en pantalla y al exportar.

Cada función `dibujar_*(fig, resultado, tema)` limpia la figura y la dibuja. Los textos están en español y cada
gráfica lleva título, ejes rotulados y leyenda. Colores de series: primeros tres puestos de la paleta validada
(azul, naranja, aguamarina) y un cuarto para el caso de cuatro categorías.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List

import matplotlib
from matplotlib import font_manager
from matplotlib.figure import Figure

TEMA_CLARO: Dict[str, Any] = {
    "fondo": "#ffffff", "texto": "#1c2421", "suave": "#5b6661", "rejilla": "#e6eae7", "eje": "#c9d0cc",
    "series": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"], "banda": "#2a78d6", "alerta": "#d03b3b"}
TEMA_OSCURO: Dict[str, Any] = {
    "fondo": "#17211d", "texto": "#eef2ef", "suave": "#a9b4ae", "rejilla": "#26332d", "eje": "#3a4a43",
    "series": ["#3987e5", "#d95926", "#199e70", "#c98500"], "banda": "#3987e5", "alerta": "#e66767"}


def familia_tipografica() -> str:
    """Primera tipografía moderna instalada (para que las gráficas combinen con la interfaz)."""
    instaladas = {f.name for f in font_manager.fontManager.ttflist}
    for nombre in ("Inter", "Segoe UI Variable", "Segoe UI", "SF Pro Text", "Helvetica Neue", "Ubuntu", "DejaVu Sans"):
        if nombre in instaladas:
            return nombre
    return "sans-serif"


def _estilo(ax, t: Dict[str, Any], titulo: str, xlabel: str, ylabel: str) -> None:
    """Ejes discretos: sin marco superior/derecho, rejilla tenue, texto en tonos de tinta."""
    ax.set_facecolor(t["fondo"])
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(t["eje"])
    ax.tick_params(colors=t["suave"], labelsize=9, length=0)
    ax.grid(axis="y", color=t["rejilla"], linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_title(titulo, loc="left", fontsize=12, fontweight="semibold", color=t["texto"], pad=14)
    ax.set_xlabel(xlabel, color=t["suave"], fontsize=9.5, labelpad=8)
    ax.set_ylabel(ylabel, color=t["suave"], fontsize=9.5, labelpad=8)


def _leyenda(ax, t: Dict[str, Any], **kw) -> None:
    kw.setdefault("fontsize", 8.5)
    leg = ax.legend(frameon=False, labelcolor=t["suave"], **kw)
    if leg:
        leg.set_zorder(5)


def _nueva(fig: Figure, t: Dict[str, Any]) -> None:
    fig.clear()
    fig.patch.set_facecolor(t["fondo"])
    matplotlib.rcParams["font.family"] = familia_tipografica()


def dibujar_histograma(fig: Figure, r: Dict[str, Any], t: Dict[str, Any] = TEMA_CLARO) -> None:
    """Distribución del rendimiento en la fecha óptima, con el rango del 80 % de los casos sombreado."""
    _nueva(fig, t)
    ax = fig.add_subplot(111)
    h, st = r["histograma_rendimiento"], r["estadisticas_rendimiento"]
    b = h["bordes"]
    ancho = (b[1] - b[0])
    ax.bar([(b[i] + b[i + 1]) / 2 for i in range(len(h["conteos"]))], h["conteos"], width=ancho * 0.88,
           color=t["series"][0], label="Escenarios simulados", zorder=3)
    ax.axvspan(st["p10"], st["p90"], color=t["banda"], alpha=0.10, zorder=1, label="80 % de los casos")
    ax.axvline(st["media"], color=t["series"][1], linewidth=2, zorder=4, label=f"Promedio: {st['media']:.2f} t/ha")
    _estilo(ax, t, "¿Cuánto podría cosechar?", "Rendimiento (toneladas por hectárea)", "Cantidad de escenarios")
    _leyenda(ax, t, loc="upper right")
    fig.tight_layout()


def dibujar_probabilidad(fig: Figure, r: Dict[str, Any], t: Dict[str, Any] = TEMA_CLARO) -> None:
    """Probabilidad de éxito para cada fecha de siembra probada."""
    _nueva(fig, t)
    ax = fig.add_subplot(111)
    fechas = [date.fromisoformat(f) for f in r["resultados_por_fecha"]]
    prob = [v["probabilidad_exito"] * 100 for v in r["resultados_por_fecha"].values()]
    ax.plot(fechas, prob, color=t["series"][0], linewidth=2, marker="o", markersize=4, label="Probabilidad de éxito", zorder=3)
    opt = date.fromisoformat(r["fecha_optima"]["fecha"])
    ax.axvline(opt, color=t["series"][1], linestyle="--", linewidth=1.6, zorder=2, label=f"Fecha óptima: {opt:%d/%m/%Y}")
    ax.scatter([opt], [r["fecha_optima"]["probabilidad_exito"] * 100], s=70, color=t["series"][1], edgecolor=t["fondo"],
               linewidth=2, zorder=5)
    _estilo(ax, t, "¿Qué tan seguro es cada día de siembra?", "Fecha de siembra", "Probabilidad de éxito (%)")
    ax.set_ylim(-3, 105)
    ax.tick_params(axis="x", rotation=25)
    _leyenda(ax, t, loc="lower right")
    fig.tight_layout()


def dibujar_estados(fig: Figure, r: Dict[str, Any], t: Dict[str, Any] = TEMA_CLARO) -> None:
    """Evolución semanal de la planta: un panel por cadena de Márkov (salud, enfermedad, crecimiento)."""
    _nueva(fig, t)
    titulos = {"salud": "Salud de la planta", "enfermedad": "Enfermedad", "crecimiento": "Crecimiento"}
    cadenas = list(r["evolucion_estados"].items())
    ejes = fig.subplots(1, max(1, len(cadenas)), sharey=True)
    ejes = [ejes] if len(cadenas) <= 1 else list(ejes)
    for i, (ax, (nombre, estados)) in enumerate(zip(ejes, cadenas)):
        for j, (est, serie) in enumerate(estados.items()):
            ax.plot(range(len(serie)), [v * 100 for v in serie], color=t["series"][j % 4], linewidth=2, label=est)
        _estilo(ax, t, titulos.get(nombre, nombre.capitalize()), "Semana", "Probabilidad (%)" if i == 0 else "")
        _leyenda(ax, t, loc="center right", fontsize=8)
        ax.set_ylim(-2, 102)
    fig.tight_layout()


def dibujar_riesgos(fig: Figure, r: Dict[str, Any], t: Dict[str, Any] = TEMA_CLARO) -> None:
    """Probabilidad de que ocurran 0, 1, 2 o más eventos raros durante el ciclo (Poisson)."""
    _nueva(fig, t)
    ax = fig.add_subplot(111)
    riesgos: List[Dict[str, Any]] = r.get("riesgos", [])
    if not riesgos:
        ax.text(0.5, 0.5, "No hay eventos raros configurados.", ha="center", color=t["suave"], transform=ax.transAxes)
        ax.axis("off")
        return
    claves = list(riesgos[0]["probabilidades"].keys())
    etiquetas = {"0": "Ninguno", "1": "1 vez", "2": "2 veces"}
    ancho = 0.8 / len(claves)
    for j, k in enumerate(claves):
        xs = [i + (j - (len(claves) - 1) / 2) * ancho for i in range(len(riesgos))]
        ax.bar(xs, [x["probabilidades"][k] * 100 for x in riesgos], width=ancho * 0.9, color=t["series"][j % 4],
               label=etiquetas.get(k, "3 o más veces"), zorder=3)
    ax.set_xticks(range(len(riesgos)))
    ax.set_xticklabels([x["etiqueta"] for x in riesgos])
    _estilo(ax, t, "¿Con qué frecuencia podría pasar?", "Evento durante el ciclo del cultivo", "Probabilidad (%)")
    _leyenda(ax, t, loc="upper right", title="Ocurrencias", title_fontsize=8.5)
    fig.tight_layout()


def dibujar_poblacion(fig: Figure, r: Dict[str, Any], t: Dict[str, Any] = TEMA_CLARO) -> None:
    """Población de plantas a lo largo de las temporadas (Galton-Watson), con banda del 80 % y capacidad del terreno."""
    _nueva(fig, t)
    ax = fig.add_subplot(111)
    plan = r["plan_temporadas"]
    tr = plan["trayectoria"]
    xs = list(range(len(tr["media"])))
    ax.fill_between(xs, tr["p10"], tr["p90"], color=t["banda"], alpha=0.15, label="80 % de los casos", linewidth=0)
    ax.plot(xs, tr["media"], color=t["series"][0], linewidth=2.2, marker="o", markersize=4, label="Población esperada")
    ax.axhline(plan["capacidad"], color=t["suave"], linestyle=":", linewidth=1.4, label="Capacidad del terreno")
    _estilo(ax, t, "¿Se sostiene el cultivo?", "Temporada (0 = siembra inicial)", "Plantas")
    ax.set_xticks(xs)
    _leyenda(ax, t, loc="best")
    fig.tight_layout()


def dibujar_comparacion(fig: Figure, ra: Dict[str, Any], rb: Dict[str, Any], t: Dict[str, Any] = TEMA_CLARO) -> None:
    """Dos simulaciones lado a lado: KPI y probabilidad de éxito."""
    _nueva(fig, t)
    ejes = fig.subplots(1, 2)
    nombres = [ra.get("nombre") or "A", rb.get("nombre") or "B"]
    datos = [("KPI esperado", [ra["kpi"]["valor"], rb["kpi"]["valor"]], "KPI"),
             ("Probabilidad de éxito", [ra["fecha_optima"]["probabilidad_exito"] * 100,
                                        rb["fecha_optima"]["probabilidad_exito"] * 100], "Probabilidad (%)")]
    for ax, (titulo, vals, ylab) in zip(ejes, datos):
        for i, (n, v) in enumerate(zip(nombres, vals)):
            ax.bar([i], [v], width=0.55, color=t["series"][i], label=n, zorder=3)
            ax.text(i, v, f"{v:.1f}", ha="center", va="bottom", fontsize=9.5, color=t["texto"])
        _estilo(ax, t, titulo, "", ylab)
        ax.set_xticks([])
        _leyenda(ax, t, loc="upper right", fontsize=8)
    fig.tight_layout()


GRAFICAS = (("Rendimiento", dibujar_histograma), ("Fechas", dibujar_probabilidad), ("Estados", dibujar_estados),
            ("Riesgos", dibujar_riesgos), ("Temporadas", dibujar_poblacion))
