"""Gestión del Factor de Relevancia: cálculo por 4 métodos y perfiles guardables/compartibles."""
from __future__ import annotations

import copy
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from src.dominio import metodos_relevancia as mr
from src.dominio.entidades import PESOS_POR_DEFECTO, DatosEntrada
from src.dominio.interfaces import RepositorioConfigRelevancia, RepositorioRegistrosCampo

FORMATO = "siembra-relevancia"
VERSION = 1
METODOS = {"defecto": "Valores sugeridos", "ley_minimo": "Automático (Ley del Mínimo)", "historico": "Desde mi histórico",
           "experto": "Modo experto (AHP)", "campo": "Diario de campo", "manual": "Manual"}
NOMBRE_DEFECTO = "Agricultura real (por defecto)"


def _media(dist: Dict[str, Any]) -> float:
    """Valor medio de una distribución (Normal, Uniforme o Triangular)."""
    p, tipo = dist["parametros"], dist["tipo"]
    if tipo == "normal":
        return float(p["media"])
    if tipo == "uniforme":
        return (p["min"] + p["max"]) / 2.0
    return (p["min"] + p["moda"] + p["max"]) / 3.0


class GestorRelevancia:
    """Casos de uso del Factor de Relevancia."""

    def __init__(self, repo: RepositorioConfigRelevancia, repo_registros: Optional[RepositorioRegistrosCampo] = None) -> None:
        self.repo = repo
        self.repo_registros = repo_registros

    # --------------------------------------------------------------- perfiles
    @staticmethod
    def validar_pesos(pesos: Any) -> List[str]:
        """Los pesos deben ser un conjunto no vacío de números entre 0 y 100."""
        if not isinstance(pesos, dict) or not pesos:
            return ["Los pesos deben ser un conjunto de variables con un valor de 0 a 100."]
        errores = []
        for k, v in pesos.items():
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not 0 <= v <= 100:
                errores.append(f"El peso de «{k}» debe ser un número entre 0 y 100.")
        return errores

    def guardar(self, nombre: str, pesos: Dict[str, float], metodo: str = "manual", autor: str = "", notas: str = "") -> int:
        """Guarda un perfil nuevo y devuelve su id. Lanza ValueError si el nombre o los pesos no son válidos."""
        if not nombre.strip():
            raise ValueError("Ponle un nombre a la configuración.")
        errores = self.validar_pesos(pesos)
        if errores:
            raise ValueError(" ".join(errores))
        return self.repo.guardar({"nombre": nombre.strip(), "pesos": {k: float(v) for k, v in pesos.items()},
                                  "metodo": metodo, "autor": autor.strip(), "notas": notas.strip()})

    def listar(self) -> List[Dict[str, Any]]:
        """Perfiles guardados."""
        try:
            return self.repo.listar()
        except Exception:
            return []

    def cargar(self, id_config: int) -> Dict[str, Any]:
        """Devuelve el perfil (con sus pesos) o lanza ValueError si no existe."""
        c = self.repo.obtener(id_config)
        if not c:
            raise ValueError("Esa configuración ya no existe.")
        return c

    def duplicar(self, id_config: int, nombre: str = "") -> int:
        """Crea una copia editable de un perfil."""
        c = self.cargar(id_config)
        return self.guardar(nombre or f"{c['nombre']} (copia)", c["pesos"], c.get("metodo", "manual"),
                            c.get("autor", ""), c.get("notas", ""))

    def eliminar(self, id_config: int) -> bool:
        """Elimina un perfil."""
        return self.repo.eliminar(id_config)

    def crear_defecto(self) -> int:
        """Guarda la configuración por defecto para agricultura real (agua 80, temperatura 70, pH 40, N/P/K 60)."""
        return self.guardar(NOMBRE_DEFECTO, PESOS_POR_DEFECTO, "defecto", "Proyecto Siembrate",
                            "Valores orientativos para agricultura real. No sustituyen el consejo de un agrónomo.")

    # ------------------------------------------------------------ compartir
    @staticmethod
    def a_documento(nombre: str, pesos: Dict[str, float], metodo: str = "manual", autor: str = "", notas: str = "") -> Dict[str, Any]:
        """Documento JSON para compartir: nombre, autor, fecha, pesos, método usado y notas."""
        return {"formato": FORMATO, "version": VERSION, "nombre": nombre, "autor": autor, "fecha": date.today().isoformat(),
                "metodo": metodo, "pesos": {k: float(v) for k, v in pesos.items()}, "notas": notas}

    def exportar(self, id_config: int) -> Dict[str, Any]:
        """Documento JSON de un perfil guardado."""
        c = self.cargar(id_config)
        return self.a_documento(c["nombre"], c["pesos"], c.get("metodo", "manual"), c.get("autor", ""), c.get("notas", ""))

    def validar_documento(self, doc: Any) -> List[str]:
        """Revisa un JSON recibido: devuelve los problemas (vacía si está bien) sin lanzar excepciones."""
        if not isinstance(doc, dict):
            return ["El archivo no contiene una configuración de relevancia (está corrupto o es de otro tipo)."]
        errores = []
        if doc.get("formato") != FORMATO:
            errores.append("El archivo no es una configuración de relevancia de esta aplicación.")
        for campo in ("nombre", "pesos"):
            if campo not in doc:
                errores.append(f"Falta el campo obligatorio «{campo}».")
        if "pesos" in doc:
            errores += self.validar_pesos(doc["pesos"])
        if "nombre" in doc and not str(doc["nombre"]).strip():
            errores.append("El nombre está vacío.")
        return errores

    def importar(self, doc: Dict[str, Any]) -> int:
        """Valida y guarda un perfil recibido de otro usuario. Lanza ValueError con los problemas si no sirve."""
        errores = self.validar_documento(doc)
        if errores:
            raise ValueError("\n".join(errores))
        return self.guardar(str(doc["nombre"]), doc["pesos"], str(doc.get("metodo", "manual")),
                            str(doc.get("autor", "")), str(doc.get("notas", "")))

    # --------------------------------------------------------------- métodos
    @staticmethod
    def ley_del_minimo(datos: DatosEntrada) -> Tuple[Dict[str, float], Dict[str, str]]:
        """Pesos automáticos: más relevancia a lo que más se aleja del óptimo del cultivo."""
        c, det, est = datos.cultivo, datos.deterministas, datos.estocasticos

        def numero(clave: str) -> Optional[float]:
            v = det.get(clave)
            return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None

        variables: Dict[str, Optional[Dict[str, float]]] = {
            "agua": {"actual": _media(est["lluvia"]) + (numero("agua") or 0.0), "optimo": c.requerimiento_agua,
                     "tolerable": c.requerimiento_agua},
            "temperatura": {"actual": _media(est["temperatura"]), "optimo": (c.temp_min + c.temp_max) / 2,
                            "tolerable": (c.temp_max - c.temp_min) / 2},
            "humedad": {"actual": _media(est["humedad"]), "optimo": 65.0, "tolerable": 40.0},
            "ph": ({"actual": numero("ph"), "optimo": 6.5, "tolerable": 2.5} if numero("ph") is not None else None),
        }
        # Ley del Mínimo: de los nutrientes, limita el más lejano a su óptimo.
        peor, peor_dev = None, -1.0
        for nombre, clave, optimo in (("Nitrógeno", "nitrogeno", 100.0), ("Fósforo", "fosforo", 50.0), ("Potasio", "potasio", 100.0)):
            v = numero(clave)
            if v is not None and abs(v - optimo) / optimo > peor_dev:
                peor, peor_dev = (nombre, {"actual": v, "optimo": optimo, "tolerable": optimo}), abs(v - optimo) / optimo
        variables["nutrientes"] = peor[1] if peor else None
        pesos, textos = mr.ley_del_minimo(variables)
        if peor and pesos["nutrientes"] >= 15:
            textos["nutrientes"] = textos["nutrientes"].rstrip(".") + f" (el que limita es el {peor[0].lower()})."
        return pesos, textos

    @staticmethod
    def desde_historico(filas: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Pesos por correlación de Spearman a partir de un histórico ya leído (ver `lector_historico`)."""
        return mr.relevancia_historica(filas)

    @staticmethod
    def pares_experto() -> List[Tuple[str, str]]:
        """Parejas de variables que el experto debe comparar."""
        return mr.pares_de_variables()

    @staticmethod
    def desde_experto(comparaciones: Dict[Tuple[str, str], float]) -> Dict[str, Any]:
        """Pesos AHP desde las comparaciones por pares (escala 1-9)."""
        variables = list(mr.VARIABLES)
        res = mr.ahp(mr.matriz_comparacion(variables, comparaciones), variables)
        res["justificaciones"] = {v: f"{mr.ETIQUETAS[v]}: relevancia {p:.0f} según tus comparaciones." for v, p in res["pesos"].items()}
        res["resumen_consistencia"] = (f"Razón de consistencia CR = {res['cr']:.2f}: " +
                                       ("tus respuestas son coherentes." if res["consistente"] else
                                        "hay contradicciones; repite las comparaciones sugeridas."))
        return res

    # ---------------------------------------------------------- diario de campo
    @staticmethod
    def experimento(variable: str) -> str:
        """Texto del experimento sugerido para una variable."""
        return mr.experimento_sugerido(variable)

    def agregar_registro(self, temporada: str, variable: str, valor: Any, rendimiento: Any) -> int:
        """Anota un resultado del experimento. Lanza ValueError si algún dato no es válido."""
        if self.repo_registros is None:
            raise ValueError("El diario de campo no está disponible.")
        if variable not in mr.VARIABLES:
            raise ValueError("Elige una variable de la lista.")
        v, r = mr._a_numero(valor), mr._a_numero(rendimiento)
        if v is None or r is None:
            raise ValueError("El valor y el rendimiento deben ser números.")
        if not str(temporada).strip():
            raise ValueError("Escribe la temporada (por ejemplo, 2026-A).")
        return self.repo_registros.guardar({"temporada": str(temporada).strip(), "variable": variable, "valor": v, "rendimiento": r})

    def registros(self) -> List[Dict[str, Any]]:
        """Registros del diario de campo."""
        return self.repo_registros.listar() if self.repo_registros else []

    def eliminar_registro(self, id_registro: int) -> bool:
        """Borra un registro."""
        return bool(self.repo_registros and self.repo_registros.eliminar(id_registro))

    def desde_campo(self, datos: DatosEntrada) -> Dict[str, Any]:
        """Relevancia empírica; con menos de 5 registros usa la Ley del Mínimo y lo avisa."""
        res = mr.relevancia_empirica(self.registros())
        if res["suficiente"]:
            return {**res, "usa_ley_minimo": False}
        pesos, textos = self.ley_del_minimo(datos)
        return {"suficiente": False, "registros": res["registros"], "pesos": pesos, "justificaciones": textos,
                "usa_ley_minimo": True, "motivo": res["motivo"] + " Mientras tanto uso la Ley del Mínimo."}
