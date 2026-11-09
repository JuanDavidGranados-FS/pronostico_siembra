# Registro de cambios

Todos los cambios relevantes del proyecto se documentan en este archivo.
El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto usa [versionado semántico](https://semver.org/lang/es/).

## [2.0.0] - 2026-11-09

### Cambiado
- **La versión web ahora es igual a la app de escritorio.** Tiene las mismas 7 pestañas (Inicio, Datos, Relevancia, Simulación,
  Resultados, Historial, Ayuda), el mismo diseño y los mismos widgets, el asistente lateral, el recorrido guiado, el semáforo y el
  tema claro/oscuro. En el celular se reacomoda igual que el modo celular de escritorio.
- `web/motor.py` ahora arma el contexto completo: orquestador, gestores de historial y relevancia, y repositorios en memoria que se
  guardan en el navegador.
- Las gráficas son las de escritorio (matplotlib en el navegador), en lugar de Chart.js.

### Agregado (web)
- Relevancia completa: Ley del Mínimo, histórico CSV/Excel, modo experto (AHP), diario de campo y configuraciones guardadas
  (guardar, cargar, duplicar, eliminar, descargar e importar).
- Datos completos: clima con tipo de distribución, matrices de Márkov editables (normalizar, agregar o quitar estados, guardar y
  cargar), eventos raros y plan de temporadas.
- Historial: buscar, abrir, comparar dos, reutilizar la configuración, renombrar y eliminar.
- Exportes a PDF, Excel, CSV, JSON y PNG, y carga de JSON de un simulador.

## [1.2.0] - 2026-11-09

### Agregado
- **Versión web** (`web/`) para probar la app desde el navegador, sin instalar nada:
  - el mismo motor en Python (`src/dominio` y `src/aplicacion`) corre en el dispositivo con Pyodide, en segundo plano;
  - pantallas Inicio, Datos y Resultados, con gráficas (Chart.js), comparación, riesgos, temporadas y asistente;
  - diseño para celular, tema claro/oscuro automático e instalable en la pantalla de inicio;
  - lista para publicarse en Vercel como sitio estático (`web/vercel.json`).
- `web/empaquetar.py` genera `web/siembra.zip`, y `tests/test_web.py` verifica que esté al día.
- Guía `docs/web.md`: publicación en Vercel y código QR.

### Corregido
- La simulación podía quedarse trabada en la app de escritorio. Si el recolector de basura de Python liberaba objetos de Tk
  (por ejemplo, tras cambiar el tema) dentro del hilo de cálculo, cada liberación esperaba al bucle de Tk. Ahora se limpian en el
  hilo principal y el recolector se pausa mientras se simula. Esto también causaba fallos intermitentes en las pruebas de interfaz.
- La prueba de reproducibilidad CV-03 fallaba a veces porque comparaba el nombre por defecto, que incluye la hora.

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
