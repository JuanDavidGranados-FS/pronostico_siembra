# Siembra · Sistema de Pronóstico de Siembra Adaptable

Aplicación de escritorio (Windows / Linux / macOS) con aspecto de aplicación web moderna que recomienda la **fecha óptima de siembra**
y planifica varias temporadas. Combina:

- **Cadenas de Márkov** (salud, enfermedad, crecimiento) con matrices editables.
- **Simulación de Montecarlo** del clima incierto.
- **Distribución de Poisson** para eventos raros (plagas, heladas, lluvias intensas): panel «Riesgos identificados».
- **Proceso de Galton-Watson** para planes de 1 a 10 temporadas, con alerta de extinción (μ < 1).
- **Factor de Relevancia** (pesos 0-100) calculable por: valores sugeridos, Ley del Mínimo, histórico CSV/Excel (Spearman), modo experto (AHP) o diario de campo.

La interfaz muestra la información **en pedazos**: una pantalla a la vez, secciones plegadas, un solo número destacado y un asistente
(sin internet) al que se puede preguntar todo lo que se quiera.

Arquitectura en capas: `presentacion` (Tkinter/ttkbootstrap) → `aplicacion` → `dominio` (matemática pura) ← `infraestructura` (PostgreSQL, JSON, exportes).

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# Linux: si falta Tkinter ->  sudo apt install python3-tk
```

## Base de datos (opcional)

```bash
cp .env.example .env
docker compose -f docker/docker-compose.yml up -d     # crea el esquema y carga los cultivos
```

Sin PostgreSQL la aplicación funciona igual con almacenamiento en memoria (se pierde al cerrar). Inicio → *Estado del sistema* lo indica y explica cómo activarla.

## Uso

```bash
python main.py
```

1. **Inicio**: «Comenzar simulación», o «Ejecutar con valores sugeridos» (no hace falta cambiar nada).
2. **Datos**, **Relevancia**, **Simulación**: cada sección se abre solo si quieres cambiarla.
3. **Resultados**: fecha recomendada y motivo; gráficas, comparación, riesgos, temporadas y exportes (PDF, Excel, CSV, JSON, PNG) bajo demanda.
4. **Historial**: buscar, renombrar, reutilizar la configuración y comparar dos simulaciones.
5. **Ayuda**: recorrido guiado, glosario, preguntas frecuentes y la guía de integración (`docs/integration_guide.md`).

Datos desde un simulador: coloca un JSON en la carpeta de entrada (Inicio la muestra) o usa «Cargar JSON». Ver `docs/integration_guide.md`.

## Pruebas

```bash
pytest --cov                         # la cobertura excluye el repositorio PostgreSQL (necesita una base real)
xvfb-run -a pytest                   # en Linux sin pantalla, para ejecutar también las pruebas de interfaz
```

Cubren CV-01 a CV-06 (incluidos CV-05: μ < 1 → extinción y CV-06: Poisson λ = 1,5 → P(0) ≈ 22 %). Con una base real, `tests/test_postgres.py` se activa solo.

## Empaquetado

```bash
pyinstaller --noconfirm --onefile --windowed --name Siembra --add-data "docs:docs" --add-data "db:db" main.py
```

## Aviso

Las recomendaciones son informativas y no reemplazan el juicio de un profesional. Los valores iniciales son un punto de partida
(referencias: DSSAT y AquaCrop) y no están calibrados para un sitio concreto: confírmalos con tu equipo antes de usarlos en agricultura real.
