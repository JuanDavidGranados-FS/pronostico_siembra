"""Orquestador: coordina validación → Márkov → Montecarlo → Poisson → Relevancia → KPI → fecha óptima → plan."""
from __future__ import annotations

import logging
import math
import random
import time
from datetime import date, datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

import numpy as np

from src.aplicacion import explicador
from src.aplicacion.validador import ErrorValidacion, Validador
from src.dominio import poisson
from src.dominio.entidades import Cultivo, DatosEntrada
from src.dominio.factor_relevancia import FactorRelevancia
from src.dominio.galton_watson import ProcesoGaltonWatson
from src.dominio.interfaces import RepositorioConfiguraciones, RepositorioCultivos, RepositorioHistorial
from src.dominio.kpi import calcular_kpi, encontrar_fecha_optima
from src.dominio.markov import CadenaMarkov
from src.dominio.montecarlo import SimuladorMontecarlo
from src.dominio.objetos_valor import KPI, FechaOptima, ResultadoSimulacion

log = logging.getLogger(__name__)

UMBRAL_EXITO = 0.40       # éxito = rendimiento >= 40 % del rendimiento base
PROB_MIN_VIABLE = 0.10    # una fecha es viable si la probabilidad de éxito es >= 10 %
LIMITES = {"temperatura": None, "lluvia": (0.0, None), "humedad": (0.0, 100.0)}
ETIQUETAS_EVENTO = {"plagas": "Plagas", "heladas": "Heladas", "lluvias_intensas": "Lluvias intensas"}


class OrquestadorSimulacion:
    """Caso de uso principal: calcula la fecha óptima de siembra y el plan de temporadas."""

    def __init__(self, repo_cultivos: Optional[RepositorioCultivos] = None,
                 repo_config: Optional[RepositorioConfiguraciones] = None,
                 repo_historial: Optional[RepositorioHistorial] = None,
                 validador: Optional[Validador] = None) -> None:
        """Los repositorios son opcionales: sin ellos la simulación funciona pero no persiste."""
        self.repo_cultivos = repo_cultivos
        self.repo_config = repo_config
        self.repo_historial = repo_historial
        self.validador = validador or Validador()

    def listar_cultivos(self) -> List[Cultivo]:
        """Devuelve el catálogo de cultivos (lista vacía si no hay repositorio o falla)."""
        if not self.repo_cultivos:
            return []
        try:
            return [Cultivo.desde_dict(c) for c in self.repo_cultivos.listar()]
        except Exception:  # robustez: nunca crashear por el catálogo
            log.exception("No se pudo leer el catálogo de cultivos")
            return []

    # ------------------------------------------------------------------ API
    def ejecutar_simulacion(self, datos: DatosEntrada,
                            progreso: Optional[Callable[[int, int], None]] = None) -> ResultadoSimulacion:
        """Ejecuta la simulación completa y guarda el resultado en el historial."""
        inicio = time.perf_counter()
        errores = self.validador.validar_datos_entrada(datos)
        if errores:
            raise ErrorValidacion(errores)
        semilla = datos.semilla if datos.semilla is not None else random.SystemRandom().randrange(2 ** 31)
        sim = SimuladorMontecarlo(datos.iteraciones, semilla)
        fr = self._crear_factor(datos)
        fecha0 = date.fromisoformat(str(datos.deterministas["fecha"]))
        fechas = [fecha0 + timedelta(days=d) for d in range(0, datos.ventana_dias, datos.paso_dias)]

        registros: Dict[date, Dict[str, float]] = {}
        detalle: Dict[date, tuple] = {}
        for i, f in enumerate(fechas):
            reg, valores, evo, lambdas = self._evaluar_fecha(datos, fr, sim, f, int(semilla))
            registros[f] = reg
            detalle[f] = (valores, evo, lambdas)
            if progreso:
                progreso(i + 1, len(fechas))

        fecha_opt, kpi_val = encontrar_fecha_optima({f: r["kpi"] for f, r in registros.items()})
        reg = registros[fecha_opt]
        valores, evo, lambdas = detalle[fecha_opt]
        conteos, bordes = np.histogram(valores, bins=30)
        stats = {"media": float(valores.mean()), "std": float(valores.std()),
                 **{k: float(v) for k, v in zip(("p10", "p50", "p90"), np.percentile(valores, [10, 50, 90]))}}
        viable = reg["kpi"] > 0 and reg["probabilidad_exito"] >= PROB_MIN_VIABLE
        riesgos = self._riesgos(datos, lambdas)
        comparaciones = explicador.construir_comparaciones(registros, fecha_opt, fecha0, date.today(), datos.paso_dias)
        parrafo, razones = explicador.justificar(datos.cultivo, fecha_opt, reg, registros, datos.pesos, comparaciones,
                                                 riesgos, viable, float(datos.deterministas["agua"]))
        plan = self._plan_temporadas(datos, reg, fecha_opt, int(semilla))
        nombre = datos.nombre.strip() or f"Simulación {datetime.now():%d/%m/%Y %H:%M:%S}"
        resultado = ResultadoSimulacion(
            fecha_optima=FechaOptima(fecha_opt, kpi_val, reg["probabilidad_exito"], viable),
            kpi=KPI(kpi_val, reg["rendimiento_esperado"], reg["factor_relevancia"], float(datos.esfuerzo)),
            resultados_por_fecha={f.isoformat(): r for f, r in registros.items()},
            estadisticas_rendimiento=stats,
            histograma_rendimiento={"conteos": conteos.tolist(), "bordes": bordes.tolist()},
            evolucion_estados=evo, semilla=int(semilla), iteraciones=datos.iteraciones,
            nombre=nombre, cultivo=datos.cultivo.nombre, justificacion=parrafo, justificacion_detalle=razones,
            comparaciones=comparaciones, riesgos=riesgos, plan_temporadas=plan,
            duracion_segundos=round(time.perf_counter() - inicio, 2), pesos=dict(datos.pesos))
        return resultado.con_id(self._persistir(datos, resultado))

    # ------------------------------------------------------------ internos
    @staticmethod
    def _crear_factor(datos: DatosEntrada) -> FactorRelevancia:
        """Construye el Factor de Relevancia con rangos (mín, óptimo, máx) según el cultivo."""
        c = datos.cultivo
        rangos = {"temperatura": (c.temp_min - 5, (c.temp_min + c.temp_max) / 2, c.temp_max + 5),
                  "agua": (0.0, c.requerimiento_agua, 3 * c.requerimiento_agua),
                  "humedad": (20.0, 65.0, 100.0), "ph": (4.0, 6.5, 9.0),
                  "nitrogeno": (0.0, 100.0, 300.0), "fosforo": (0.0, 50.0, 150.0), "potasio": (0.0, 100.0, 300.0)}
        return FactorRelevancia(datos.pesos, rangos)

    @staticmethod
    def _puntajes(fr: FactorRelevancia, esc: np.ndarray, det: Dict[str, Any]) -> Dict[str, Any]:
        """Puntajes 0-1 por escenario para cada variable relevante."""
        return {
            "temperatura": fr.normalizar("temperatura", esc[:, :, 0]).mean(axis=1),
            "agua": fr.normalizar("agua", esc[:, :, 1].mean(axis=1) + float(det["agua"])),  # lluvia + riego
            "humedad": fr.normalizar("humedad", esc[:, :, 2].mean(axis=1)),
            "ph": fr.normalizar("ph", float(det["ph"])),
            "nutrientes": float(np.mean([fr.normalizar(k, float(det[k])) for k in ("nitrogeno", "fosforo", "potasio")])),
        }

    @staticmethod
    def _ajustar_salud(m: np.ndarray, estres: float) -> np.ndarray:
        """El estrés climático desplaza probabilidad Sano→Estresado y Estresado→Enfermo (hasta 30 %/semana)."""
        m = m.copy()
        delta = 0.3 * estres
        for i in range(min(2, m.shape[0] - 1)):
            mov = min(delta, m[i, i])
            m[i, i] -= mov
            m[i, i + 1] += mov
        return m

    @staticmethod
    def _ajustar_enfermedad(m: np.ndarray, resistencia: float) -> np.ndarray:
        """La resistencia a plagas reduce hasta 60 % la probabilidad de contraer la enfermedad."""
        m = m.copy()
        if m.shape[0] >= 2:
            m[0, 1:] *= 1.0 - 0.6 * resistencia / 100.0
            m[0, 0] = max(0.0, 1.0 - m[0, 1:].sum())
        return m

    @staticmethod
    def _ajustar_crecimiento(m: np.ndarray, clima: float) -> np.ndarray:
        """Las buenas condiciones aceleran el avance de etapa (velocidad 0.5x a 1.5x)."""
        m = m.copy()
        vel = 0.5 + clima
        for i in range(m.shape[0] - 1):
            p = m[i, i + 1]
            nuevo = min(p * vel, p + m[i, i])
            m[i, i] = max(0.0, m[i, i] - (nuevo - p))
            m[i, i + 1] = nuevo
        return m

    def _markov(self, datos: DatosEntrada, estres: float, clima: float, pasos: int):
        """Evoluciona las tres cadenas; devuelve (multiplicador de rendimiento, evolución serializable)."""
        resistencia = float(datos.deterministas.get("resistencia", datos.cultivo.resistencia_plagas))
        ajustes = {"salud": lambda m: self._ajustar_salud(m, estres),
                   "enfermedad": lambda m: self._ajustar_enfermedad(m, resistencia),
                   "crecimiento": lambda m: self._ajustar_crecimiento(m, clima)}
        mult, evolucion = 1.0, {}
        for nombre, ajustar in ajustes.items():
            cfg = datos.estado[nombre]
            base = np.array(cfg["matriz"], dtype=float)
            cadena = CadenaMarkov(cfg["estados"], ajustar(base))
            evo = cadena.evolucion(cfg["estado_inicial"], pasos)
            pesos = cfg.get("rendimiento_por_estado", {})
            vec = np.array([pesos.get(e, 1.0) for e in cadena.estados], dtype=float)
            mult *= float(evo[-1] @ vec)  # E[factor de rendimiento] al final del ciclo
            evolucion[nombre] = {e: evo[:, j].tolist() for j, e in enumerate(cadena.estados)}
        return mult, evolucion

    @staticmethod
    def _lambdas(datos: DatosEntrada, estres: float) -> Dict[str, float]:
        """Tasa esperada de eventos raros durante el ciclo (Poisson).

        La tasa mensual del usuario se multiplica por 0.5 + estrés climático (entre 0.5x y 1.5x: el mal clima
        hace más frecuentes los eventos) y, en las plagas, por (1 - 0.5·resistencia/100). Se escala a la duración del ciclo.
        """
        resistencia = float(datos.deterministas.get("resistencia", datos.cultivo.resistencia_plagas))
        salida = {}
        for nombre, cfg in datos.eventos_raros.items():
            lam_mes = float(cfg["tasa_mensual"]) * (0.5 + estres)
            if nombre == "plagas":
                lam_mes *= 1.0 - 0.5 * resistencia / 100.0
            salida[nombre] = lam_mes * datos.cultivo.dias_crecimiento / 30.0
        return salida

    def _evaluar_fecha(self, datos: DatosEntrada, fr: FactorRelevancia, sim: SimuladorMontecarlo, fecha: date,
                       semilla: int):
        """Evalúa una fecha candidata: escenarios → puntajes → Márkov → Poisson → rendimiento → KPI."""
        c, det = datos.cultivo, datos.deterministas
        h, doy = c.dias_crecimiento, fecha.timetuple().tm_yday
        dists = {}
        for nombre in ("temperatura", "lluvia", "humedad"):
            d = datos.estocasticos[nombre]
            dists[nombre] = {"tipo": d["tipo"], "parametros": d["parametros"], "limites": LIMITES[nombre],
                             "desplazamiento": sim.perfil_estacional(doy, h, float(d.get("amplitud_estacional", 0.0)),
                                                                     float(d.get("dia_pico", 200)))}
        esc = sim.generar_escenarios(dists, h)  # semilla fija: mismos números aleatorios en cada fecha
        p = self._puntajes(fr, esc, det)
        # El clima (ponderado por relevancia) determina el estrés y la velocidad de crecimiento.
        clima = float(fr.calcular_kpi_ponderado({k: float(np.mean(p[k])) for k in ("temperatura", "agua", "humedad")}))
        mult, evo = self._markov(datos, 1.0 - clima, clima, max(1, h // 7))
        lambdas = self._lambdas(datos, 1.0 - clima)
        rng_eventos = np.random.default_rng([semilla, 7919])  # mismos números en cada fecha y en cada ejecución
        captura: Dict[str, float] = {}

        def rendimiento(e: np.ndarray) -> np.ndarray:
            q = self._puntajes(fr, e, det)
            # Viabilidad térmica: por debajo de un puntaje medio de 0.15 (heladas/calor extremo) el cultivo no prospera.
            letal = np.clip(q["temperatura"] / 0.15, 0.0, 1.0)
            # Eventos raros: cada ocurrencia (Poisson) multiplica el rendimiento por (1 - pérdida).
            riesgo = np.ones(e.shape[0])
            for nombre, cfg in datos.eventos_raros.items():
                n_eventos = poisson.muestrear(rng_eventos, lambdas[nombre], e.shape[0])
                riesgo *= poisson.factor_rendimiento(n_eventos, float(cfg["perdida"]))
            captura["riesgo"] = float(riesgo.mean())
            return c.rendimiento_base * mult * fr.calcular_kpi_ponderado(q) * letal * riesgo

        est = sim.calcular_rendimiento(esc, rendimiento)
        valores = est["valores"]
        rend_esp = c.rendimiento_base * mult * captura["riesgo"]   # rendimiento esperado ya ajustado por eventos raros
        f_rel = float(np.mean(valores) / rend_esp) if rend_esp > 0 else 0.0
        reg = {"kpi": calcular_kpi(rend_esp, f_rel, datos.esfuerzo), "rendimiento_esperado": float(rend_esp),
               "factor_relevancia": f_rel, "rendimiento_medio": est["media"], "rendimiento_p10": est["p10"],
               "rendimiento_p90": est["p90"], "multiplicador_markov": float(mult), "estres_climatico": 1.0 - clima,
               "perdida_eventos": 1.0 - captura["riesgo"],
               "probabilidad_exito": float(np.mean(valores >= UMBRAL_EXITO * c.rendimiento_base)),
               "temperatura_media": float(esc[:, :, 0].mean()), "lluvia_media": float(esc[:, :, 1].mean()),
               "p_temperatura": float(np.mean(p["temperatura"])), "p_agua": float(np.mean(p["agua"])),
               "p_humedad": float(np.mean(p["humedad"])), "p_ph": float(p["ph"]), "p_nutrientes": float(p["nutrientes"])}
        return reg, valores, evo, lambdas

    @staticmethod
    def _riesgos(datos: DatosEntrada, lambdas: Dict[str, float]) -> List[Dict[str, Any]]:
        """Panel de «Riesgos identificados»: probabilidad de 0, 1, 2 o más eventos y pérdida esperada."""
        salida = []
        for nombre, cfg in datos.eventos_raros.items():
            lam = lambdas[nombre]
            salida.append({"clave": nombre, "etiqueta": ETIQUETAS_EVENTO.get(nombre, nombre.replace("_", " ").capitalize()),
                           "tasa_mensual": float(cfg["tasa_mensual"]), "lambda_ciclo": lam,
                           "probabilidades": poisson.distribucion(lam, 2), "perdida_por_evento": float(cfg["perdida"]),
                           "perdida_esperada": poisson.perdida_esperada(lam, float(cfg["perdida"]))})
        return salida

    def _plan_temporadas(self, datos: DatosEntrada, reg: Dict[str, float], fecha_opt: date, semilla: int) -> Dict[str, Any]:
        """Plan de N temporadas con Galton-Watson: población, cosecha, semillas a guardar y riesgo de extinción.

        La media de descendientes de la primera temporada es μ = media_descendientes × (rendimiento medio / rendimiento base):
        si el clima y los riesgos reducen la cosecha, cada planta deja menos descendencia.
        """
        p = datos.plan
        n = int(p["temporadas"])
        base = datos.cultivo.rendimiento_base
        ratio = max(0.0, min(1.0, reg["rendimiento_medio"] / base))
        mu0 = float(p["media_descendientes"]) * ratio
        cap = int(p["capacidad"])
        proceso = ProcesoGaltonWatson(mu0, int(p["plantas_iniciales"]), cap, float(p["agotamiento_suelo"]))
        res = proceso.resumen(n, 2000, semilla)
        medias = res["medias"]
        filas = []
        for t in range(1, n + 1):
            plantas = res["poblacion_media"][t - 1]
            filas.append({"temporada": t, "fecha_siembra": (fecha_opt + timedelta(days=365 * (t - 1))).isoformat(),
                          "poblacion_esperada": plantas, "ocupacion": min(1.0, plantas / cap),
                          "media_descendientes": medias[t - 1],
                          "cosecha_estimada": reg["rendimiento_medio"] * min(1.0, plantas / cap),
                          "semillas_guardar": int(math.ceil(res["poblacion_media"][t]))})
        primera = next((t for t, m in enumerate(medias, 1) if m < 1), None)
        if primera == 1:
            reco = (f"Con estas condiciones cada planta deja menos de una descendiente (μ = {medias[0]:.2f}): el cultivo no se "
                    f"sostiene. Cambia de fecha, mejora el riego o rota a otro cultivo.")
        elif primera:
            reco = (f"En la temporada {primera} la media de descendientes baja a {medias[primera - 1]:.2f} (menos de 1) por el "
                    f"desgaste del suelo: rota el cultivo antes de esa temporada.")
        else:
            reco = (f"El cultivo es sostenible durante {n} temporada{'s' if n > 1 else ''} (μ de {medias[-1]:.2f} a {medias[0]:.2f}). "
                    f"Guarda las semillas indicadas en la tabla para la siguiente siembra.")
        return {"temporadas": n, "media_base": mu0, "ratio_rendimiento": ratio, "medias": medias,
                "clasificacion": res["clasificacion"], "prob_extincion_largo_plazo": res["prob_extincion_largo_plazo"],
                "prob_extincion_horizonte": res["prob_extincion_horizonte"], "riesgo_extincion": res["riesgo_extincion"],
                "recomendacion": reco, "filas": filas, "capacidad": cap, "aviso_largo_plazo": n > 10,
                "trayectoria": {"media": res["poblacion_media"], "p10": res["poblacion_p10"], "p90": res["poblacion_p90"]}}

    def _persistir(self, datos: DatosEntrada, resultado: ResultadoSimulacion) -> Optional[int]:
        """Guarda configuración y resultado; un fallo de persistencia nunca interrumpe la simulación."""
        try:
            cfg_id = None
            if self.repo_config:
                cfg_id = self.repo_config.guardar(resultado.nombre, datos.a_dict())
            if self.repo_historial:
                return self.repo_historial.guardar(resultado.a_dict(), cfg_id, resultado.nombre)
        except Exception:
            log.exception("No se pudo guardar la simulación en el historial")
        return None
