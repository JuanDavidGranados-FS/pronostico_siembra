# Ejecutar Siembrate en Android (Pydroid 3)

La aplicación corre en celulares Android con **Pydroid 3**, que incluye Python, Tkinter y un gestor de librerías. Al detectar Android,
la interfaz entra en **modo celular**:

- abre a pantalla completa;
- ajusta el tamaño del texto a la pantalla;
- reacomoda en una columna lo que no cabe;
- permite desplazar el contenido con el dedo.

> Otras apps como *Python CodePad* **no sirven**: no traen Tkinter, así que la ventana no puede abrir.

## 1. Requisitos

- Android con **Pydroid 3** instalado desde Google Play.
- Permiso de almacenamiento concedido a Pydroid (lo pide la primera vez).
- El proyecto en una carpeta normal del celular, por ejemplo `Descargas/pronostico_siembra`.

## 2. Copiar el proyecto al celular

1. Descarga el proyecto en `.zip`: en GitHub, **Code → Download ZIP**.
2. Descomprímelo con la app **Files** (o "Archivos"): mantén presionado el `.zip` → **Extraer** → en **Descargas**.
3. Revisa que, al entrar a la carpeta, se vean directamente `main.py`, `src` y `requirements-android.txt`. Si hay una carpeta dentro de
   otra, usa la de adentro.

## 3. Instalar las librerías

Abre Pydroid → menú ☰ → **Terminal**:

```bash
cd /storage/emulated/0/Download/pronostico_siembra
mkdir -p logs
pip install -r requirements-android.txt
```

Luego instala las librerías científicas desde el menú ☰ → **Pip**. Marca **Use prebuilt libraries repository** e instala una por una:

1. `numpy`
2. `scipy`
3. `matplotlib`

> ⚠️ **No ejecutes `pip install --upgrade pip`** aunque Pydroid lo sugiera. En Pydroid la actualización puede quedar a medias y dañar
> pip. Si ya pasó, la solución es Ajustes de Android → Apps → Pydroid 3 → Almacenamiento → **Borrar datos**. El proyecto no se borra,
> porque está en Descargas.

`psycopg2` (PostgreSQL) **no se instala en Android**. No hace falta: sin él, la app usa almacenamiento en memoria automáticamente.

## 4. Ejecutar

1. En Pydroid toca el ícono de carpeta 📂 y abre **Download → pronostico_siembra → `main.py`**.
2. Toca el botón amarillo ▶️.

**Debe correrse desde el editor, no desde la terminal.** Pydroid solo abre ventanas gráficas cuando el programa se lanza con ▶️. La
primera línea de `main.py` (`#Pydroid run tkinter`) le indica que use el modo gráfico.

## 5. Ajustar el tamaño de la interfaz

Si todo se ve muy pequeño o muy grande, edita `src/presentacion/tema.py`:

```python
AJUSTE_ESCALA_MOVIL = 1.0   # súbelo (1.2) si se ve pequeño; bájalo (0.85) si se ve grande
```

## 6. Solución de problemas

| Síntoma | Causa y solución |
|---|---|
| `GUI applications cannot be ran from terminal` | Se ejecutó desde la terminal. Ábrelo en el editor y usa ▶️. |
| Pantalla negra y vuelve al editor sin mostrar nada | La app se cerró por un error. Revísalo con `cat /storage/emulated/0/Download/pronostico_siembra/error.txt`. |
| `invalid command name "::msgcat::mcmset"` | El Tcl de Pydroid no trae `msgcat`. `main.py` ya lo resuelve: asegúrate de tener la versión actual. |
| `No se usará PostgreSQL (No module named 'psycopg2')` | Es normal en Android: la app usa memoria. |
| `No se pudo crear el archivo de log logs/app.log` | Falta la carpeta `logs`: `mkdir -p logs` dentro del proyecto. |
| `pg_config executable not found` al instalar | Se intentó instalar `psycopg2-binary`. Usa `requirements-android.txt`, que no lo incluye. |
| `ImportError: cannot import name 'get_runnable_pip'` | pip quedó dañado por una actualización a medias. Borra los datos de Pydroid (ver paso 3). |
| No se desplaza al deslizar | Desliza sobre texto o tarjetas, no sobre una casilla de texto ni un deslizador. Prueba con dos dedos o arrastra la barra de la derecha. |

## Cómo funciona el modo celular

El detalle técnico está en el [manual técnico](manual_tecnico.md#adaptación-a-celular). En resumen, `src/presentacion/tema.py` detecta
el celular y fija la escala. `src/presentacion/movil.py` reacomoda **solo lo que no cabe**, así que las páginas siguen escritas una vez
para el escritorio.
