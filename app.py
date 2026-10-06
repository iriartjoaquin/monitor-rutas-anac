import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(
    page_title="Monitor de Rutas",
    page_icon="✈️",
    layout="wide"
)

st.title("✈️ Monitor de Rutas")
st.markdown("Visualización y análisis de conectividad aérea de cabotaje a partir de datos oficiales.")

# Diccionario para ordenar meses en español
meses_orden = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
    'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
}

def limpiar_numero(serie):
    if serie.dtype == object:
        serie = serie.astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
    return pd.to_numeric(serie, errors='coerce').fillna(0)

@st.cache_data(ttl=86400)
def procesar_datos(origen_datos, archivo_subido=None):
    source = archivo_subido if archivo_subido is not None else origen_datos
    
    try:
        df = pd.read_csv(source, sep=None, engine='python', dtype=str)
    except Exception:
        df = pd.read_csv(source, sep=';', dtype=str)

    df.columns = df.columns.str.strip().str.lower()

    # -------------------------------------------------------------
    # CASO 1: Archivo del Tablero SINTA / Yvera (ej. AEP SAL.csv)
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
            df['num_mes'] = df['mes'].astype(str).str.strip().str.lower().map(meses_orden).fillna(1).astype(int)
            df['num_ano'] = pd.to_numeric(df[col_ano], errors='coerce').fillna(2025).astype(int)
            df['periodo_orden'] = df['num_ano'] * 100 + df['num_mes']
            df['periodo'] = df[col_ano].astype(str) + " - " + df['mes'].astype(str).str.capitalize()
            df = df.sort_values(by='periodo_orden', ascending=True)
        elif 'fecha' in df.columns:
            df['periodo'] = df['fecha'].astype(str)
        else:
            df['periodo'] = df['mes'].astype(str)

        resultado = df[[col_ruta, col_aerolinea, 'periodo', 'pasajeros', 'vuelos']].copy()
        resultado.columns = ['ruta', 'aerolinea', 'periodo', 'pasajeros', 'vuelos']
        return resultado

    # -------------------------------------------------------------
    # CASO 2: Archivo crudo de ANAC
    # -------------------------------------------------------------
    filtro_cab = df['clase de vuelo'].astype(str).str.lower().str.contains('cabotaje', na=False)
    filtro_desp = df['tipo de movimiento'].astype(str).str.lower() == 'despegue'
    df = df[filtro_cab & filtro_desp].copy()

    mapa = {
        'AER': 'AEP', 'AEP': 'AEP', 'EZE': 'EZE',
        'BAR': 'BRC', 'BRC': 'BRC', 'SAL': 'SLA', 'SLA': 'SLA'
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
    return agrupado.sort_values(by='periodo', ascending=True)

# ---------------------------------------------------------
# INTERFAZ Y FILTROS
# ---------------------------------------------------------
st.sidebar.header("📁 Fuente de Datos")
metodo_carga = st.sidebar.radio("Cargar desde:", ["Subir archivo CSV manualmente", "URL oficial (ANAC)"])

archivo_subido = None
url_usar = ""

if metodo_carga == "Subir archivo CSV manualmente":
    archivo_subido = st.sidebar.file_uploader("Subí tu archivo CSV:", type=['csv'])
else:
    url_usar = st.sidebar.text_input("Enlace al CSV directo:")

if metodo_carga == "Subir archivo CSV manualmente" and archivo_subido is None:
    st.info("👆 Por favor, subí tu archivo CSV desde el panel de la izquierda para comenzar.")
else:
    with st.spinner("Cargando información..."):
        try:
            datos = procesar_datos(url_usar, archivo_subido)
            
            # Cálculo de promedio de pasajeros por vuelo
            datos['pax_por_vuelo'] = (datos['pasajeros'] / datos['vuelos']).replace([np.inf, -np.inf], 0).round(1)

            st.sidebar.divider()
            st.sidebar.header("🔍 Filtros de Análisis")

            # 1. Filtro de Rutas (Múltiples)
            rutas_disponibles = sorted(datos['ruta'].dropna().unique().tolist())
            rutas_seleccionadas = st.sidebar.multiselect(
                "Rutas a incluir:",
                options=rutas_disponibles,
                default=rutas_disponibles[:3] if len(rutas_disponibles) >= 3 else rutas_disponibles
            )

            # 2. Filtro de Fechas / Períodos
            periodos_ordenados = list(dict.fromkeys(datos['periodo'].tolist()))
            if len(periodos_ordenados) > 1:
                rango_periodo = st.sidebar.select_slider(
                    "Rango de Fechas / Períodos:",
                    options=periodos_ordenados,
                    value=(periodos_ordenados[0], periodos_ordenados[-1])
                )
                idx_ini = periodos_ordenados.index(rango_periodo[0])
                idx_fin = periodos_ordenados.index(rango_periodo[1])
                periodos_filtrados = periodos_ordenados[idx_ini:idx_fin + 1]
            else:
                periodos_filtrados = periodos_ordenados

            # 3. Filtro de Aerolíneas
            aerolineas_disponibles = sorted(datos['aerolinea'].dropna().unique().tolist())
            aerolineas_seleccionadas = st.sidebar.multiselect(
                "Aerolíneas:",
                options=aerolineas_disponibles,
                default=aerolineas_disponibles
            )

            # 4. Selector de métrica y gráfico
            st.sidebar.divider()
            st.sidebar.header("📊 Opciones Visuales")
            metrica = st.sidebar.selectbox(
                "Métrica a graficar:",
                ["Pasajeros", "Vuelos", "Pasajeros por Vuelo"]
            )
            col_metrica = "pasajeros" if metrica == "Pasajeros" else ("vuelos" if metrica == "Vuelos" else "pax_por_vuelo")

            tipo_grafico = st.sidebar.radio("Estilo de gráfico:", ["Barras agrupadas", "Barras apiladas", "Líneas de tendencia"])

            # Aplicar filtros
            df_view = datos[
                datos['ruta'].isin(rutas_seleccionadas) &
                datos['periodo'].isin(periodos_filtrados) &
                datos['aerolinea'].isin(aerolineas_seleccionadas)
            ].copy()

            if df_view.empty:
                st.warning("No hay datos para la combinación de filtros seleccionada.")
            else:
                # KPIs principales
                st.divider()
                k1, k2, k3, k4 = st.columns(4)
                total_pax = df_view['pasajeros'].sum()
                total_vue = df_view['vuelos'].sum()
                prom_pax = round(total_pax / total_vue, 1) if total_vue > 0 else 0
                lider = df_view.groupby('aerolinea')['pasajeros'].sum().idxmax()

                k1.metric("Pasajeros Totales", f"{total_pax:,.0f}".replace(",", "."))
                k2.metric("Vuelos Totales", f"{total_vue:,.0f}".replace(",", "."))
                k3.metric("Promedio Pax / Vuelo", f"{prom_pax}")
                k4.metric("Aerolínea Líder", lider)

                st.divider()

                # Gráfico principal
                barmode_val = "group" if tipo_grafico == "Barras agrupadas" else "stack"

                if tipo_grafico == "Líneas de tendencia":
                    fig_principal = px.line(
                        df_view,
                        x="periodo",
                        y=col_metrica,
                        color="aerolinea",
                        markers=True,
                        title=f"Evolución temporal de {metrica}",
                        labels={"periodo": "Período", col_metrica: metrica, "aerolinea": "Aerolínea"},
                        template="plotly_white"
                    )
                else:
                    fig_principal = px.bar(
                        df_view,
                        x="periodo",
                        y=col_metrica,
                        color="aerolinea",
                        barmode=barmode_val,
                        title=f"Distribución mensual de {metrica}",
                        labels={"periodo": "Período", col_metrica: metrica, "aerolinea": "Aerolínea"},
                        template="plotly_white"
                    )
                st.plotly_chart(fig_principal, use_container_width=True)

                # Si hay más de una ruta, mostrar comparativa entre rutas
                if len(rutas_seleccionadas) > 1:
                    st.subheader("🗺️ Comparativa entre Rutas Seleccionadas")
                    comp_rutas = df_view.groupby('ruta', as_index=False)['pasajeros'].sum().sort_values(by='pasajeros', ascending=False)
                    fig_comp = px.bar(
                        comp_rutas,
                        x="ruta",
                        y="pasajeros",
                        color="ruta",
                        title="Pasajeros acumulados por Ruta en el período",
                        labels={"ruta": "Ruta", "pasajeros": "Total Pasajeros"},
                        template="plotly_white"
                    )
                    st.plotly_chart(fig_comp, use_container_width=True)

                # Sección inferior: Market share y tabla
                c_pie, c_tabla = st.columns([1, 1])
                with c_pie:
                    st.subheader("🥧 Cuota de Mercado (% Pasajeros)")
                    fig_pie = px.pie(df_view, values="pasajeros", names="aerolinea", hole=0.4)
                    st.plotly_chart(fig_pie, use_container_width=True)

                with c_tabla:
                    st.subheader("📋 Datos Filtrados")
                    st.dataframe(df_view, use_container_width=True, height=350)
                    
                    # Botón para descargar el Excel filtrado
                    csv_descarga = df_view.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Descargar datos filtrados (CSV)",
                        data=csv_descarga,
                        file_name="rutas_filtradas.csv",
                        mime="text/csv"
                    )

        except Exception as e:
            st.error(f"Error al procesar: {e}")
