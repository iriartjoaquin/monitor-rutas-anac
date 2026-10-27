"""
Manual de uso para quien entra por primera vez. Se muestra como un desplegable arriba de cada sección.
"""
import streamlit as st

GENERAL = """
**¿Qué es esto?** Un monitor de los vuelos de pasajeros de Argentina con los datos oficiales de SINTA
(Ministerio de Turismo), que salen de los registros de ANAC. Tiene dos secciones, que elegís con los botones de arriba:

- **✈️ Cabotaje:** vuelos dentro de Argentina.
- **🌎 Internacional – América:** vuelos entre Argentina y el resto de América, de aerolíneas argentinas y extranjeras.

**¿De cuándo son los datos?** Desde enero de 2017 hasta el último mes que publicó la fuente (figura en la etiqueta
📅 de cada sección). Se actualizan solos todos los meses: la fuente publica entre el 10 y el 20 de cada mes el mes anterior,
así que siempre hay un mes y medio de atraso. Los datos se compararon contra los registros propios de ANAC y coinciden con
menos de 1% de diferencia.

**Palabras que vas a ver**
- **Frecuencias semanales:** vuelos por semana en cada sentido. Un vuelo diario ida y vuelta = 7.
- **Ocupación:** pasajeros ÷ asientos. Un avión con 180 asientos y 153 pasajeros va al 85%.
- **Participación o cuota:** parte de los pasajeros que lleva cada aerolínea. Los cambios de cuota se miden en
  **puntos porcentuales (pp)**: pasar de 20% a 23% es +3 pp.
- **HHI:** qué tan concentrado está un mercado, de 0 a 10.000. Más de 2.500 = concentrado (pocas aerolíneas se reparten casi todo);
  10.000 = una sola aerolínea.
- **Asientos-km y pasajeros-km:** asientos o pasajeros multiplicados por la distancia de la ruta. Sirven para comparar el tamaño
  real de las aerolíneas: no pesa lo mismo un pasajero a Ushuaia (o a Miami) que uno a Rosario (o a Montevideo).
- **Variación (Var. %):** casi siempre contra el **mismo período del año anterior**, para no confundir un cambio con la temporada.

**Trucos**
- Todas las tablas se **ordenan** tocando el título de una columna, y se pueden **agrandar** o **descargar** con los íconos
  que aparecen arriba a la derecha al pasar el mouse.
- En los gráficos podés **pasar el mouse** (o tocar, en el celular) para ver el número exacto, y **tocar un nombre de la leyenda**
  para ocultarlo o mostrarlo.
- Cada pestaña termina con una aclaración en letra chica que dice qué muestra y qué filtros respeta.
- **↺ Restablecer** vuelve todos los filtros a como estaban al entrar.
- **ℹ️ Metodología**, al final de cada sección, tiene todas las definiciones.
"""

CABOTAJE = """
**Paso 1: elegí qué querés mirar.** La página abre con **Analizar total país** activado (todo el cabotaje, en lo que va del año).
Para mirar algo puntual, desactivalo y elegí una o más:
- **Ruta (ida y vuelta):** por ejemplo *AEP (Aeroparque) ⇄ BRC (Bariloche)*, que suma los dos sentidos.
- **Aerolínea:** se puede combinar con todo lo demás, también con el total país.
- **Origen y destino:** para ver un sentido o todos los vuelos que salen o llegan a un aeropuerto. El botón **⇄** los da vuelta.
- **Desde / Hasta:** el período. Por defecto, del 1 de enero al último día publicado.

**Paso 2: tocá 🔍 Buscar vuelos.** Los filtros se aplican recién cuando tocás el botón. Arriba vas a ver el resumen del
período: pasajeros, vuelos, asientos, ocupación, pasajeros por vuelo y HHI.

**Paso 3: recorré las pestañas**
- **📊 Panorama:** lo primero que hay que mirar. Arranca con el **resumen del último mes publicado** (qué cambió contra el mismo
  mes del año pasado: quién agregó o sacó asientos, quién ganó cuota, qué aerolíneas empezaron o dejaron de volar cada ruta, qué
  rutas crecieron o cayeron y cuáles van más llenas o más vacías). Después, el mapa, la evolución de oferta y demanda, la
  evolución anual (en pasajeros, vuelos, ocupación, pasajeros-km o asientos-km) y el tamaño de los aviones.
- **⚖️ Competencia:** pasajeros y participación de cada aerolínea mes a mes, concentración (HHI) por año, ocupación por
  aerolínea, la tabla de desempeño (con asientos-km y pasajeros-km) y la comparación contra el año anterior.
- **🛬 Destinos y aeropuertos:** ranking de destinos, pasajeros por ciudad y **conectividad federal** (cuánto del tráfico
  no pasa por Buenos Aires).
- **🗺️ Rutas:** ranking de rutas con distancia, rutas activas, rutas con **un solo operador** (sin competencia) y el
  balance entre sentidos.
- **📅 Estacionalidad:** en qué meses sube y baja cada ruta (índice 100 = mes promedio del año).
- **📋 Datos y descargas:** la matriz mensual y la descarga del detalle en Excel o CSV.

**Ejemplos de preguntas que se responden rápido**
- *¿Cómo le fue a una aerolínea este mes?* → Elegila en **Aerolínea**, Buscar, y mirá el resumen del último mes en Panorama.
- *¿Quién compite en Aeroparque–Bariloche y quién gana?* → Elegí la ruta y andá a **Competencia**.
- *¿Qué rutas no tienen competencia?* → Total país y **Rutas → Dependencia de un solo operador**.
- *¿Cuándo es temporada alta en Ushuaia?* → Origen o destino USH y **Estacionalidad**.
"""

INTERNACIONAL = """
**Paso 1: filtros (se aplican solos, sin botón).** La página abre con todas las rutas entre Argentina y América, en lo que
va del año. Podés acotar por:
- **Región** y **País** del otro extremo (por ejemplo, Brasil).
- **Tipo de aerolínea:** argentinas, extranjeras de América o extranjeras de fuera de América (como Emirates o Turkish, que llegan
  a Argentina haciendo escala en otra ciudad de América).
- **Aerolínea** y **Aeropuerto argentino** (por ejemplo, solo Córdoba).
- **Desde / Hasta:** el período.
- **Ver las rutas como:** *Ciudad ⇄ ciudad* (el mercado: Buenos Aires junta Aeroparque, Ezeiza y El Palomar), *Aeropuerto argentino ⇄
  ciudad* o *Aeropuerto ⇄ aeropuerto* (para separar, por ejemplo, Galeão de Santos Dumont en Río). Cambia cómo se agrupan todas las tablas.

**Paso 2: recorré las pestañas**
- **📊 Panorama:** el **resumen del último mes publicado** (igual que en cabotaje, más la cuota argentina), el mapa, los pasajeros
  por tipo de aerolínea, la evolución anual y las puertas de entrada (cuánto tráfico usa aeropuertos del interior).
- **🛫 Ficha de ruta:** la tabla con todas las rutas y, abajo, la **ficha completa** de la que elijas: quién la vuela, con qué
  frecuencia y avión, cuánto vende cada uno frente a su oferta, vuelos por día de la semana, historia desde 2017, entradas y
  salidas de aerolíneas, estacionalidad y cuántos pasajeros salen y llegan cada mes.
- **🏢 Competidores:** ranking de aerolíneas (también en pasajeros-km), quién ganó y perdió cuota, el **análisis de una aerolínea**
  (sus rutas nuevas y cortadas, el cara a cara con otra aerolínea y su red en el mapa) y la **cuota argentina mes a mes**.
- **📦 Capacidad:** qué rutas van llenas sin que nadie agregue asientos (posible demanda insatisfecha) y cuáles tienen más oferta
  de la que se llena; quién agregó o sacó capacidad.
- **💡 Oportunidades:** rutas sin aerolíneas argentinas, destinos a los que solo se llega directo desde Buenos Aires, rutas que más
  crecen y caen, y rutas nuevas y cortadas.
- **🏙️ Destinos:** ranking de países y de ciudades.
- **🔁 Escalas:** tramos que una aerolínea vuela fuera de su país: escalas (Air Canada vía São Paulo) o quinta libertad
  (LATAM Santiago–Buenos Aires–Miami).
- **📋 Datos:** descarga del detalle filtrado y la metodología.

**Ejemplos de preguntas que se responden rápido**
- *¿Qué pasó en el último mes?* → **Panorama**, arriba de todo.
- *¿Cómo está Buenos Aires–Río y quién la vuela?* → **Ficha de ruta**, elegila en la lista (podés escribir para buscarla).
- *¿Dónde crece un competidor?* → **Competidores → Análisis de una aerolínea**, y compararla con la tuya.
- *¿Dónde podría faltar capacidad?* → **Capacidad**, rutas llenas, y **Oportunidades**.

**Para tener en cuenta**
- **JetSMART** aparece separada en **JetSMART Argentina** (cuenta como argentina) y **JetSMART Chile**, con datos de ANAC.
- La fuente **no tiene** tarifas, número de vuelo, tipo de avión, conexiones de los pasajeros ni la programación futura:
  todo lo que ves es lo que ya voló.
"""


def mostrar_manual(internacional):
    with st.expander("📖 ¿Primera vez? Cómo usar el monitor"):
        st.markdown(GENERAL)
        st.markdown("---")
        st.markdown("#### " + ("🌎 Cómo usar Internacional – América" if internacional else "✈️ Cómo usar Cabotaje"))
        st.markdown(INTERNACIONAL if internacional else CABOTAJE)
        st.caption("La otra sección tiene su propia guía: cambiá de sección con los botones de arriba.")
