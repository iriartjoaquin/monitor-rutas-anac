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

    cols_map = {c: c.strip().lower() for c in df.columns}
    df.rename(columns=cols_map, inplace=True)

    # 1. Aerolínea / Empresa
    cand_aero = [c for c in df.columns if any(p in c for p in ['aerolinea', 'empresa', 'operador', 'linea', 'compania'])]
    if cand_aero:
        df['aerolinea'] = df[cand_aero[0]].fillna('Otras').astype(str).str.strip()
    else:
        df['aerolinea'] = 'Todas las Aerolíneas (Total)'

    # 2. Pasajeros, Vuelos y Asientos (para Load Factor)
    cand_pax = [c for c in df.columns if 'pasajero' in c or 'pax' in c]
    df['pasajeros'] = limpiar_numero(df[cand_pax[0]]) if cand_pax else 0

    cand_vue = [c for c in df.columns if 'vuelo' in c or 'movimiento' in c]
    df['vuelos'] = limpiar_numero(df[cand_vue[0]]) if cand_vue else 1

    cand_asi = [c for c in df.columns if 'asiento' in c or 'plaza' in c]
    if cand_asi:
        df['asientos'] = limpiar_numero(df[cand_asi[0]])
    else:
        df['asientos'] = 0

    # 3. Fecha completa
    col_dia = next((c for c in df.columns if 'dia' in c or 'día' in c), None)
    col_mes = next((c for c in df.columns if 'mes' in c), None)
    col_ano = next((c for c in df.columns if 'año' in c or 'anio' in c or 'year' in c), None)

    if col_ano and col_mes and col_dia:
        num_mes = df[col_mes].astype(str).str.strip().str.lower().map(meses_orden).fillna(1).astype(int)
        num_dia = pd.to_numeric(df[col_dia], errors='coerce').fillna(1).astype(int)
        num_ano = pd.to_numeric(df[col_ano], errors='coerce').fillna(2025).astype(int)
        df['fecha'] = pd.to_datetime(dict(year=num_ano, month=num_mes, day=num_dia), errors='coerce')
    elif 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce', dayfirst=True)
    elif col_ano and col_mes:
        num_mes = df[col_mes].astype(str).str.strip().str.lower().map(meses_orden).fillna(1).astype(int)
        num_ano = pd.to_numeric(df[col_ano], errors='coerce').fillna(2025).astype(int)
        df['fecha'] = pd.to_datetime(dict(year=num_ano, month=num_mes, day=1), errors='coerce')
    else:
        df['fecha'] = pd.to_datetime(datetime.now())

    df['fecha'] = df['fecha'].fillna(pd.to_datetime(datetime.now()))
    df['periodo_mes'] = df['fecha'].dt.strftime('%Y-%m')

    # 4. Origen, Destino y Tramo
    col_dest = None
    for k in ['destino', 'aeropuerto_destino', 'aeropuerto de destino', 'destino_etiqueta_anac', 'localidad_destino', 'ciudad_destino', 'llegada']:
        if k in df.columns:
            col_dest = k
            break
    if not col_dest:
        for c in df.columns:
            if ('destino' in c or 'llegada' in c) and 'origen' not in c:
                col_dest = c
                break
    if not col_dest:
        for c in df.columns:
            if 'origen / destino' in c or 'origen_destino' in c or 'origen/destino' in c:
                col_dest = c
                break

    col_orig = None
    for k in ['origen', 'aeropuerto_origen', 'aeropuerto de origen', 'origen_etiqueta_anac', 'localidad_origen', 'ciudad_origen', 'salida']:
        if k in df.columns:
            col_orig = k
            break
    if not col_orig:
        for c in df.columns:
            if ('origen' in c or 'salida' in c) and 'destino' not in c:
                col_orig = c
                break
    if not col_orig:
        for c in df.columns:
            if 'aeropuerto' in c and c != col_dest:
                col_orig = c
                break

    cand_ruta = next((c for c in df.columns if 'ruta' in c or 'trayecto' in c), None)

    if col_orig and col_dest and col_orig != col_dest:
        df['origen'] = df[col_orig].astype(str).str.strip()
        df['destino'] = df[col_dest].astype(str).str.strip()
        df['tramo'] = df['origen'] + " ➔ " + df['destino']
        if not cand_ruta:
            df['ruta'] = df.apply(lambda r: " - ".join(sorted([r['origen'], r['destino']])), axis=1)
        else:
            df['ruta'] = df[cand_ruta].astype(str).str.strip()
    elif cand_ruta:
        df['ruta'] = df[cand_ruta].astype(str).str.strip()
        partes = df['ruta'].astype(str).str.split(r'\s*-\s*', expand=True)
        if partes.shape[1] >= 2:
            df['origen'] = partes[0].str.strip()
            df['destino'] = partes[1].str.strip()
            df['tramo'] = df['origen'] + " ➔ " + df['destino']
        else:
            df['origen'] = df['ruta']
            df['destino'] = df['ruta']
            df['tramo'] = df['ruta']
    else:
        df['origen'] = "General"
        df['destino'] = "General"
        df['tramo'] = "General"
        df['ruta'] = "General"

    return df

# ---------------------------------------------------------
# INTERFAZ Y FUENTE DE DATOS
# ---------------------------------------------------------
st.sidebar.header("📁 Fuente de Datos")

archivo_local_auto = "datos_actualizados.csv"
tiene_datos_auto = os.path.exists(archivo_local_auto)

opciones_fuente = ["Subir archivo CSV manualmente"]
if tiene_datos_auto:
    opciones_fuente.insert(0, "Datos automáticos en la nube")

metodo_carga = st.sidebar.radio("Cargar desde:", opciones_fuente)

archivo_a_procesar = None
if metodo_carga == "Datos automáticos en la nube":
    archivo_a_procesar = archivo_local_auto
else:
    archivo_a_procesar = st.sidebar.file_uploader("Subí tu archivo CSV de SINTA:", type=['csv'])

if archivo_a_procesar is None:
    st.info("👆 Por favor, subí tu archivo CSV desde el panel de la izquierda para comenzar.")
else:
    with st.spinner("Procesando información..."):
        try:
            datos = procesar_datos(archivo_a_procesar)

            st.sidebar.divider()
            st.sidebar.header("🔍 Filtros de Salida y Llegada")

            # 1. Origen
            origenes_disp = sorted(datos['origen'].dropna().unique().tolist())
            origenes_sel = st.sidebar.multiselect(
                "🛫 Origen (Salida):",
                options=origenes_disp,
                default=[]
            )

            # 2. Destino
            destinos_disp = sorted(datos['destino'].dropna().unique().tolist())
            destinos_sel = st.sidebar.multiselect(
                "🛬 Destino (Llegada):",
                options=destinos_disp,
                default=[]
            )

            # 3. Tramo directo
            tramos_disp = sorted(datos['tramo'].dropna().unique().tolist())
            tramos_sel = st.sidebar.multiselect(
                "🔄 Tramo directo (Origen ➔ Destino):",
                options=tramos_disp,
                default=[]
            )

            # 4. Fechas
            st.sidebar.divider()
            st.sidebar.subheader("📅 Fechas")
            fecha_min = datos['fecha'].min().date()
            fecha_max = datos['fecha'].max().date()

            c_f1, c_f2 = st.sidebar.columns(2)
            f_desde = c_f1.date_input("Desde:", value=fecha_min, min_value=fecha_min, max_value=fecha_max)
            f_hasta = c_f2.date_input("Hasta:", value=fecha_max, min_value=fecha_min, max_value=fecha_max)

            # 5. Aerolíneas
            aerolineas_disp = sorted(datos['aerolinea'].dropna().unique().tolist())
            aerolineas_sel = st.sidebar.multiselect(
                "Aerolíneas:",
                options=aerolineas_disp,
                default=[]
            )

            # Opciones de gráfico
            st.sidebar.divider()
            metrica = st.sidebar.selectbox("Métrica:", ["Pasajeros", "Vuelos", "Load Factor (%)", "Pasajeros por Vuelo"])
            tipo_grafico = st.sidebar.radio("Gráfico:", ["Barras agrupadas", "Barras apiladas", "Líneas"])

            # Aplicar filtros (vacío = no filtrar nada)
            cond_orig = datos['origen'].isin(origenes_sel) if origenes_sel else True
            cond_dest = datos['destino'].isin(destinos_sel) if destinos_sel else True
            cond_tramo = datos['tramo'].isin(tramos_sel) if tramos_sel else True
            cond_aero = datos['aerolinea'].isin(aerolineas_sel) if aerolineas_sel else True
            cond_fecha = (datos['fecha'].dt.date >= f_desde) & (datos['fecha'].dt.date <= f_hasta)

            df_filtro = datos[cond_orig & cond_dest & cond_tramo & cond_aero & cond_fecha].copy()
            df_filtro['pax_por_vuelo'] = (df_filtro['pasajeros'] / df_filtro['vuelos']).replace([np.inf, -np.inf], 0).round(1)
            df_filtro['load_factor'] = np.where(df_filtro['asientos'] > 0, (df_filtro['pasajeros'] / df_filtro['asientos']) * 100, 0).round(1)

            if df_filtro.empty:
                st.warning("No se encontraron registros para los filtros seleccionados.")
            else:
                # KPIs principales
                st.divider()
                k1, k2, k3, k4, k5 = st.columns(5)
                tot_pax = df_filtro['pasajeros'].sum()
                tot_vue = df_filtro['vuelos'].sum()
                tot_asi = df_filtro['asientos'].sum()
                prom_pax = round(tot_pax / tot_vue, 1) if tot_vue > 0 else 0
                
                # Load Factor Global Ponderado
                if tot_asi > 0:
                    lf_global = f"{round((tot_pax / tot_asi) * 100, 1)}%"
                else:
                    lf_global = "N/D"

                if df_filtro['aerolinea'].nunique() > 1:
                    lider = df_filtro.groupby('aerolinea')['pasajeros'].sum().idxmax()
                else:
                    lider = df_filtro['aerolinea'].iloc[0]

                k1.metric("Pasajeros Totales", f"{tot_pax:,.0f}".replace(",", "."))
                k2.metric("Vuelos Totales", f"{tot_vue:,.0f}".replace(",", "."))
                k3.metric("Load Factor", lf_global)
                k4.metric("Promedio Pax/Vuelo", f"{prom_pax}")
                k5.metric("Aerolínea Líder", lider)

                st.divider()

                # Agrupación temporal para el gráfico
                agrup_grafico = df_filtro.groupby(['periodo_mes', 'aerolinea', 'tramo'], as_index=False).agg(
                    pasajeros=('pasajeros', 'sum'),
                    vuelos=('vuelos', 'sum'),
                    asientos=('asientos', 'sum')
                )
                agrup_grafico['pax_por_vuelo'] = (agrup_grafico['pasajeros'] / agrup_grafico['vuelos']).round(1)
                agrup_grafico['load_factor'] = np.where(agrup_grafico['asientos'] > 0, 
                                                        (agrup_grafico['pasajeros'] / agrup_grafico['asientos']) * 100, 
                                                        0).round(1)

                if metrica == "Pasajeros":
                    col_met = "pasajeros"
                elif metrica == "Vuelos":
                    col_met = "vuelos"
                elif metrica == "Load Factor (%)":
                    col_met = "load_factor"
                else:
                    col_met = "pax_por_vuelo"

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

                # Comparativa entre Tramos
                if df_filtro['tramo'].nunique() > 1:
                    st.subheader("🛫 Comparativa por Sentido (Origen ➔ Destino)")
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
                    if df_filtro['aerolinea'].nunique() > 1:
                        st.subheader("🥧 Cuota de Mercado (% Pasajeros)")
                        fig_pie = px.pie(df_filtro, values="pasajeros", names="aerolinea", hole=0.4)
                        st.plotly_chart(fig_pie, use_container_width=True)
                    else:
                        st.subheader("🥧 Distribución por Tramo")
                        fig_pie = px.pie(df_filtro, values="pasajeros", names="tramo", hole=0.4)
                        st.plotly_chart(fig_pie, use_container_width=True)

                with col_c2:
                    st.subheader("📋 Detalle de Registros")
                    columnas_ver = [c for c in ['fecha', 'tramo', 'origen', 'destino', 'aerolinea', 'pasajeros', 'asientos', 'vuelos', 'load_factor'] if c in df_filtro.columns]
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
