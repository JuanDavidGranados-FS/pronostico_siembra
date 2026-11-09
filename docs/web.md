# Versión web (Vercel + código QR)

La carpeta `web/` es la **misma aplicación de escritorio**, pero en el navegador y sin instalar nada. Tiene las mismas 7 pestañas,
el mismo diseño, el asistente, el recorrido guiado y el tema claro/oscuro. Sirve para que cualquier persona la pruebe en su celular o
PC escaneando un código QR.

## Cómo funciona

- Es una página **estática** (HTML, CSS y JavaScript). En Vercel no hay servidor que mantener y es gratis.
- Todo el cálculo lo hace el **mismo código Python del proyecto**: `src/dominio`, `src/aplicacion` y los repositorios, gráficas y
  exportes de `src/infraestructura`. Corre **dentro del navegador** con [Pyodide](https://pyodide.org) (Python compilado a
  WebAssembly).
- Las gráficas son las mismas de escritorio (matplotlib). matplotlib se descarga solo la primera vez que se abre una gráfica o se
  exporta un archivo; openpyxl se descarga solo para Excel.
- El historial, las configuraciones de relevancia, el diario de campo y las matrices guardadas se guardan **en el propio
  dispositivo** (almacenamiento del navegador). Ningún dato sale de él.
- La primera visita tarda unos segundos mientras se descarga Python. El navegador lo guarda, así que las siguientes cargan rápido.

| Archivo | Para qué sirve |
|---|---|
| `web/index.html`, `estilos.css`, `app.js` | Interfaz: réplica de `src/presentacion`. Las páginas y los widgets llevan los mismos nombres (`Seccion`, `Segmentado`, `Deslizador`…). |
| `web/motor.worker.js` | Carga Pyodide en segundo plano para que la pantalla no se congele. Carga matplotlib y openpyxl solo cuando se necesitan. |
| `web/motor.py` | Hace el papel de `main.py` + la ventana: arma el contexto (orquestador, gestores, repositorios) y ofrece las operaciones de las páginas. |
| `web/siembra.zip` | El código Python que corre en el navegador (más la guía de integración). **Se genera** con `web/empaquetar.py`. |
| `web/manifest.webmanifest`, `icono*.png` | Permite instalarla en la pantalla de inicio del celular. |
| `web/vercel.json`, `.vercelignore` | Configuración de Vercel (sitio estático, sin compilación). |

Diferencias con la app de escritorio, por ser una página web:

- **Datos de un simulador (JSON):** se cargan con el botón «Cargar JSON». No hay carpeta de entrada vigilada.
- **Base de datos:** en lugar de PostgreSQL se usa el almacenamiento del navegador, con las últimas 40 simulaciones. Si se borran los
  datos del navegador, se borra el historial.
- **Ventanas aparte** (comparación, renombrar): se muestran sobre la misma página.

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
