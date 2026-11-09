# Manual técnico

## Capas
- `src/dominio`: matemática y entidades puras (numpy): `markov`, `montecarlo`, `poisson`, `galton_watson`, `factor_relevancia`, `metodos_relevancia`, `matrices`, `kpi`, `entidades`, `objetos_valor`, `interfaces`.
- `src/aplicacion`: casos de uso: `orquestador` (simulación), `gestor_relevancia`, `gestor_historial`, `diagnostico`, `validador`, `explicador` (justificación en lenguaje natural), `asistente` (respuestas sin internet por palabras clave), `reutilizacion`, `contexto`.
- `src/infraestructura`: `repositorio_postgres` / `repositorio_memoria`, `adaptador_json`, `exportador` (PDF/Excel/CSV/JSON/PNG), `graficas` (matplotlib sin Tk), `lector_historico`, `preferencias`, `logger`.
- `src/presentacion`: `tema` (paletas claro/oscuro y escala para celular), `movil` (reacomodo en pantallas angostas), `widgets/` (botón redondeado, tarjeta, sección desplegable, ayuda «?», semáforo), `paginas/` (una por pestaña), `panel_asistente`, `tour`, `main_window`.
- `main.py` es la raíz de composición: elige PostgreSQL o memoria y construye el `Contexto`.

## Flujo de simulación
`VentanaPrincipal.ejecutar` → `volcar()` de las páginas a `DatosEntrada` → hilo → `OrquestadorSimulacion.ejecutar_simulacion` (Montecarlo con números aleatorios comunes por semilla; Márkov semanal; Poisson para pérdidas; Galton-Watson para el plan) → cola → página Resultados.
`KPI = rendimiento · relevancia / (1 + esfuerzo)`. Éxito: ≥ 40 % del rendimiento base; viable: éxito ≥ 10 %.

## Persistencia
`db/init.sql` crea `cultivos`, `configuraciones`, `historial_simulaciones`, `datos_externos`, `matrices_markov`, `configuraciones_relevancia` y `registros_campo`. La configuración completa de cada simulación se guarda dentro de `datos_deterministas._completo` para poder reutilizarla desde el Historial.

## Datos externos
`AdaptadorJSON` valida; la ventana vigila `SIEMBRA_ENTRADA` cada 3 s (por fecha de modificación). Ver `docs/integration_guide.md` (también en Ayuda).

## Preferencias
`~/.pronostico_siembra/preferencias.json` (o `$SIEMBRA_HOME`): tema, recorrido visto.

## Adaptación a celular
La interfaz se escribe una sola vez, pensada para escritorio. En pantallas angostas se adapta en tiempo de ejecución:

- `tema.configurar_pantalla(ventana)` decide si es celular. Lo es en Android (`sys.getandroidapilevel` o `ANDROID_ROOT`/`ANDROID_DATA`),
  cuando la pantalla mide menos de 900 px de ancho o cuando se fuerza con `SIEMBRA_MOVIL=1` (`0` lo desactiva). En modo celular fija
  `tk scaling` según el lado corto de la pantalla (`AJUSTE_ESCALA_MOVIL` / `SIEMBRA_ESCALA` lo afinan) y abre la ventana a pantalla
  completa. También calcula `FACTOR`, con el que `tema.px()` convierte medidas de escritorio en píxeles.
- `movil.reacomodar(raiz, x, ancho)` recorre los widgets visibles y cambia **solo lo que no cabe**, en este orden:
  1. rejillas de varias columnas → una columna;
  2. filas `pack(side=left/right)` → renglones, de lo más profundo a lo más externo;
  3. `wraplength` de las etiquetas al ancho disponible y columnas de `Treeview` encogidas.

  Un contenedor se excluye con `widget._sin_reflujo = True` (lo usa la matriz de Márkov, que se desplaza de lado).
- `VentanaPrincipal.programar_reflujo()` agrupa las peticiones y se dispara al mostrar una página, al cambiar el contenido de un
  `PaginaScroll` o al cambiar el ancho de la ventana. Un contador evita ciclos.
- `widgets/base.py`: `al_tocar()` activa los controles al **soltar** el dedo y solo si no hubo arrastre. `registrar_toques()` agrega
  desplazamiento con el dedo (`scan_mark`/`scan_dragto`), con gestos de rueda y con movimiento sin botón. `PaginaScroll` usa una barra
  gruesa en el celular.
- `tema.figura()` y `tema.lienzo()` ajustan las gráficas de matplotlib al ancho de la pantalla. Tienen en cuenta que en Linux el
  backend Tk ya multiplica por la escala.
- `tema.dialogo()` y `tema.ancho_texto()` abren los diálogos a pantalla completa con textos al ancho de la pantalla.

Compatibilidad con Pydroid 3 (en `main.py`): el comentario `#Pydroid run tkinter` activa el modo gráfico. `asegurar_msgcat()` carga
`msgcat` o una versión mínima antes de que ttkbootstrap la use. Los errores fatales se guardan en `error.txt`.

## Versión web
`web/` reutiliza `src/dominio` y la parte de `src/aplicacion` que usa la simulación. `web/empaquetar.py` los mete en `web/siembra.zip`
junto con `web/motor.py` (el puente). En el navegador, `motor.worker.js` carga Pyodide y numpy desde jsDelivr, descomprime el zip y
llama a `motor.simular()`, que devuelve JSON. La interfaz (`app.js`) dibuja con Chart.js. No hay servidor ni persistencia. Detalle y
publicación en Vercel: `docs/web.md`.

## Pruebas
`pytest --cov` (cobertura ≈ 96 %, sin el repositorio PostgreSQL). Las pruebas de interfaz necesitan pantalla (`xvfb-run`) y se omiten si no la hay. Para probar el modo celular: `SIEMBRA_MOVIL=1 xvfb-run -a -s "-screen 0 1080x2340x24" pytest tests/test_ui.py`.
