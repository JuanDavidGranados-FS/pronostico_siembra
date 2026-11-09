# Versión web (Vercel + código QR)

La carpeta `web/` es una versión liviana de Siembrate que se abre desde el navegador, sin instalar nada. Sirve para que cualquier
persona la pruebe en su celular o PC escaneando un código QR.

## Cómo funciona

- Es una página **estática** (HTML, CSS y JavaScript). En Vercel no hay servidor que mantener y es gratis.
- El cálculo lo hace el **mismo código Python del proyecto** (`src/dominio` y `src/aplicacion`). Corre **dentro del navegador** con
  [Pyodide](https://pyodide.org) (Python compilado a WebAssembly) y numpy.
- Ningún dato sale del dispositivo: no hay base de datos ni envíos a internet, aparte de descargar la página y Pyodide.
- La primera visita tarda unos segundos mientras se descarga Python. El navegador lo guarda, así que las siguientes cargan rápido.

| Archivo | Para qué sirve |
|---|---|
| `web/index.html`, `estilos.css`, `app.js` | Interfaz: Inicio, Datos, Resultados (gráficas, comparación, riesgos, temporadas) y asistente. |
| `web/motor.worker.js` | Carga Pyodide y el motor en segundo plano, para que la pantalla no se congele mientras simula. |
| `web/motor.py` | Puente entre la página y el orquestador: arma los datos y devuelve el resultado en JSON. |
| `web/siembra.zip` | El código Python que corre en el navegador. **Se genera** con `web/empaquetar.py`. |
| `web/vendor/chart.umd.min.js` | Chart.js 4.6.1 (licencia MIT) para las gráficas. |
| `web/manifest.webmanifest`, `icono*.png` | Permite instalarla en la pantalla de inicio del celular. |
| `web/vercel.json`, `.vercelignore` | Configuración de Vercel (sitio estático, sin compilación). |

Comparada con la app de escritorio, la versión web no tiene historial, exportes, matrices de Márkov editables ni carga de JSON. Usa
los valores sugeridos de esas partes.

## Publicarla en Vercel (una sola vez)

1. Entra a **[vercel.com](https://vercel.com)** → **Sign Up** → **Continue with GitHub**. Usa la cuenta donde está el repositorio.
2. Toca **Add New… → Project**.
3. Busca **`pronostico_siembra`** y toca **Import**. Si no aparece, toca **Adjust GitHub App Permissions** y dale acceso a ese repositorio.
4. En **Root Directory** toca **Edit** y elige la carpeta **`web`**. Este paso es importante.
5. **Framework Preset:** *Other*. No cambies nada más: no hay comando de compilación.
6. Toca **Deploy**. En menos de un minuto te da una dirección como `https://pronostico-siembra.vercel.app`.
7. (Opcional) En **Settings → Domains** puedes cambiarla por una más corta, por ejemplo `siembrate.vercel.app`, si está libre.

Desde ese momento, **cada cambio que se suba a la rama `main` se publica solo**.

## Código QR para que los usuarios la prueben

Con la dirección final de Vercel:

```bash
pip install "qrcode[pil]"
python -c "import qrcode; qrcode.make('https://TU-DIRECCION.vercel.app').save('qr_siembrate.png')"
```

Imprime el `qr_siembrate.png` en el póster o muéstralo en pantalla. Los usuarios:

1. Abren la **cámara** del celular y apuntan al código (en Android también sirve Google Lens).
2. Tocan el enlace que aparece.
3. Esperan unos segundos la primera vez y tocan **«Probar con valores sugeridos»**.
4. Si quieren tenerla como app: en Chrome, menú ⋮ → **Agregar a la pantalla principal**. En iPhone (Safari): **Compartir → Agregar a
   inicio**.

Requisitos: un navegador actualizado (Chrome, Safari, Edge o Firefox) e internet para la primera carga.

## Mantenimiento

Si cambias algo de `src/dominio`, `src/aplicacion` o `web/motor.py`, vuelve a generar el paquete y súbelo:

```bash
python web/empaquetar.py
git add web/siembra.zip
```

La prueba `tests/test_web.py::test_zip_actualizado` falla si se te olvida. Si cambias el paquete, sube también el número `VERSION`
en `web/motor.worker.js`, para que los navegadores descarguen el nuevo y no usen el guardado.

Para probarla en el PC sin publicarla:

```bash
cd web
python -m http.server 8000
# abre http://localhost:8000
```
