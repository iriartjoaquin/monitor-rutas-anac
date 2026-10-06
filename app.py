import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración de página
st.set_page_config(
    page_title="Monitor de Conectividad Aérea: Salta y Bariloche",
    page_icon="✈️",
    layout="wide"
)

st.title("✈️ Monitor de Rutas Aéreas: Salta y Bariloche")
st.markdown("Visualización de pasajeros mensuales de cabotaje a partir de datos oficiales de la **ANAC**.")

# ---------------------------------------------------------
# 1. CARGA Y PROCESAMIENTO DE DATOS
# ---------------------------------------------------------
@st.cache_data(ttl=86400) # Guarda en memoria por 24 hs
def procesar_datos(origen_datos, archivo_subido=None):
    if archivo_subido is not None:
        df = pd.read_csv(archivo_subido, sep=';', low_memory=False)
    else:
        df = pd.read_csv(origen_datos, sep=';', low_memory=False)

    df.columns = df.columns.str.strip().str.lower()

    # Filtro de cabotaje y solo despegues (evita doble cómputo de pasajeros)
    filtro_cab = df['clase de vuelo'].astype(str).str.lower().str.contains('cabotaje', na=False)
    filtro_desp = df['tipo de movimiento'].astype(str).str.lower() == 'despegue'
    df = df[filtro_cab & filtro_desp].copy()

    # Mapeo de códigos de aeropuertos (FAA / IATA)
    mapa = {
        'AER': 'AEP', 'AEP': 'AEP',
        'EZE': 'EZE',
        'BAR': 'BRC', 'BRC': 'BRC',
        'SAL': 'SLA', 'SLA': 'SLA'
    }

    df['origen'] = df['aeropuerto'].astype(str).str.strip().str.upper().map(mapa)
    df['destino'] = df['origen / destino'].astype(str).str.strip().str.upper().map(mapa)

    # Identificación de las 4 rutas
    rutas_validas = {
        frozenset(['AEP', 'BRC']): 'AEP - BRC',
        frozenset(['AEP', 'SLA']): 'AEP - SLA',
        frozenset(['EZE', 'BRC']): 'EZE - BRC',
        frozenset(['EZE', 'SLA']): 'EZE - SLA',
    }

    def asignar_ruta(row):
        return rutas_validas.get(frozenset([row['origen'], row['destino']]), None)

    df['ruta'] = df.apply(asignar_ruta, axis=1)
    df = df[df['ruta'].notna()].copy()

    # Normalizar empresa / aerolínea
    col_empresa = 'aerolinea_nombre' if 'aerolinea_nombre' in df.columns else 'empresa'
    df['aerolinea'] = df[col_empresa].fillna('Otros')

    # Fechas a período mensual
    df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce', dayfirst=True)
    df['periodo'] = df['fecha'].dt.strftime('%Y-%m')

    # Agrupación final
    agrupado = df.groupby(['periodo', 'ruta', 'aerolinea'], as_index=False).agg(
        pasajeros=('pasajeros', 'sum'),
        vuelos=('pasajeros', 'count')
    )
    return agrupado.sort_values(by=['periodo', 'pasajeros'], ascending=[True, False])

# ---------------------------------------------------------
# 2. PANEL LATERAL (CONFIGURACIÓN)
# ---------------------------------------------------------
st.sidebar.header("⚙️ Configuración de Datos")

url_defecto = "https://datos.transporte.gob.ar/dataset/aterrizajes-y-despegues-procesados-por-la-administracion-nacional-de-aviacion-civil-anac/archivo/0706775f-bed9-46e7-aac5-726d7e72e429"
metodo_carga = st.sidebar.radio("Fuente de los datos:", ["URL oficial automática (ANAC)", "Subir archivo CSV manualmente"])

archivo_subido = None
url_usar = url_defecto

if metodo_carga == "Subir archivo CSV manualmente":
    archivo_subido = st.sidebar.file_uploader("Subí el archivo CSV de ANAC:", type=['csv'])
else:
    url_usar = st.sidebar.text_input("Enlace al CSV de ANAC:", value=url_defecto)

# ---------------------------------------------------------
# 3. RENDERIZADO DEL DASHBOARD
# ---------------------------------------------------------
if metodo_carga == "Subir archivo CSV manualmente" and archivo_subido is None:
    st.info("👆 Por favor, subí el archivo CSV en el panel de la izquierda para comenzar.")
else:
    with st.spinner("Cargando y procesando datos oficiales..."):
        try:
            datos = procesar_datos(url_usar, archivo_subido)
            
            # Filtro de Rutas
            rutas_disponibles = sorted(datos['ruta'].unique().tolist())
            ruta_elegida = st.selectbox("Seleccioná la ruta a analizar:", ["Todas las rutas"] + rutas_disponibles)

            if ruta_elegida != "Todas las rutas":
                datos_filtrados = datos[datos['ruta'] == ruta_elegida].copy()
            else:
                datos_filtrados = datos.copy()

            # Métricas resumen (KPIs)
            st.divider()
            c1, c2, c3 = st.columns(3)
            total_pasajeros = datos_filtrados['pasajeros'].sum()
            total_vuelos = datos_filtrados['vuelos'].sum()
            aerolinea_lider = datos_filtrados.groupby('aerolinea')['pasajeros'].sum().idxmax()

            c1.metric("Pasajeros Totales", f"{total_pasajeros:,.0f}".replace(",", "."))
            c2.metric("Vuelos Totales", f"{total_vuelos:,.0f}".replace(",", "."))
            c3.metric("Aerolínea Líder", aerolinea_lider)

            # Gráfico de evolución mensual
            st.subheader("📈 Pasajeros Mensuales por Aerolínea")
            fig_barras = px.bar(
                datos_filtrados,
                x="periodo",
                y="pasajeros",
                color="aerolinea",
                barmode="group",
                labels={"periodo": "Mes", "pasajeros": "Cantidad de Pasajeros", "aerolinea": "Aerolínea"},
                template="plotly_white"
            )
            st.plotly_chart(fig_barras, use_container_width=True)

            # Cuota de Mercado (% Market Share)
            st.subheader("🥧 Cuota de Mercado acumulada")
            fig_torta = px.pie(
                datos_filtrados,
                values="pasajeros",
                names="aerolinea",
                hole=0.4
            )
            st.plotly_chart(fig_torta, use_container_width=True)

            # Tabla descargable
            st.subheader("📋 Tabla de Datos Detallada")
            st.dataframe(datos_filtrados, use_container_width=True)

        except Exception as e:
            st.error(f"Ocurrió un error al procesar la información: {e}")
