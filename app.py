import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os
from datetime import datetime

st.set_page_config(
    page_title="Monitor de Rutas",
    page_icon="✈️",
    layout="wide"
)

st.title("✈️ Monitor de Rutas")
st.markdown("Visualización y análisis de conectividad aérea de cabotaje a partir de datos oficiales.")

meses_orden = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
    'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
}

def limpiar_numero(serie):
    if serie.dtype == object:
        serie = serie.astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
    return pd.to_numeric(serie, errors='coerce').fillna(0)

@st.cache_data(ttl=3600)
def procesar_datos(source):
    try:
        df = pd.read_csv(source, sep=None, engine='python', dtype=str)
    except Exception:
        df = pd.read_csv(source, sep=';', dtype=str)

    df.columns = df.columns.str.strip().str.lower()

    # Identificación de columnas
    col_aerolinea = 'empresa agrupada' if 'empresa agrupada' in df.columns else ('aerolinea_nombre' if 'aerolinea_nombre' in df.columns else 'aerolinea')
    col_pasajeros = 'pasajeros' if 'pasajeros' in df.columns else [c for c in df.columns if 'pasajero' in c][0]
    col_vuelos = 'vuelos' if 'vuelos' in df.columns else [c for c in df.columns if 'vuelo' in c][0]
    col_ruta = 'ruta' if 'ruta' in df.columns else ('trayecto' if 'trayecto' in df.columns else None)

    df['pasajeros'] = limpiar_numero(df[col_pasajeros])
    df['vuelos'] = limpiar_numero(df[col_vuelos])
    df['aerolinea'] = df[col_aerolinea].fillna('Otros')

    # 1. Construcción de Fecha completa (Día, Mes, Año)
    col_dia = 'día' if 'día' in df.columns else ('dia' if 'dia' in df.columns else None)
    col_mes = 'mes' if 'mes' in df.columns else None
    col_ano = 'año' if 'año' in df.columns else ('anio' if 'anio' in df.columns else 'year')

    if col_ano and col_mes and col_dia:
        num_mes = df[col_mes].astype(str).str.strip().str.lower().map(meses_orden).fillna(1).astype(int)
        num_dia = pd.to_numeric(df[col_dia], errors='coerce').fillna(1).astype(int)
        num_ano = pd.to_numeric(df[col_ano], errors='coerce').fillna(2025).astype(int)
        df['fecha'] = pd.to_datetime(dict(year=num_ano, month=num_mes, day=num_dia))
    elif 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce', dayfirst=True)
    elif col_ano and col_mes:
        num_mes = df[col_mes].astype(str).str.strip().str.lower().map(meses_orden).fillna(1).astype(int)
        num_ano = pd.to_numeric(df[col_ano], errors='coerce').fillna(2025).astype(int)
        df['fecha'] = pd.to_datetime(dict(year=num_ano, month=num_mes, day=1))
    else:
        df['fecha'] = pd.to_datetime(datetime.now())

    # 2. Origen, Destino y Tramo (diferenciación por sentido)
    col_orig = 'origen' if 'origen' in df.columns else ('aeropuerto' if 'aeropuerto' in df.columns else None)
    col_dest = 'destino' if 'destino' in df.columns else ('origen / destino' if 'origen / destino' in df.columns else None)

    if col_orig and col_dest:
        df['origen'] = df[col_orig].astype(str).str.strip()
        df['destino'] = df[col_dest].astype(str).str.strip()
        df['tramo'] = df['origen'] + " ➔ " + df['destino']
        if not col_ruta:
            df['ruta'] = df.apply(lambda r: " - ".join(sorted([r['origen'], r['destino']])), axis=1)
    else:
        df['origen'] = "N/D"
        df['destino'] = "N/D"
        df['tramo'] = df[col_ruta] if col_ruta else "Ruta General"
        if not col_ruta:
            df['ruta'] = df['tramo']

    df['periodo_mes'] = df['fecha'].dt.strftime('%Y-%m')
    return df

# ---------------------------------------------------------
# INTERFAZ Y FUENTE DE DATOS
# ---------------------------------------------------------
st.sidebar.header("📁 Datos de Origen")

archivo_local_auto = "datos_actualizados.csv"
tiene_datos_auto = os.path.exists(archivo_local_auto)

opciones_fuente = ["Subir archivo CSV manualmente"]
if tiene_datos_auto:
    opciones_fuente.insert(0, "Datos automáticos en la nube")

metodo_carga = st.sidebar.radio("Fuente:", opciones_fuente)

archivo_a_procesar = None
if metodo_carga == "Datos automáticos en la nube":
    archivo_a_procesar = archivo_local_auto
else:
    archivo_a_procesar = st.sidebar.file_uploader("Subí tu archivo CSV de SINTA:", type=['csv'])

if archivo_a_procesar is None:
    st.info("👆 Por favor, subí tu archivo CSV en el panel de la izquierda para comenzar.")
else:
    with st.spinner("Procesando datos y calendarios..."):
        try:
            datos = procesar_datos(archivo_a_procesar)

            st.sidebar.divider()
            st.sidebar.header("🔍 Filtros de Análisis")

            # 1. Filtro de Rutas (Multiselect: 1, 2, ..., N rutas)
            rutas_disponibles = sorted(datos['ruta'].dropna().unique().tolist())
            rutas_seleccionadas = st.sidebar.multiselect(
                "Rutas a incluir (podés elegir varias):",
                options=rutas_disponibles,
                default=rutas_disponibles[:2] if len(rutas_disponibles) >= 2 else rutas_disponibles
            )

            # 2. Filtro de Tramo / Sentido específico (Origen ➔ Destino)
            tramos_disponibles = sorted(datos[datos['ruta'].isin(rutas_seleccionadas)]['tramo'].dropna().unique().tolist())
            tramos_seleccionados = st.sidebar.multiselect(
                "Sentido del vuelo (Origen ➔ Destino):",
                options=tramos_disponibles,
                default=tramos_disponibles
            )

            # 3. Filtro de Fecha con dos Calendarios
            st.sidebar.subheader("📅 Rango de Fechas")
            fecha_min = datos['fecha'].min().date()
            fecha_max = datos['fecha'].max().date()

            c_f1, c_f2 = st.sidebar.columns(2)
            f_desde = c_f1.date_input("Desde:", value=fecha_min, min_value=fecha_min, max_value=fecha_max)
            f_hasta = c_f2.date_input("Hasta:", value=fecha_max, min_value=fecha_min, max_value=fecha_max)

            # 4. Filtro de Aerolíneas
            aerolineas_disponibles = sorted(datos['aerolinea'].dropna().unique().tolist())
            aerolineas_seleccionadas = st.sidebar.multiselect(
                "Aerolíneas:",
                options=aerolineas_disponibles,
                default=aerolineas_disponibles
            )

            # 5. Opciones visuales
            st.sidebar.divider()
            metrica = st.sidebar.selectbox("Métrica para el gráfico:", ["Pasajeros", "Vuelos", "Pasajeros por Vuelo"])
            tipo_grafico = st.sidebar.radio("Tipo de gráfico:", ["Barras agrupadas", "Barras apiladas", "Líneas"])

            # Aplicar filtros cruzados
            df_filtro = datos[
                (datos['ruta'].isin(rutas_seleccionadas)) &
                (datos['tramo'].isin(tramos_seleccionados)) &
                (datos['aerolinea'].isin(aerolineas_seleccionadas)) &
                (datos['fecha'].dt.date >= f_desde) &
                (datos['fecha'].dt.date <= f_hasta)
            ].copy()

            df_filtro['pax_por_vuelo'] = (df_filtro['pasajeros'] / df_filtro['vuelos']).replace([np.inf, -np.inf], 0).round(1)

            if df_filtro.empty:
                st.warning("No se encontraron registros para los filtros seleccionados.")
            else:
                # Métricas principales (KPIs)
                st.divider()
                k1, k2, k3, k4 = st.columns(4)
                tot_pax = df_filtro['pasajeros'].sum()
                tot_vue = df_filtro['vuelos'].sum()
                prom_pax = round(tot_pax / tot_vue, 1) if tot_vue > 0 else 0
                lider = df_filtro.groupby('aerolinea')['pasajeros'].sum().idxmax()

                k1.metric("Pasajeros Totales", f"{tot_pax:,.0f}".replace(",", "."))
                k2.metric("Vuelos Totales", f"{tot_vue:,.0f}".replace(",", "."))
                k3.metric("Promedio Pax / Vuelo", f"{prom_pax}")
                k4.metric("Aerolínea Líder", lider)

                st.divider()

                # Agrupación temporal para el gráfico
                col_met = "pasajeros" if metrica == "Pasajeros" else ("vuelos" if metrica == "Vuelos" else "pax_por_vuelo")
                agrup_grafico = df_filtro.groupby(['periodo_mes', 'aerolinea', 'tramo'], as_index=False).agg(
                    pasajeros=('pasajeros', 'sum'),
                    vuelos=('vuelos', 'sum')
                )
                agrup_grafico['pax_por_vuelo'] = (agrup_grafico['pasajeros'] / agrup_grafico['vuelos']).round(1)

                st.subheader(f"📈 Evolución de {metrica}")
                barmode_val = "group" if tipo_grafico == "Barras agrupadas" else "stack"

                if tipo_grafico == "Líneas":
                    fig_main = px.line(
                        agrup_grafico, x="periodo_mes", y=col_met, color="aerolinea",
                        markers=True, labels={"periodo_mes": "Mes", col_met: metrica, "aerolinea": "Aerolínea"},
                        template="plotly_white"
                    )
                else:
                    fig_main = px.bar(
                        agrup_grafico, x="periodo_mes", y=col_met, color="aerolinea",
                        barmode=barmode_val, labels={"periodo_mes": "Mes", col_met: metrica, "aerolinea": "Aerolínea"},
                        template="plotly_white"
                    )
                st.plotly_chart(fig_main, use_container_width=True)

                # Comparativa entre Tramos (Ida vs Vuelta)
                if len(tramos_seleccionados) > 1:
                    st.subheader("🛫 Comparativa por Tramo / Sentido")
                    comp_tramos = df_filtro.groupby('tramo', as_index=False)['pasajeros'].sum().sort_values(by='pasajeros', ascending=False)
                    fig_tramos = px.bar(
                        comp_tramos, x="tramo", y="pasajeros", color="tramo",
                        labels={"tramo": "Tramo", "pasajeros": "Pasajeros Totales"},
                        template="plotly_white"
                    )
                    st.plotly_chart(fig_tramos, use_container_width=True)

                # Cuota de mercado y tabla
                col_c1, col_c2 = st.columns([1, 1])
                with col_c1:
                    st.subheader("🥧 Cuota de Mercado (% Pasajeros)")
                    fig_pie = px.pie(df_filtro, values="pasajeros", names="aerolinea", hole=0.4)
                    st.plotly_chart(fig_pie, use_container_width=True)

                with col_c2:
                    st.subheader("📋 Detalle de Registros")
                    columnas_ver = [c for c in ['fecha', 'tramo', 'aerolinea', 'pasajeros', 'vuelos', 'pax_por_vuelo'] if c in df_filtro.columns]
                    st.dataframe(df_filtro[columnas_ver].sort_values(by='fecha', ascending=False), use_container_width=True, height=350)
                    
                    csv_descarga = df_filtro.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Descargar datos filtrados (CSV)",
                        data=csv_descarga,
                        file_name="rutas_filtradas.csv",
                        mime="text/csv"
                    )

        except Exception as e:
            st.error(f"Error al procesar: {e}")
