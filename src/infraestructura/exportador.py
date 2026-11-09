"""Exportación de resultados: PDF (informe), Excel, CSV, JSON y PNG (gráficas)."""
from __future__ import annotations

import csv
import json
import os
import textwrap
from typing import Any, Dict, List

from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure

from src.aplicacion.explicador import fecha_larga
from src.infraestructura import graficas as g

FORMATOS = {".pdf": "Informe PDF", ".xlsx": "Excel", ".csv": "CSV (datos por fecha)", ".json": "JSON (resultados)",
            ".png": "PNG (gráficas)"}
AVISO = ("Las recomendaciones de esta herramienta son informativas y no reemplazan el juicio de un profesional. "
         "En agricultura real, consulta a un agrónomo antes de decidir.")


def exportar(ruta: str, r: Dict[str, Any]) -> None:
    """Exporta según la extensión de `ruta`. Lanza ValueError si el formato no existe."""
    ext = os.path.splitext(ruta)[1].lower()
    {".pdf": exportar_pdf, ".xlsx": exportar_excel, ".csv": exportar_csv, ".json": exportar_json,
     ".png": exportar_png}.get(ext, _desconocido)(ruta, r)


def _desconocido(ruta: str, r: Dict[str, Any]) -> None:
    raise ValueError("Formato no soportado. Elige PDF, Excel, CSV, JSON o PNG.")


def exportar_json(ruta: str, r: Dict[str, Any]) -> None:
    """Resultados crudos, compatibles con una futura importación."""
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False, indent=2)


def exportar_csv(ruta: str, r: Dict[str, Any]) -> None:
    """Tabla de rendimientos por fecha (una fila por fecha candidata)."""
    filas = r["resultados_por_fecha"]
    columnas = ["fecha"] + list(next(iter(filas.values())).keys())
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(columnas)
        for fecha, reg in filas.items():
            w.writerow([fecha] + [reg[c] for c in columnas[1:]])


def exportar_excel(ruta: str, r: Dict[str, Any]) -> None:
    """Libro con hojas Resumen, Por fecha, Temporadas y Riesgos."""
    from openpyxl import Workbook
    from openpyxl.styles import Font
    libro = Workbook()
    hoja = libro.active
    hoja.title = "Resumen"
    fo, k, est = r["fecha_optima"], r["kpi"], r["estadisticas_rendimiento"]
    for fila in [("Simulación", r.get("nombre", "")), ("Cultivo", r.get("cultivo", "")), ("Fecha óptima", fo["fecha"]),
                 ("KPI", round(k["valor"], 3)), ("Probabilidad de éxito (%)", round(fo["probabilidad_exito"] * 100, 1)),
                 ("Rendimiento P10 (t/ha)", round(est["p10"], 2)), ("Rendimiento promedio (t/ha)", round(est["media"], 2)),
                 ("Rendimiento P90 (t/ha)", round(est["p90"], 2)), ("Justificación", r.get("justificacion", "")),
                 ("Aviso", AVISO)]:
        hoja.append(fila)
    for c in hoja["A"]:
        c.font = Font(bold=True)
    hoja.column_dimensions["A"].width = 30
    hoja.column_dimensions["B"].width = 90
    por_fecha = libro.create_sheet("Por fecha")
    filas = r["resultados_por_fecha"]
    columnas = list(next(iter(filas.values())).keys())
    por_fecha.append(["fecha"] + columnas)
    for fecha, reg in filas.items():
        por_fecha.append([fecha] + [reg[c] for c in columnas])
    plan = r.get("plan_temporadas", {})
    if plan.get("filas"):
        t = libro.create_sheet("Temporadas")
        t.append(["Temporada", "Fecha de siembra", "Plantas esperadas", "Media de descendientes", "Cosecha estimada (t/ha)",
                  "Semillas a guardar"])
        for f in plan["filas"]:
            t.append([f["temporada"], f["fecha_siembra"], round(f["poblacion_esperada"], 1), round(f["media_descendientes"], 3),
                      round(f["cosecha_estimada"], 2), f["semillas_guardar"]])
    if r.get("riesgos"):
        rs = libro.create_sheet("Riesgos")
        rs.append(["Evento", "Tasa mensual", "P(0 eventos)", "P(1)", "P(2)", "P(3 o más)", "Pérdida esperada (%)"])
        for x in r["riesgos"]:
            p = x["probabilidades"]
            rs.append([x["etiqueta"], x["tasa_mensual"], round(p["0"], 4), round(p["1"], 4), round(p["2"], 4),
                       round(p["3+"], 4), round(x["perdida_esperada"] * 100, 1)])
    libro.save(ruta)


def exportar_png(ruta: str, r: Dict[str, Any]) -> None:
    """Todas las gráficas en una sola imagen vertical."""
    dibujos = [d for _, d in g.GRAFICAS if d is not g.dibujar_poblacion or r.get("plan_temporadas")]
    fig = Figure(figsize=(9, 4.2 * len(dibujos)), dpi=110)
    fig.patch.set_facecolor(g.TEMA_CLARO["fondo"])
    # Cada gráfica se dibuja en su propia figura y se pega como imagen para poder reutilizar las mismas funciones.
    import io
    import matplotlib.image as mpimg
    ejes = fig.subplots(len(dibujos), 1)
    ejes = [ejes] if len(dibujos) == 1 else list(ejes)
    for ax, dibujar in zip(ejes, dibujos):
        sub = Figure(figsize=(9, 4.2), dpi=110)
        dibujar(sub, r, g.TEMA_CLARO)
        buf = io.BytesIO()
        sub.savefig(buf, format="png", facecolor=sub.get_facecolor())
        buf.seek(0)
        ax.imshow(mpimg.imread(buf))
        ax.axis("off")
    fig.tight_layout(pad=0.5)
    fig.savefig(ruta, facecolor=fig.get_facecolor())


def _texto_pagina(fig: Figure, y: float, texto: str, tam: float = 10.5, ancho: int = 92, **kw) -> float:
    """Escribe texto ajustado al ancho y devuelve la siguiente posición vertical."""
    for linea in textwrap.wrap(texto, ancho) or [""]:
        fig.text(0.09, y, linea, fontsize=tam, color=g.TEMA_CLARO["texto"], va="top", **kw)
        y -= tam * 0.0021 * 1.55
    return y


def exportar_pdf(ruta: str, r: Dict[str, Any]) -> None:
    """Informe: portada, resumen con justificación, gráficas y plan de temporadas."""
    import matplotlib
    matplotlib.rcParams["font.family"] = g.familia_tipografica()
    t = g.TEMA_CLARO
    fo, est = r["fecha_optima"], r["estadisticas_rendimiento"]
    with PdfPages(ruta) as pdf:
        # Portada
        f = Figure(figsize=(8.27, 11.69))
        f.text(0.09, 0.72, "Pronóstico de siembra", fontsize=30, fontweight="bold", color=t["texto"])
        f.text(0.09, 0.67, r.get("nombre", ""), fontsize=15, color=t["suave"])
        f.text(0.09, 0.62, f"Cultivo: {r.get('cultivo', '')}", fontsize=12, color=t["texto"])
        f.text(0.09, 0.59, f"Fecha recomendada: {fecha_larga(__import__('datetime').date.fromisoformat(fo['fecha']))}",
               fontsize=12, color=t["texto"])
        _texto_pagina(f, 0.08, AVISO, 8.5, 110)
        pdf.savefig(f)
        # Resumen
        f = Figure(figsize=(8.27, 11.69))
        f.text(0.09, 0.93, "Resumen de la recomendación", fontsize=18, fontweight="bold", color=t["texto"])
        y = 0.88
        for etiqueta, valor in (("Fecha óptima", fecha_larga(__import__("datetime").date.fromisoformat(fo["fecha"]))),
                                ("KPI esperado", f"{fo['kpi']:.2f}"),
                                ("Probabilidad de éxito", f"{fo['probabilidad_exito'] * 100:.0f} %"),
                                ("Cosecha esperada (80 % de confianza)", f"entre {est['p10']:.1f} y {est['p90']:.1f} t/ha")):
            f.text(0.09, y, etiqueta, fontsize=10.5, color=t["suave"])
            f.text(0.55, y, valor, fontsize=12, fontweight="bold", color=t["texto"])
            y -= 0.035
        y = _texto_pagina(f, y - 0.02, r.get("justificacion", ""), 11)
        for d in r.get("justificacion_detalle", []):
            y = _texto_pagina(f, y - 0.008, "• " + d, 10)
        if r.get("comparaciones"):
            y -= 0.03
            f.text(0.09, y, "Comparación con otras fechas", fontsize=13, fontweight="bold", color=t["texto"])
            y -= 0.032
            for c in r["comparaciones"]:
                extra = "" if c["ventaja_pct"] is None else f"  (la óptima es {c['ventaja_pct']:.0f} % mejor)"
                f.text(0.09, y, f"{c['etiqueta']}: {c['fecha']}  KPI {c['kpi']:.2f}  éxito {c['probabilidad_exito'] * 100:.0f} %{extra}",
                       fontsize=10, color=t["texto"])
                y -= 0.026
        if r.get("riesgos"):
            y -= 0.03
            f.text(0.09, y, "Riesgos identificados", fontsize=13, fontweight="bold", color=t["texto"])
            y -= 0.032
            for x in r["riesgos"]:
                p = x["probabilidades"]
                f.text(0.09, y, f"{x['etiqueta']}: ninguno {p['0'] * 100:.0f} %, 1 vez {p['1'] * 100:.0f} %, 2 veces "
                                f"{p['2'] * 100:.0f} %, 3 o más {p['3+'] * 100:.0f} %; pérdida esperada {x['perdida_esperada'] * 100:.0f} %",
                       fontsize=9.5, color=t["texto"])
                y -= 0.026
        pdf.savefig(f)
        # Gráficas (dos por página)
        dibujos = [d for _, d in g.GRAFICAS if d is not g.dibujar_poblacion or r.get("plan_temporadas")]
        for i in range(0, len(dibujos), 2):
            f = Figure(figsize=(8.27, 11.69))
            for k, dibujar in enumerate(dibujos[i:i + 2]):
                sub = Figure(figsize=(8, 5))
                dibujar(sub, r, t)
                import io
                import matplotlib.image as mpimg
                buf = io.BytesIO()
                sub.savefig(buf, format="png", dpi=130, facecolor=t["fondo"])
                buf.seek(0)
                ax = f.add_axes([0.04, 0.52 - k * 0.47, 0.92, 0.44])
                ax.imshow(mpimg.imread(buf))
                ax.axis("off")
            pdf.savefig(f)
        # Plan de temporadas
        plan = r.get("plan_temporadas", {})
        if plan.get("filas"):
            f = Figure(figsize=(8.27, 11.69))
            f.text(0.09, 0.93, "Plan de temporadas", fontsize=18, fontweight="bold", color=t["texto"])
            y = _texto_pagina(f, 0.89, plan["recomendacion"], 11)
            y -= 0.03
            f.text(0.09, y, f"Probabilidad de extinción a largo plazo: {plan['prob_extincion_largo_plazo'] * 100:.1f} %", fontsize=10.5,
                   color=t["texto"])
            y -= 0.045
            for cab, x in zip(("Temporada", "Siembra", "Plantas", "Cosecha (t/ha)", "Semillas a guardar"), (0.09, 0.24, 0.43, 0.58, 0.78)):
                f.text(x, y, cab, fontsize=10, fontweight="bold", color=t["texto"])
            y -= 0.03
            for fila in plan["filas"]:
                for val, x in zip((fila["temporada"], fila["fecha_siembra"], f"{fila['poblacion_esperada']:.0f}",
                                   f"{fila['cosecha_estimada']:.2f}", fila["semillas_guardar"]), (0.09, 0.24, 0.43, 0.58, 0.78)):
                    f.text(x, y, str(val), fontsize=10, color=t["texto"])
                y -= 0.026
            pdf.savefig(f)
