import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Monitor de Conectividad Aérea",
    page_icon="✈️",
    layout="wide"
)

st.title("✈️ Monitor de Rutas Aéreas: Salta y Bariloche")
st.markdown("Visualización de pasajeros mensuales de cabotaje a partir de datos oficiales.")

# Función auxiliar para convertir números con formato argentino (1.234 -> 1234)
def limpiar_numero(serie):
    if serie.dtype == object:
        serie = serie.astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
    return pd.to_numeric(serie, errors='coerce').fillna(0)

@st.cache_data(ttl=86400)
def procesar_datos(origen_datos, archivo_subido=None):
    source = archivo_subido if archivo_subido is not None else origen_datos
    
    # Detección automática del separador (; o ,)
    try:
        df = pd.read_csv(source, sep=None, engine='python', dtype=str)
    except Exception:
        df = pd.read_csv(source, sep=';', dtype=str)

    df.columns = df.columns.str.strip().str.lower()

    # -------------------------------------------------------------
    # CASO 1: Archivo del Tablero SINTA / Yvera (como AEP SAL.csv)
    # -------------------------------------------------------------
    if 'empresa agrupada' in df.columns or ('ruta' in df.columns and 'clase de vuelo' not in df.columns):
        col_aerolinea = 'empresa agrupada' if 'empresa agrupada' in df.columns else ('aerolinea' if 'aerolinea' in df.columns else 'empresa')
        col_pasajeros = 'pasajeros' if 'pasajeros' in df.columns else [c for c in df.columns if 'pasajero' in c][0]
        col_vuelos = 'vuelos' if 'vuelos' in df.columns else [c for c in df.columns if 'vuelo' in c][0]
        col_ruta = 'ruta' if 'ruta' in df.columns else 'trayecto'

        df['pasajeros'] = limpiar_numero(df[col_pasajeros])
        df['vuelos'] = limpiar_numero(df[col_vuelos])

        col_ano = 'año' if 'año' in df.columns else ('anio' if 'anio' in df.columns else 'year')
        if col_ano in df.columns and 'mes' in df.columns:
            df['periodo'] = df[col_ano].astype(str) + " - " + df['mes'].astype(str)
        elif 'fecha' in df.columns:
            df['periodo'] = df['fecha'].astype(str)
        else:
            df['periodo'] = df['mes'].astype(str)

        resultado = df[[col_ruta, col_aerolinea, 'periodo', 'pasajeros', 'vuelos']].copy()
        resultado.columns = ['ruta', 'aerolinea', 'periodo', 'pasajeros', 'vuelos']
        return resultado

    # -------------------------------------------------------------
    # CASO 2: Archivo crudo vuelo por vuelo de ANAC (datos abiertos)
    # -------------------------------------------------------------
    filtro_cab = df['clase de vuelo'].astype(str).str.lower().str.contains('cabotaje', na=False)
    filtro_desp = df['tipo de movimiento'].astype(str).str.lower() == 'despegue'
    df = df[filtro_cab & filtro_desp].copy()

    mapa = {
        'AER': 'AEP', 'AEP': 'AEP',
        'EZE': 'EZE',
        'BAR': 'BRC', 'BRC': 'BRC',
        'SAL': 'SLA', 'SLA': 'SLA'
    }

    df['origen'] = df['aeropuerto'].astype(str).str.strip().str.upper().map(mapa)
    df['destino'] = df['origen / destino'].astype(str).str.strip().str.upper().map(mapa)

    rutas_validas = {
        frozenset(['AEP', 'BRC']): 'Aeroparque - Bariloche',
        frozenset(['AEP', 'SLA']): 'Aeroparque - Salta',
        frozenset(['EZE', 'BRC']): 'Ezeiza - Bariloche',
        frozenset(['EZE', 'SLA']): 'Ezeiza - Salta',
    }

    def asignar_ruta(row):
        return rutas_validas.get(frozenset([row['origen'], row['destino']]), None)

    df['ruta'] = df.apply(asignar_ruta, axis=1)
    df = df[df['ruta'].notna()].copy()

    col_empresa = 'aerolinea_nombre' if 'aerolinea_nombre' in df.columns else 'empresa'
    df['aerolinea'] = df[col_empresa].fillna('Otros')

    df['fecha_dt'] = pd.to_datetime(df['fecha'], errors='coerce', dayfirst=True)
    df['periodo'] = df['fecha_dt'].dt.strftime('%Y-%m')

    df['pasajeros'] = limpiar_numero(df['pasajeros'])

    agrupado = df.groupby(['periodo', 'ruta', 'aerolinea'], as_index=False).agg(
        pasajeros=('pasajeros', 'sum'),
        vuelos=('pasajeros', 'count')
    )
    return agrupado

# ---------------------------------------------------------
# INTERFAZ WEB
# ---------------------------------------------------------
st.sidebar.header("⚙️ Configuración")
metodo_carga = st.sidebar.radio("Fuente de los datos:", ["Subir archivo CSV manualmente", "URL oficial (ANAC)"])

archivo_subido = None
url_usar = ""

if metodo_carga == "Subir archivo CSV manualmente":
    archivo_subido = st.sidebar.file_uploader("Subí el archivo CSV:", type=['csv'])
else:
    url_usar = st.sidebar.text_input("Enlace al CSV directo:")

if metodo_carga == "Subir archivo CSV manualmente" and archivo_subido is None:
    st.info("👆 Por favor, subí tu archivo CSV en el panel de la izquierda.")
else:
    with st.spinner("Procesando datos..."):
        try:
            datos = procesar_datos(url_usar, archivo_subido)
            
            # Selector de Ruta
            rutas_disponibles = sorted(datos['ruta'].dropna().unique().tolist())
            ruta_elegida = st.selectbox("Seleccioná la ruta a analizar:", ["Todas las rutas"] + rutas_disponibles)

            if ruta_elegida != "Todas las rutas":
                datos_filtrados = datos[datos['ruta'] == ruta_elegida].copy()
            else:
                datos_filtrados = datos.copy()

            # KPIs
            st.divider()
            c1, c2, c3 = st.columns(3)
            tot_pax = datos_filtrados['pasajeros'].sum()
            tot_vue = datos_filtrados['vuelos'].sum()
            
            if not datos_filtrados.empty:
                lider = datos_filtrados.groupby('aerolinea')['pasajeros'].sum().idxmax()
            else:
                lider = "-"

            c1.metric("Pasajeros Totales", f"{tot_pax:,.0f}".replace(",", "."))
            c2.metric("Vuelos Totales", f"{tot_vue:,.0f}".replace(",", "."))
            c3.metric("Aerolínea Líder", lider)

            # Gráficos
            st.subheader("📈 Pasajeros por Mes y Aerolínea")
            fig_barras = px.bar(
                datos_filtrados,
                x="periodo",
                y="pasajeros",
                color="aerolinea",
                barmode="group",
                labels={"periodo": "Período", "pasajeros": "Pasajeros", "aerolinea": "Aerolínea"},
                template="plotly_white"
            )
            st.plotly_chart(fig_barras, use_container_width=True)

            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.subheader("🥧 Cuota de Mercado (% Pasajeros)")
                fig_pie = px.pie(datos_filtrados, values="pasajeros", names="aerolinea", hole=0.4)
                st.plotly_chart(fig_pie, use_container_width=True)

            with col_g2:
                st.subheader("🛫 Total de Vuelos")
                fig_vuelos = px.bar(datos_filtrados, x="aerolinea", y="vuelos", color="aerolinea")
                st.plotly_chart(fig_vuelos, use_container_width=True)

            st.subheader("📋 Datos Detallados")
            st.dataframe(datos_filtrados, use_container_width=True)

        except Exception as e:
            st.error(f"Error al procesar el archivo: {e}")
