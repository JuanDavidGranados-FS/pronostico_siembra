"""Gestión del historial de simulaciones."""
from __future__ import annotations

import logging
import unicodedata
from typing import Any, Dict, List, Optional

from src.dominio.interfaces import RepositorioHistorial

log = logging.getLogger(__name__)


def _sin_tildes(texto: str) -> str:
    return unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode().lower()


class GestorHistorial:
    """Guarda, lista (con filtros), recupera, renombra y compara simulaciones."""

    def __init__(self, repo: RepositorioHistorial) -> None:
        """Recibe el repositorio de historial."""
        self.repo = repo

    def guardar(self, resultado: Dict[str, Any], configuracion_id: Optional[int] = None, nombre: str = "") -> int:
        """Guarda un resultado (diccionario) y devuelve su id."""
        return self.repo.guardar(resultado, configuracion_id, nombre)

    def listar(self, limite: int = 200, texto: str = "", desde: str = "", hasta: str = "") -> List[Dict[str, Any]]:
        """Lista las simulaciones recientes; filtra por nombre (sin distinguir tildes) y por fecha de ejecución
        (AAAA-MM-DD, ambos extremos incluidos). Devuelve [] si el repositorio falla."""
        try:
            filas = self.repo.listar(limite)
        except Exception:
            log.exception("No se pudo listar el historial")
            return []
        t = _sin_tildes(texto.strip())
        salida = []
        for f in filas:
            dia = str(f.get("fecha_ejecucion", ""))[:10]
            if t and t not in _sin_tildes(f.get("nombre", "")):
                continue
            if desde and dia < desde:
                continue
            if hasta and dia > hasta:
                continue
            salida.append(f)
        return salida

    def obtener(self, id_sim: int) -> Optional[Dict[str, Any]]:
        """Obtiene una simulación por id."""
        return self.repo.obtener(id_sim)

    def renombrar(self, id_sim: int, nombre: str) -> bool:
        """Cambia el nombre de una simulación guardada."""
        if not nombre.strip():
            raise ValueError("El nombre no puede estar vacío.")
        return self.repo.renombrar(id_sim, nombre.strip())

    def eliminar(self, id_sim: int) -> bool:
        """Borra una simulación del historial."""
        return self.repo.eliminar(id_sim)

    def comparar(self, ids: List[int]) -> List[Dict[str, Any]]:
        """Compara simulaciones: fecha óptima, KPI, probabilidad y diferencias respecto a la primera."""
        filas = []
        for i in ids:
            sim = self.repo.obtener(i)
            if sim is None:
                raise ValueError(f"No existe la simulación {i}.")
            r = sim["resultado_completo"]
            filas.append({"id": i, "fecha_optima": r["fecha_optima"]["fecha"], "kpi": r["kpi"]["valor"],
                          "probabilidad_exito": r["fecha_optima"]["probabilidad_exito"]})
        if filas:
            base = filas[0]
            for f in filas:
                f["dif_kpi"] = f["kpi"] - base["kpi"]
                f["dif_probabilidad"] = f["probabilidad_exito"] - base["probabilidad_exito"]
        return filas

    def comparar_detallado(self, id_a: int, id_b: int) -> Dict[str, Any]:
        """Vista paralela de dos simulaciones: resúmenes, mejor opción según KPI y diferencias en lenguaje cotidiano."""
        sims = []
        for i in (id_a, id_b):
            s = self.repo.obtener(i)
            if s is None:
                raise ValueError(f"No existe la simulación {i}.")
            sims.append(s)
        ra, rb = sims[0]["resultado_completo"], sims[1]["resultado_completo"]

        def resumen(i: int, s: Dict[str, Any], r: Dict[str, Any]) -> Dict[str, Any]:
            est = r["estadisticas_rendimiento"]
            return {"id": i, "nombre": r.get("nombre") or s.get("nombre") or f"Simulación {i}", "cultivo": r.get("cultivo", ""),
                    "fecha_optima": r["fecha_optima"]["fecha"], "kpi": r["kpi"]["valor"],
                    "probabilidad_exito": r["fecha_optima"]["probabilidad_exito"], "p10": est["p10"], "p90": est["p90"]}

        a, b = resumen(id_a, sims[0], ra), resumen(id_b, sims[1], rb)
        mejor = "a" if a["kpi"] > b["kpi"] else "b" if b["kpi"] > a["kpi"] else "empate"
        dif: List[str] = []
        if a["cultivo"] and b["cultivo"] and a["cultivo"] != b["cultivo"]:
            dif.append(f"Cambia el cultivo: {a['cultivo']} → {b['cultivo']}.")
        if a["fecha_optima"] != b["fecha_optima"]:
            dias = (_a_fecha(b["fecha_optima"]) - _a_fecha(a["fecha_optima"])).days
            dif.append(f"La fecha óptima pasa del {a['fecha_optima']} al {b['fecha_optima']} "
                       f"({abs(dias)} días {'después' if dias > 0 else 'antes'}).")
        else:
            dif.append("Las dos recomiendan la misma fecha de siembra.")
        if a["kpi"] > 0:
            pct = (b["kpi"] - a["kpi"]) / a["kpi"] * 100
            dif.append(f"El KPI de «{b['nombre']}» es {abs(pct):.0f} % {'mayor' if pct >= 0 else 'menor'} que el de «{a['nombre']}».")
        dif.append(f"Probabilidad de éxito: {a['probabilidad_exito'] * 100:.0f} % frente a {b['probabilidad_exito'] * 100:.0f} %.")
        pa, pb = ra.get("pesos", {}), rb.get("pesos", {})
        for v in sorted(set(pa) | set(pb)):
            if abs(pa.get(v, 0) - pb.get(v, 0)) >= 10:
                dif.append(f"El peso de {v} cambia de {pa.get(v, 0):.0f} a {pb.get(v, 0):.0f}.")
        ganador = {"a": a["nombre"], "b": b["nombre"]}.get(mejor)
        cierre = f"La mejor opción según el KPI es «{ganador}»." if ganador else "Las dos opciones tienen el mismo KPI."
        return {"a": a, "b": b, "mejor": mejor, "diferencias": dif, "resumen": " ".join(dif[:2]) + " " + cierre,
                "resultado_a": ra, "resultado_b": rb}


def _a_fecha(texto: str):
    from datetime import date
    return date.fromisoformat(texto)
