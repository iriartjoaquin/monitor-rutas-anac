# Monitor de Rutas Aéreas de Argentina

Página web en Streamlit que muestra los vuelos de pasajeros de Argentina con datos oficiales: **cabotaje** y
**internacional dentro de América**. Frecuencias semanales, ocupación, participación por aerolínea, concentración (HHI),
asientos-km, mapas y un resumen fijo de "Qué cambió" en el último mes publicado.

- Página pública: https://monitor-rutas-anac-aqkgos7zqbvy7utelsx7mx.streamlit.app/ (`?seccion=internacional` abre la otra sección)
- Publicada en Streamlit Community Cloud desde la rama `main`: cada push a `main` se publica solo.
- Todos los textos van en castellano rioplatense, tratando de "vos". Los números van con formato argentino (1.234,5).

## Cómo se corre

```bash
pip install -r requirements.txt
streamlit run app.py
```

Pruebas: no hay suite de tests. Se prueba con `streamlit.testing.v1.AppTest` (abrir cada sección, tocar "Buscar vuelos")
y mirando la página en el navegador.

## De dónde salen los datos

- **SINTA** (Ministerio de Turismo), https://tableros.yvera.tur.ar/conectividad/, sección "Conectividad", armado con registros
  de ANAC. De ahí salen `conectividad_aerea.zip` (cabotaje, diario, desde 2017) e `internacional_america.zip`.
- **ANAC, aterrizajes y despegues** (datos.gob.ar): se usa para separar JetSMART Argentina de JetSMART Chile
  (`jetsmart_operador.csv`) y para controlar SINTA. Coinciden con menos de 1% de diferencia por mes. En ANAC, cada vuelo de cabotaje
  aparece dos veces (despegue y aterrizaje).
- **Agente mensual**: `.github/workflows/actualizar_datos.yml` corre del 10 al 20 de cada mes. Baja los datos nuevos, actualiza
  `novedades.json` y abre un issue "✈️ Qué cambió en …", que GitHub manda por mail al dueño del repositorio (un aviso por mes).
- **Regla**: la página nunca inventa ni simula datos. Si no hay base, muestra un error.

## Estructura

| Archivo | Qué es |
|---|---|
| `app.py` | Página principal: encabezado, selector de sección, toda la sección de cabotaje y utilidades compartidas (`UTILES`) |
| `internacional.py` | Sección Internacional – América (carga, separación de JetSMART y página) |
| `datos.py` | Lectura y limpieza de la base de cabotaje, sin Streamlit (la usan la página y el agente) |
| `novedades.py` / `generar_novedades.py` | Cálculo de "Qué cambió" y su guardado en `novedades.json` y `novedades_mail.md` |
| `mapas.py` | Mapa de rutas (Plotly Scattermap) |
| `manual.py` | Desplegable "¿Primera vez?" con el manual de uso |
| `actualizar_zip.py`, `verificar_zip.py`, `actualizar_jetsmart.py` | Scripts del agente mensual (descarga con Playwright y controles) |
| `*.zip`, `jetsmart_operador.csv`, `novedades.json` | Datos. Los genera el agente; no se editan a mano |
| `.streamlit/config.toml` | Tema de colores |

## No tocar sin preguntar

- **Los archivos de datos** (`*.zip`, `jetsmart_operador.csv`, `novedades.json`): solo los actualiza el agente.
- **El workflow** `.github/workflows/actualizar_datos.yml`: horarios, permisos y el aviso por mail.
- **Versiones fijas** en `requirements.txt` (streamlit 1.65.0, plotly 7.1.0, pandas 2.2.3).
- **Hacer `git push`**: publica la página al instante. Preguntar antes, salvo que me lo hayas pedido.
- **El alcance**: cabotaje más internacional dentro de América, datos desde 2017.
- **Decisiones ya tomadas**:
  - las dos secciones arrancan vacías hasta tocar "Buscar vuelos";
  - los filtros se aplican recién con "Buscar vuelos";
  - las tarjetas de arriba muestran números sin redondear;
  - no hay función "Mi aerolínea".
- **Memoria**: Streamlit Cloud gratis ya avisó una vez que se quedaba sin memoria (7/10/2026). Ojo con cargar más datos o copias
  de los DataFrames.

## Contexto del dueño

- La usa el dueño del repositorio y quizá alguna persona más; no es una página masiva.
- El repositorio sigue siendo público, y los avisos mensuales (issues) también.
- Solo el dueño maneja Streamlit Cloud y hace cambios en el repositorio.
- No hay datos ni aerolíneas que haya que ocultar.
- **El manual tiene tres copias**: `manual.py` (en la página), un Claude Doc (https://claude.ai/artifact/CFUEFtUVAgNKbsTbz5xJTu)
  y un Word que se manda por mail. Si cambia `manual.py`, hay que actualizar el Claude Doc y ofrecer mandar el Word nuevo.
- `.devcontainer` es la plantilla que trae Streamlit para editar desde GitHub Codespaces. No se usa, pero no molesta: se deja.
