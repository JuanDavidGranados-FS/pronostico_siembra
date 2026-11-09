# Registro de cambios

Todos los cambios relevantes del proyecto se documentan en este archivo.
El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto usa [versionado semántico](https://semver.org/lang/es/).

## [1.1.0] - 2026-11-09

### Agregado
- **Soporte para Android con Pydroid 3**. La app abre en modo gráfico, carga una versión mínima de `msgcat` si el Tcl del
  entorno no la trae y guarda en `error.txt` cualquier error que la cierre.
- **Interfaz adaptable a celular**. Se activa sola en Android o en pantallas de menos de 900 px de ancho:
  - escala del texto según la pantalla y ventana a pantalla completa;
  - reacomodo automático (`src/presentacion/movil.py`): filas en varios renglones, rejillas en una columna, textos y tablas al
    ancho disponible;
  - desplazamiento con el dedo, con gestos de rueda y con una barra lateral gruesa;
  - menú en su propia franja, asistente a pantalla completa y gráficas al ancho de la pantalla.
- Variables de entorno `SIEMBRA_MOVIL` (forzar o desactivar el modo celular) y `SIEMBRA_ESCALA` (ajustar el tamaño).
- `requirements-android.txt`, guía `docs/android_pydroid.md`, capturas en `docs/img/` y prueba automática en GitHub Actions.

### Corregido
- Al volver a simular estando en Resultados, la página anterior quedaba visible encima de las demás.

## [1.0.0] - 2026-10-30

### Agregado
- Recomendación de la fecha óptima de siembra con cadenas de Márkov, simulación de Montecarlo, distribución de Poisson y el proceso de
  Galton-Watson.
- Factor de Relevancia con cinco métodos de cálculo (valores sugeridos, Ley del Mínimo, histórico, AHP y diario de campo).
- Historial con búsqueda, comparación y reutilización de configuraciones.
- Exportes a PDF, Excel, CSV, JSON y PNG.
- Integración con simuladores externos mediante JSON.
- Persistencia en PostgreSQL con respaldo en memoria.
- Asistente sin internet, recorrido guiado y temas claro/oscuro.
