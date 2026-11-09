# Manual técnico

## Capas
- `src/dominio`: matemática y entidades puras (numpy): `markov`, `montecarlo`, `poisson`, `galton_watson`, `factor_relevancia`, `metodos_relevancia`, `matrices`, `kpi`, `entidades`, `objetos_valor`, `interfaces`.
- `src/aplicacion`: casos de uso: `orquestador` (simulación), `gestor_relevancia`, `gestor_historial`, `diagnostico`, `validador`, `explicador` (justificación en lenguaje natural), `asistente` (respuestas sin internet por palabras clave), `reutilizacion`, `contexto`.
- `src/infraestructura`: `repositorio_postgres` / `repositorio_memoria`, `adaptador_json`, `exportador` (PDF/Excel/CSV/JSON/PNG), `graficas` (matplotlib sin Tk), `lector_historico`, `preferencias`, `logger`.
- `src/presentacion`: `tema` (paletas claro/oscuro), `widgets/` (botón redondeado, tarjeta, sección desplegable, ayuda «?», semáforo), `paginas/` (una por pestaña), `panel_asistente`, `tour`, `main_window`.
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

## Pruebas
`pytest --cov` (cobertura ≈ 96 %, sin el repositorio PostgreSQL). Las pruebas de interfaz necesitan pantalla (`xvfb-run`) y se omiten si no la hay.
