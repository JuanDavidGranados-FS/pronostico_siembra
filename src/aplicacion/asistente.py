"""Asistente de preguntas sin internet: glosario, preguntas frecuentes y respuestas a lo que el usuario escriba.

No usa modelos de lenguaje: busca por palabras clave (tolerando tildes y errores de tecleo) en un conjunto de
respuestas redactadas para el programa. Cada respuesta es breve; el usuario puede pedir más detalle cuando quiera.
"""
from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

FUENTE_DEFECTO = ("Referencias del proyecto: Jones et al. (2003), «The DSSAT cropping system model», y FAO (2016), "
                  "«AquaCrop reference manual». Los valores iniciales son un punto de partida y no están calibrados "
                  "para un sitio concreto.")


@dataclass(frozen=True)
class Tema:
    """Un tema que el asistente sabe explicar."""
    clave: str
    titulo: str
    palabras: Tuple[str, ...]
    respuesta: str
    detalle: str = ""
    glosario: bool = False


TEMAS: Tuple[Tema, ...] = (
    Tema("markov", "Cadena de Márkov", ("markov", "cadena", "estados", "transicion", "salud", "enfermedad", "crecimiento"),
         "Es una forma de describir cómo cambia la planta de un estado a otro (por ejemplo, de Sana a Débil). "
         "Solo importa el estado de hoy, no el pasado.",
         "Cada fila de la matriz dice con qué probabilidad la planta pasa del estado de esa fila a cada estado de las "
         "columnas, en una semana. Cada fila debe sumar 1. Un estado como «Muerto» es absorbente: no se sale de él.", True),
    Tema("montecarlo", "Montecarlo", ("montecarlo", "escenarios", "iteraciones", "simulaciones", "aleatorio", "clima incierto"),
         "Es repetir miles de veces el clima posible (cada vez distinto) para ver qué tan bien o mal le iría al cultivo.",
         "En lugar de suponer un clima promedio, el programa genera miles de climas al azar según las distribuciones "
         "que indicaste y mide qué pasa en cada uno. Más iteraciones dan resultados más estables pero tardan más.", True),
    Tema("poisson", "Distribución de Poisson", ("poisson", "eventos raros", "plagas", "heladas", "lluvias intensas", "tasa"),
         "Calcula la probabilidad de que ocurran 0, 1, 2 o más eventos raros (plaga, helada…) conociendo cuántos "
         "ocurren en promedio.",
         "Con 1,5 plagas por mes, la probabilidad de que no llegue ninguna en un mes es de 22 %. El programa usa esa "
         "idea para descontar del rendimiento el riesgo real de pérdidas inesperadas.", True),
    Tema("galton", "Galton-Watson", ("galton", "watson", "extincion", "temporadas", "semillas", "sostenible", "rotar", "rotacion", "poblacion"),
         "Planifica varias temporadas: calcula cuántas plantas esperas, cuántas semillas guardar y si el cultivo se "
         "sostiene o se extingue.",
         "Si cada planta deja en promedio más de una descendiente (μ > 1) el cultivo crece; si deja menos de una "
         "(μ < 1) se acaba. Con μ < 1 el programa te avisa y recomienda rotar el cultivo.", True),
    Tema("relevancia", "Factor de Relevancia", ("relevancia", "factor", "pesos", "peso", "importancia", "sliders", "deslizadores"),
         "Es cuánto le importa a cada variable en tu caso, de 0 (se ignora) a 100 (máxima importancia).",
         "Sirve para adaptar el programa: en un simulador sin nutrientes pones nutrientes = 0; en una parcela con poca "
         "agua subes el agua a 100. La recomendación se orienta a las fechas donde lo importante está mejor.", True),
    Tema("minimo", "Ley del Mínimo", ("minimo", "ley", "liebig", "automatico", "limitante"),
         "Calcula la relevancia sola: lo que está más lejos de su valor ideal es lo que más limita al cultivo, así "
         "que recibe más peso.",
         "Fórmula: |valor actual − óptimo| ÷ rango tolerable × 100. Si el pH está en su rango ideal, su relevancia es "
         "baja; si el agua está muy por debajo de lo que pide la planta, su relevancia es alta.", True),
    Tema("ahp", "Modo experto (AHP)", ("ahp", "experto", "comparaciones", "pares", "consistencia"),
         "Comparas las variables de dos en dos («¿qué pesa más, el agua o la temperatura?») y el programa calcula los pesos.",
         "Se usa la escala de 1 a 9. El programa también revisa que tus respuestas no se contradigan (razón de "
         "consistencia menor que 0,1); si lo hacen, te pide repetir las comparaciones más dudosas.", True),
    Tema("historico", "Desde mi histórico", ("historico", "excel", "csv", "spearman", "correlacion", "archivo"),
         "Subes un archivo CSV o Excel con tus temporadas pasadas y el programa mide qué variables se relacionan más con el rendimiento.",
         "El archivo necesita una columna «rendimiento», al menos una variable (agua, temperatura, humedad, ph, "
         "nitrogeno, fosforo o potasio) y mínimo 10 filas completas. Se usa la correlación de Spearman.", True),
    Tema("diario", "Diario de campo", ("diario", "experimento", "campo", "registros", "lotes"),
         "Te propone un experimento simple (cambiar una sola variable entre dos lotes) y guardas lo que obtengas.",
         "Con al menos 5 registros el programa calcula la relevancia con tus propios datos. Mientras tanto usa la Ley del Mínimo.", True),
    Tema("kpi", "KPI", ("kpi", "indicador", "puntaje"),
         "Es el puntaje que compara fechas: el rendimiento esperado ajustado por lo que te importa y por el esfuerzo. "
         "La fecha con el KPI más alto gana.",
         "KPI = rendimiento esperado × factor de relevancia ÷ (1 + esfuerzo).", True),
    Tema("fecha", "Fecha óptima", ("fecha optima", "fecha", "cuando sembrar", "recomendacion", "recomendada"),
         "Es el día de siembra con el mejor resultado esperado entre todas las fechas que se probaron.",
         "El programa prueba una fecha cada cierto número de días dentro de la ventana que elijas y se queda con la "
         "de mayor KPI. Si dos empatan, gana la más temprana.", True),
    Tema("exito", "Probabilidad de éxito", ("exito", "probabilidad", "viable", "no viable", "seguro"),
         "Es el porcentaje de escenarios en que la cosecha llega al menos al 40 % del rendimiento base.",
         "Una fecha se considera viable si esa probabilidad es de al menos 10 %. Si ninguna fecha lo logra, el "
         "programa te dice «no encontré una fecha segura» y sugiere cambiar la ventana, el cultivo o el riego.", True),
    Tema("rango", "Rango de cosecha", ("percentil", "percentiles", "intervalo", "confianza", "rango", "p10", "p90", "80"),
         "El rango de cosecha va del percentil 10 al 90: en 8 de cada 10 escenarios la cosecha cae dentro de él.",
         "Es más útil que un promedio, porque te dice qué tan incierto es el resultado.", True),
    Tema("semilla", "Semilla aleatoria", ("semilla aleatoria", "reproducir", "repetir", "mismo resultado"),
         "Es un número que fija el azar de la simulación. Con la misma semilla obtienes exactamente el mismo resultado.",
         "Si la dejas vacía, cada ejecución usa un azar distinto y los números cambian un poco.", True),
    Tema("esfuerzo", "Esfuerzo", ("esfuerzo", "costo", "coste"),
         "Es el costo o trabajo relativo de sembrar (0 o más). Cuanto más alto, más baja el KPI.",
         "El KPI se divide entre (1 + esfuerzo): con esfuerzo 1 el KPI queda a la mitad.", False),
    Tema("ventana", "Ventana y paso", ("ventana", "paso", "dias", "candidatas"),
         "La ventana son los días que se exploran desde la fecha inicial; el paso es cada cuántos días se prueba una fecha.",
         "Con ventana 365 y paso 15 se evalúan unas 25 fechas. Un paso más pequeño es más fino pero tarda más.", False),
    Tema("ph", "pH del suelo", ("ph", "acidez", "suelo"),
         "Mide qué tan ácido o alcalino es el suelo (0 a 14). Para la mayoría de cultivos lo ideal está cerca de 6,5.", "", False),
    Tema("npk", "Nutrientes N/P/K", ("nitrogeno", "fosforo", "potasio", "npk", "nutrientes", "abono", "fertilizante"),
         "Son los tres nutrientes principales del suelo (kg por hectárea): nitrógeno, fósforo y potasio.",
         "Como referencia, el programa considera ideales 100, 50 y 100 kg/ha.", False),
    Tema("resistencia", "Resistencia a plagas", ("resistencia", "semilla resistente"),
         "Qué tan bien aguanta la planta plagas y enfermedades (0 a 100). Más resistencia reduce la probabilidad de enfermar.", "", False),
    Tema("riego", "Riego", ("riego", "agua", "regar", "lluvia"),
         "Es el agua que tú aportas (mm por día) y se suma a la lluvia esperada para cubrir lo que pide el cultivo.", "", False),
    Tema("distribuciones", "Distribuciones", ("normal", "uniforme", "triangular", "distribucion", "media", "desviacion"),
         "Describen cuánto puede variar una variable: Normal (media y desviación), Uniforme (entre un mínimo y un "
         "máximo) o Triangular (mínimo, valor más probable y máximo).", "", False),
    Tema("estacional", "Cambio por estación", ("amplitud", "estacional", "estacion", "dia pico", "pico"),
         "La amplitud es cuánto sube y baja la variable a lo largo del año; el día pico es cuándo alcanza su valor más alto.",
         "Por ejemplo, amplitud 6 y día pico 200 hacen que la temperatura sea unos 6 °C más alta a mediados de julio.", False),
    Tema("matriz", "Matriz de transición", ("matriz", "fila", "suma 1", "normalizar", "estado inicial"),
         "Cada fila es un estado de partida y cada número, la probabilidad de pasar a otro estado en una semana. "
         "Cada fila debe sumar 1.", "Si una fila no suma 1 se marca en rojo; puedes usar «Normalizar filas» para corregirla.", False),
    Tema("capacidad", "Capacidad y suelo", ("capacidad", "terreno", "agotamiento", "plantas iniciales"),
         "La capacidad es el máximo de plantas que cabe en tu terreno; el agotamiento es cuánto empeora el suelo cada temporada.", "", False),
    Tema("defecto", "Valores sugeridos", ("defecto", "sugeridos", "restaurar", "predeterminado", "fuente", "agua 80"),
         "Son valores de partida para agricultura real: agua 80, temperatura 70, pH 40, nutrientes 60. Puedes ejecutar "
         "una simulación sin cambiar nada.", FUENTE_DEFECTO, True),
    Tema("json", "Datos externos (JSON)", ("json", "externo", "simulador", "mod", "integracion", "importar", "conectar"),
         "Un simulador o mod puede enviarte datos como archivo JSON. Colócalo en la carpeta de entrada o cárgalo con «Cargar JSON».",
         "La guía para desarrolladores está en Ayuda → Guía de integración: explica los campos obligatorios, un "
         "ejemplo mínimo y los errores más comunes.", False),
    Tema("semaforo", "Semáforo de conexión", ("semaforo", "conectado", "indicador", "verde", "amarillo", "rojo"),
         "Verde: llegaron datos válidos. Amarillo: hace más de 5 minutos que no llegan datos. Rojo: el último archivo era inválido.", "", False),
    Tema("postgres", "Base de datos", ("postgresql", "postgres", "base de datos", "bd", "docker", "memoria"),
         "PostgreSQL guarda tu historial y tus configuraciones. Sin ella, el programa funciona pero todo se pierde al cerrar.",
         "Para activarla: copia «.env.example» como «.env» y ejecuta «docker compose -f docker/docker-compose.yml up -d».", False),
    Tema("exportar", "Exportar", ("exportar", "pdf", "descargar", "png", "compartir", "informe"),
         "Desde Resultados puedes exportar un informe PDF, Excel, CSV, JSON o PNG con las gráficas.", "", False),
    Tema("historial", "Historial", ("historial", "guardadas", "comparar", "renombrar", "reutilizar"),
         "Cada simulación se guarda sola. En Historial puedes buscarlas, ponerles nombre, reutilizar su configuración y comparar dos.", "", False),
    Tema("tour", "Recorrido guiado", ("tour", "recorrido", "guia", "tutorial", "ayuda", "empezar", "perdido"),
         "El recorrido guiado te muestra los pasos principales: datos, relevancia, simulación, resultados y exportar. Puedes volver a verlo desde Ayuda.", "", False),
    Tema("descargo", "Aviso importante", ("descargo", "responsabilidad", "agronomo", "confiable", "garantia"),
         "Las recomendaciones son informativas y no reemplazan el juicio de un profesional. En agricultura real consulta a un agrónomo.", "", False),
)

SUGERENCIAS_INICIALES = ["¿Qué es el Factor de Relevancia?", "¿Qué significa «no viable»?", "¿Qué es Montecarlo?",
                         "¿Cómo exporto los resultados?"]


def _norm(texto: str) -> str:
    t = unicodedata.normalize("NFD", texto.lower())
    return re.sub(r"[^a-z0-9 ]+", " ", "".join(c for c in t if unicodedata.category(c) != "Mn"))


def _puntaje(tokens: List[str], consulta: str, tema: Tema) -> float:
    total = 0.0
    for p in tema.palabras:
        pn = _norm(p).strip()
        if " " in pn:
            if pn in consulta:
                total += 3.0
            continue
        for tk in tokens:
            if tk == pn:
                total += 3.0
            elif len(tk) >= 4 and len(pn) >= 4 and (tk.startswith(pn[:5]) or pn.startswith(tk[:5])):
                total += 2.0
            elif len(tk) >= 5 and difflib.SequenceMatcher(None, tk, pn).ratio() >= 0.84:
                total += 2.0
    if _norm(tema.titulo).strip() in consulta:
        total += 4.0
    return total


def buscar(pregunta: str) -> Optional[Tema]:
    """El tema que mejor responde a la pregunta, o None si nada se parece."""
    consulta = _norm(pregunta)
    tokens = [t for t in consulta.split() if len(t) > 1]
    if not tokens:
        return None
    mejor = max(TEMAS, key=lambda t: _puntaje(tokens, consulta, t))
    return mejor if _puntaje(tokens, consulta, mejor) >= 2.0 else None


def _sobre_resultado(consulta: str, resultado: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Preguntas sobre el resultado que el usuario tiene en pantalla."""
    quiere = lambda *ps: any(p in consulta for p in ps)
    if quiere("por que esta fecha", "por que esa fecha", "por que recomiendas", "por que me recomiendas", "mi resultado",
              "que significa mi", "explica mi", "explicame el resultado"):
        det = resultado.get("justificacion_detalle") or []
        return {"respuesta": resultado.get("justificacion", "Aún no hay una justificación."), "tema": "Tu resultado",
                "mas": " ".join(det) if det else None}
    if quiere("mis riesgos", "riesgo de mi", "que riesgos", "riesgos identificados"):
        r = resultado.get("riesgos") or []
        if r:
            mayor = max(r, key=lambda x: x["perdida_esperada"])
            return {"respuesta": f"El mayor riesgo en tu simulación es {mayor['etiqueta'].lower()}: se espera perder cerca "
                                 f"de {mayor['perdida_esperada'] * 100:.0f} % de la cosecha por esa causa.",
                    "tema": "Tu resultado", "mas": None}
    return None


def responder(pregunta: str, contexto: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Respuesta a una pregunta: {"respuesta", "tema", "mas" (detalle opcional), "sugerencias"}."""
    consulta = _norm(pregunta)
    if contexto and contexto.get("resultado"):
        r = _sobre_resultado(consulta, contexto["resultado"])
        if r:
            return {**r, "sugerencias": ["¿Qué es la probabilidad de éxito?", "¿Qué es el KPI?"]}
    tema = buscar(pregunta)
    if tema is None:
        return {"respuesta": "No encontré eso. Prueba preguntando por un término (por ejemplo «Poisson» o «Factor de "
                             "Relevancia») o elige una de las sugerencias.", "tema": None, "mas": None,
                "sugerencias": list(SUGERENCIAS_INICIALES)}
    parecidos = sorted((t for t in TEMAS if t is not tema), key=lambda t: -_puntaje(
        [x for x in _norm(tema.titulo + " " + " ".join(tema.palabras)).split() if len(x) > 3], _norm(tema.titulo), t))[:2]
    return {"respuesta": tema.respuesta, "tema": tema.titulo, "mas": tema.detalle or None,
            "sugerencias": [f"¿Qué es {t.titulo}?" if t.glosario else f"Háblame de {t.titulo}" for t in parecidos]}


def glosario() -> List[Tuple[str, str]]:
    """Pares (término, definición) ordenados alfabéticamente para la pestaña Glosario."""
    filas = []
    for t in TEMAS:
        if t.glosario:
            filas.append((t.titulo, (t.respuesta + " " + t.detalle).strip()))
    return sorted(filas, key=lambda f: _norm(f[0]))


PREGUNTAS_FRECUENTES: Tuple[Tuple[str, str], ...] = (
    ("¿Por dónde empiezo?", "Pulsa «Comenzar simulación» en Inicio. Puedes ejecutar una simulación sin cambiar nada: el programa trae valores sugeridos."),
    ("¿Qué significa «no viable»?", "Que en ninguna fecha explorada el cultivo llega al menos a 10 % de probabilidad de éxito. Prueba otra ventana, otro cultivo o más riego."),
    ("¿Por qué cambia el resultado entre ejecuciones?", "Porque la semilla aleatoria está vacía. Escribe un número en «Semilla» (Simulación → Ajustes avanzados) para obtener siempre el mismo resultado."),
    ("¿Funciona sin PostgreSQL?", "Sí. Sin base de datos todo se guarda en memoria y se pierde al cerrar. Inicio te explica cómo activarla."),
    ("¿Cómo comparo dos simulaciones?", "En Historial, selecciona dos y pulsa «Comparar», o abre una desde Resultados y pulsa «Comparar con otra»."),
    ("¿Cómo comparto mi configuración de relevancia?", "En Relevancia pulsa «Descargar configuración» para generar un JSON y envíaselo a otra persona; ella lo carga con «Importar»."),
    ("¿Puedo usar datos de un simulador?", "Sí: coloca un JSON en la carpeta de entrada o usa «Cargar JSON». Lee la guía de integración en Ayuda."),
)
