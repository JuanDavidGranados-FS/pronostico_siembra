# Guía de integración

Esta guía es para quien desarrolla un simulador, un mod o cualquier programa que quiera enviar datos a Siembra.

## 1. Cómo llegan los datos

Siembra recibe un archivo JSON (UTF-8) de dos maneras:

- Carpeta de entrada: copia el archivo en la carpeta que se muestra en Inicio → Datos de un simulador. Se revisa cada 3 segundos. Por defecto es `~/.pronostico_siembra/entrada` (se cambia con la variable `SIEMBRA_ENTRADA`).
- Botón «Cargar JSON»: en Inicio, para elegir un archivo a mano.

## 2. Semáforo de conexión

- Verde: llegó un archivo válido.
- Amarillo: han pasado más de 5 minutos sin datos nuevos.
- Rojo: el último archivo era inválido.

Haz clic en el semáforo para abrir el registro de recepciones (hora, archivo, resultado y motivo del error).

## 3. Campos obligatorios

El objeto raíz debe tener `cultivo`, `deterministas` y `estocasticos`. Todo lo demás es opcional: si falta, se usan los valores sugeridos.

| Campo | Contenido |
|---|---|
| `cultivo` | `nombre`, `dias_crecimiento`, `temp_min`, `temp_max`, `requerimiento_agua`, `resistencia_plagas`, `rendimiento_base` |
| `deterministas` | `fecha` (AAAA-MM-DD), `ph`, `nitrogeno`, `fosforo`, `potasio`, `resistencia`, `agua` |
| `estocasticos` | `temperatura`, `lluvia` y `humedad`; cada una con `tipo` (`normal`, `uniforme` o `triangular`) y `parametros` |
| `pesos` (opcional) | Factor de Relevancia: `agua`, `temperatura`, `humedad`, `ph`, `nutrientes` (0 a 100) |
| `eventos_raros` (opcional) | Por evento: `tasa_mensual` y `perdida` |
| `plan` (opcional) | `temporadas`, `media_descendientes`, `plantas_iniciales`, `capacidad`, `agotamiento_suelo` |

Parámetros según el tipo: `normal` usa `media` y `std`; `uniforme` usa `min` y `max`; `triangular` usa `min`, `moda` y `max`.

## 4. Ejemplo mínimo

```json
{
  "cultivo": {"nombre": "Maíz", "dias_crecimiento": 120, "temp_min": 15, "temp_max": 32,
              "requerimiento_agua": 5, "resistencia_plagas": 60, "rendimiento_base": 8},
  "deterministas": {"fecha": "2026-11-01", "ph": 6.5, "nitrogeno": 100, "fosforo": 50,
                    "potasio": 100, "resistencia": 60, "agua": 1},
  "estocasticos": {
    "temperatura": {"tipo": "normal", "parametros": {"media": 22, "std": 3}},
    "lluvia": {"tipo": "triangular", "parametros": {"min": 0, "moda": 4, "max": 15}},
    "humedad": {"tipo": "uniforme", "parametros": {"min": 50, "max": 85}}
  }
}
```

## 5. Errores comunes

- «Falta el campo obligatorio»: revisa `cultivo`, `deterministas` y `estocasticos`.
- «JSON inválido»: comas sobrantes o comillas simples. Valida el archivo con cualquier validador JSON.
- «Contenido inválido»: un número escrito como texto, o un parámetro que no corresponde al tipo de distribución.
- El archivo se ve bien pero no cambia nada: Siembra solo reprocesa un archivo cuando cambia su fecha de modificación.

## 6. Recomendaciones

- Escribe el archivo completo en un nombre temporal y renómbralo al final, para que Siembra no lea un archivo a medias.
- Envía datos nuevos al menos cada 5 minutos si quieres mantener el semáforo en verde.
- Usa punto como separador decimal.
