# Manual de usuario

## Primeros pasos
Abre **Inicio**. Puedes pulsar «Ejecutar con valores sugeridos» y obtener una recomendación sin tocar nada, o «Comenzar simulación» para revisar tus datos.
Si te pierdes, pulsa «Recorrido de 1 minuto», el «?» junto a cualquier término o **✦ Preguntar** (arriba a la derecha).

## Datos
Secciones plegadas (se abre una a la vez): Cultivo, Suelo y manejo, Clima, Estado de la planta, Eventos raros y Plan de temporadas.
- *Estado de la planta*: matrices de Márkov. Cada fila debe sumar 1 (la suma se pone en rojo si no); usa «Normalizar filas». Puedes agregar o quitar estados y guardar la matriz en la base de datos.
- *Plan de temporadas*: de 1 a 10. Con más de 10 se avisa que es menos confiable. Si los descendientes por planta son menos de 1, el cultivo se extingue y se te avisa.

## Relevancia
Los cinco deslizadores (agua, temperatura, humedad, pH, nutrientes) siempre están a la vista. «Calcularlo automáticamente» ofrece:
Valores sugeridos, Ley del Mínimo, tu histórico (CSV/Excel con columna «rendimiento» y mínimo 10 filas), modo experto (comparaciones por pares, con revisión de consistencia) y diario de campo (mínimo 5 registros).
En «Mis configuraciones guardadas» puedes guardar, cargar, duplicar, eliminar, descargar e importar perfiles (JSON).

## Simulación y resultados
Pulsa «Ejecutar simulación». En **Resultados** verás primero la fecha y el motivo; «¿Por qué esta fecha?» amplía. Bajo «¿Quieres ver más?» están Gráficas, Comparación (frente a sembrar hoy y en 30 días), Riesgos, Temporadas y Exportar (PDF, Excel, CSV, JSON, PNG).
Si ninguna fecha es segura, se muestra «No encontré una fecha segura» con sugerencias.

## Historial
Busca por nombre y por fecha; renombra, elimina, reutiliza la configuración o compara dos simulaciones lado a lado.

## Datos de un simulador
Inicio → *Datos de un simulador (JSON)*: «Cargar JSON» o la carpeta de entrada. El semáforo de la barra superior: verde (datos recibidos), amarillo (más de 5 minutos sin datos), rojo (último archivo inválido). Clic en él para ver el registro.

## Tema
El botón ☾/☀ cambia entre claro y oscuro (se recuerda).

## En el celular
En Android (con Pydroid 3) la app se adapta sola. El menú queda debajo del título, todo se ve en una columna y el contenido se desplaza
deslizando el dedo. Los botones responden al soltar el dedo, y el «?» muestra su ayuda al tocarlo. Instalación y solución de problemas
en [android_pydroid.md](android_pydroid.md).

## Aviso
Las recomendaciones son informativas; en agricultura real consulta a un agrónomo.
