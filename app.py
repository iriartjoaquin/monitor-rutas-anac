import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os
import re
from datetime import datetime

st.set_page_config(
    page_title="Monitor de Rutas",
    page_icon="✈️",
    layout="wide"
)

st.title("✈️ Monitor de Rutas")
st.markdown("Visualización y análisis de conectividad aérea de cabotaje a partir de datos oficiales.")

# Mapeo exhaustivo de nombres de aeropuertos a código IATA y ciudad
AEROPUERTOS_INFO = {
    'AEP': {'codigo': 'AEP', 'ciudad': 'Aeroparque', 'keywords': ['AEROPARQUE', 'JORGE NEWBERY', 'BUENOS AIRES', 'CABA', 'AER']},
    'EZE': {'codigo': 'EZE', 'ciudad': 'Ezeiza', 'keywords': ['EZEIZA', 'PISTARINI', 'MINISTRO PISTARINI', 'EZE']},
    'EPA': {'codigo': 'EPA', 'ciudad': 'El Palomar', 'keywords': ['PALOMAR', 'EPA']},
    'FDO': {'codigo': 'FDO', 'ciudad': 'San Fernando', 'keywords': ['SAN FERNANDO', 'FDO']},
    'BRC': {'codigo': 'BRC', 'ciudad': 'Bariloche', 'keywords': ['BARILOCHE', 'SAN CARLOS DE BARILOCHE', 'BRC', 'BAR', 'CANDELARIA']},
    'SLA': {'codigo': 'SLA', 'ciudad': 'Salta', 'keywords': ['SALTA', 'GUEMES', 'GÜEMES', 'MARTIN MIGUEL', 'SLA', 'SAL']},
    'COR': {'codigo': 'COR', 'ciudad': 'Córdoba', 'keywords': ['CORDOBA', 'CÓRDOBA', 'TARAVELLA', 'PAJAS BLANCAS', 'COR', 'CBA']},
    'MDZ': {'codigo': 'MDZ', 'ciudad': 'Mendoza', 'keywords': ['MENDOZA', 'PLUMERILLO', 'GABRIELLI', 'MDZ', 'DOZ']},
    'IGR': {'codigo': 'IGR', 'ciudad': 'Iguazú', 'keywords': ['IGUAZU', 'IGUAZÚ', 'CATARATAS', 'PUERTO IGUAZU', 'IGR', 'IGU']},
    'JUJ': {'codigo': 'JUJ', 'ciudad': 'Jujuy', 'keywords': ['JUJUY', 'SAN SALVADOR DE JUJUY', 'HORACIO GUZMAN', 'HORACIO GUZMÁN', 'JUJ']},
    'NQN': {'codigo': 'NQN', 'ciudad': 'Neuquén', 'keywords': ['NEUQUEN', 'NEUQUÉN', 'PRESIDENTE PERON', 'PRESIDENTE PERÓN', 'NQN', 'NEU']},
    'TUC': {'codigo': 'TUC', 'ciudad': 'Tucumán', 'keywords': ['TUCUMAN', 'TUCUMÁN', 'BENJAMIN MATIENZO', 'BENJAMÍN MATIENZO', 'SAN MIGUEL DE TUCUMAN', 'TUC']},
    'FTE': {'codigo': 'FTE', 'ciudad': 'El Calafate', 'keywords': ['CALAFATE', 'ARMANDO TOLA', 'TOLA', 'FTE', 'CAL']},
    'USH': {'codigo': 'USH', 'ciudad': 'Ushuaia', 'keywords': ['USHUAIA', 'MALVINAS ARGENTINAS', 'USH', 'USU']},
    'CRD': {'codigo': 'CRD', 'ciudad': 'Comodoro Rivadavia', 'keywords': ['COMODORO', 'COMODORO RIVADAVIA', 'ENRIQUE MOSCONI', 'GENERAL MOSCONI', 'CRD', 'CRV']},
    'REL': {'codigo': 'REL', 'ciudad': 'Trelew', 'keywords': ['TRELEW', 'ALMIRANTE ZAR', 'REL', 'TRE']},
    'PMY': {'codigo': 'PMY', 'ciudad': 'Puerto Madryn', 'keywords': ['MADRYN', 'PUERTO MADRYN', 'TEHUELCHE', 'PMY']},
    'MDQ': {'codigo': 'MDQ', 'ciudad': 'Mar del Plata', 'keywords': ['MAR DEL PLATA', 'PIAZZOLLA', 'PIAZZOLA', 'ASTOR', 'MDQ', 'MDP']},
    'BHI': {'codigo': 'BHI', 'ciudad': 'Bahía Blanca', 'keywords': ['BAHIA BLANCA', 'BAHÍA BLANCA', 'ESPORA', 'COMANDANTE ESPORA', 'BHI', 'BCA']},
    'ROS': {'codigo': 'ROS', 'ciudad': 'Rosario', 'keywords': ['ROSARIO', 'ISLAS MALVINAS', 'ROS']},
    'SFN': {'codigo': 'SFN', 'ciudad': 'Santa Fe', 'keywords': ['SANTA FE', 'SAUCE VIEJO', 'SFN']},
    'PRA': {'codigo': 'PRA', 'ciudad': 'Paraná', 'keywords': ['PARANA', 'PARANÁ', 'URQUIZA', 'JUSTO JOSE', 'PRA', 'PAR']},
    'PSS': {'codigo': 'PSS', 'ciudad': 'Posadas', 'keywords': ['POSADAS', 'JOSE DE SAN MARTIN', 'JOSÉ DE SAN MARTÍN', 'PSS', 'POS']},
    'RES': {'codigo': 'RES', 'ciudad': 'Resistencia', 'keywords': ['RESISTENCIA', 'RES', 'SIS']},
    'CNQ': {'codigo': 'CNQ', 'ciudad': 'Corrientes', 'keywords': ['CORRIENTES', 'PIRAGINE NIVEYRO', 'PIRAGINE', 'CNQ']},
    'SDE': {'codigo': 'SDE', 'ciudad': 'Santiago del Estero', 'keywords': ['SANTIAGO DEL ESTERO', 'ARAGONES', 'ARAGONÉS', 'SDE']},
    'RHD': {'codigo': 'RHD', 'ciudad': 'Termas de Río Hondo', 'keywords': ['TERMAS', 'RIO HONDO', 'RÍO HONDO', 'RHD', 'TRH']},
    'UAQ': {'codigo': 'UAQ', 'ciudad': 'San Juan', 'keywords': ['SAN JUAN', 'DOMINGO FAUSTINO', 'SARMIENTO', 'UAQ', 'JUA']},
    'LUQ': {'codigo': 'LUQ', 'ciudad': 'San Luis', 'keywords': ['SAN LUIS', 'CESAR RAUL OJEDA', 'CÉSAR RAÚL OJEDA', 'OJEDA', 'LUQ', 'UIS']},
    'AFA': {'codigo': 'AFA', 'ciudad': 'San Rafael', 'keywords': ['SAN RAFAEL', 'GERMANO', 'GERMANÓ', 'AFA', 'SRA']},
    'IRJ': {'codigo': 'IRJ', 'ciudad': 'La Rioja', 'keywords': ['LA RIOJA', 'ALMANDOS', 'VICENTE ALMANDOS', 'ALMONACID', 'IRJ', 'LAR']},
    'CTC': {'codigo': 'CTC', 'ciudad': 'Catamarca', 'keywords': ['CATAMARCA', 'FELIPE VARELA', 'CORONEL FELIPE VARELA', 'CTC', 'CAT']},
    'FMA': {'codigo': 'FMA', 'ciudad': 'Formosa', 'keywords': ['FORMOSA', 'EL PUCU', 'EL PUCÚ', 'FMA', 'FSA']},
    'RGL': {'codigo': 'RGL', 'ciudad': 'Río Gallegos', 'keywords': ['RIO GALLEGOS', 'RÍO GALLEGOS', 'NORBERTO FERNANDEZ', 'NORBERTO FERNÁNDEZ', 'RGL', 'GAL']},
    'RGA': {'codigo': 'RGA', 'ciudad': 'Río Grande', 'keywords': ['RIO GRANDE', 'RÍO GRANDE', 'HERMES QUIJADA', 'RAMON TREJO', 'RAMÓN TREJO', 'TREJO NOEL', 'RGA', 'GRA']},
    'EQS': {'codigo': 'EQS', 'ciudad': 'Esquel', 'keywords': ['ESQUEL', 'PARODI', 'EQS']},
    'VDM': {'codigo': 'VDM', 'ciudad': 'Viedma', 'keywords': ['VIEDMA', 'EDGARDO CASTELLO', 'VDM', 'VIE']},
    'RSA': {'codigo': 'RSA', 'ciudad': 'Santa Rosa', 'keywords': ['SANTA ROSA', 'RSA', 'OSA']}
}

def resolver_aeropuerto(texto):
    if not texto or str(texto).strip() in ['', 'N/D', 'None', 'nan']:
        return "N/D", "Desconocido"
    t = str(texto).strip().upper()
    if t in AEROPUERTOS_INFO:
        info = AEROPUERTOS_INFO[t]
        return info['codigo'], info['ciudad']
    for code, info in AEROPUERTOS_INFO.items():
        for kw in info['keywords']:
            if len(kw) > 3 and kw in t:
                return info['codigo'], info['ciudad']
            if len(kw) <= 3 and re.search(r'\b' + re.escape(kw) + r'\b', t):
                return info['codigo'], info['ciudad']
    if len(t) == 3 and t.isalpha():
        return t, t
    limpio = t.replace('AEROPUERTO', '').replace('INT.', '').strip().title()
    return t[:4], limpio[:15]

meses_es = {
    1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
    7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'
}

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

    # 1. Aerolínea
    cand_aero = [c for c in df.columns if any(p in c for p in ['aerolinea', 'empresa', 'operador', 'linea', 'compania'])]
    if cand_aero:
        df['aerolinea'] = df[cand_aero[0]].fillna('Otras').astype(str).str.strip()
    else:
        df['aerolinea'] = 'Todas las Aerolíneas (Total)'

    # 2. Pasajeros, Vuelos y Asientos
    cand_pax = [c for c in df.columns if 'pasajero' in c or 'pax' in c]
    df['pasajeros'] = limpiar_numero(df[cand_pax[0]]) if cand_pax else 0

    cand_vue = [c for c in df.columns if 'vuelo' in c or 'movimiento' in c]
    df['vuelos'] = limpiar_numero(df[cand_vue[0]]) if cand_vue else 1

    cand_asi = [c for c in df.columns if 'asiento' in c or 'plaza' in c]
    df['asientos'] = limpiar_numero(df[cand_asi[0]]) if cand_asi else 0

    # 3. Fecha y Período ordenado en español
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
    
    # Período en español y orden cronológico
    df['mes_num'] = df['fecha'].dt.month
    df['ano_num'] = df['fecha'].dt.year
    df['periodo_orden'] = df['ano_num'] * 100 + df['mes_num']
    df['periodo_mes_es'] = df['mes_num'].map(meses_es) + " " + df['ano_num'].astype(str)

    # 4. Origen, Destino y Ruta
    col_dest = next((c for c in df.columns if any(k in c for k in ['destino', 'llegada']) and 'origen' not in c), None)
    col_orig = next((c for c in df.columns if any(k in c for k in ['origen', 'salida']) and 'destino' not in c), None)
    cand_ruta = next((c for c in df.columns if 'ruta' in c or 'trayecto' in c), None)

    if col_orig and col_dest:
        origen_raw = df[col_orig].astype(str)
        destino_raw = df[col_dest].astype(str)
    elif cand_ruta:
        partes = df[cand_ruta].astype(str).str.split(r'\s*-\s*', expand=True)
        if partes.shape[1] >= 2:
            origen_raw = partes[0]
            destino_raw = partes[1]
        else:
            origen_raw = df[cand_ruta]
            destino_raw = df[cand_ruta]
    else:
        origen_raw = pd.Series(["AEP"] * len(df))
        destino_raw = pd.Series(["BRC"] * len(df))

    res_orig = [resolver_aeropuerto(x) for x in origen_raw]
    res_dest = [resolver_aeropuerto(x) for x in destino_raw]

    df['origen_cod'] = [r[0] for r in res_orig]
    df['origen_ciu'] = [r[1] for r in res_orig]
    df['destino_cod'] = [r[0] for r in res_dest]
    df['destino_ciu'] = [r[1] for r in res_dest]

    df['origen_label'] = df['origen_cod'] + " (" + df['origen_ciu'] + ")"
    df['destino_label'] = df['destino_cod'] + " (" + df['destino_ciu'] + ")"
    df['tramo_label'] = df['origen_cod'] + " ➔ " + df['destino_cod'] + " (" + df['origen_ciu'] + " a " + df['destino_ciu'] + ")"

    def armar_ruta_bidireccional(row):
        pares = sorted([(row['origen_cod'], row['origen_ciu']), (row['destino_cod'], row['destino_ciu'])], key=lambda x: x[0])
        return f"{pares[0][0]} - {pares[1][0]} ({pares[0][1]} ⇄ {pares[1][1]})"

    df['ruta_label'] = df.apply(armar_ruta_bidireccional, axis=1)
    return df

# ---------------------------------------------------------
# INTERFAZ Y FUENTE DE DATOS
# ---------------------------------------------------------
st.sidebar.header("📁 Fuente de Datos")

st.sidebar.link_button(
    "🏛️ Secretaría de Transporte (ANAC)",
    "https://datos.transporte.gob.ar/dataset/aterrizajes-y-despegues-procesados-por-la-administracion-nacional-de-aviacion-civil-anac",
    use_container_width=True
)

st.sidebar.link_button(
    "📊 Tablero SINTA (Yvera)",
    "https://tableros.yvera.tur.ar/conectividad/",
    use_container_width=True
)

st.sidebar.divider()

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
    archivo_a_procesar = st.sidebar.file_uploader("Subí tu archivo CSV:", type=['csv'])

if archivo_a_procesar is None:
    st.info("👆 Por favor, subí tu archivo CSV desde el panel de la izquierda para comenzar.")
else:
    with st.spinner("Procesando datos y calendarios..."):
        try:
            datos = procesar_datos(archivo_a_procesar)

            st.sidebar.divider()
            st.sidebar.header("🔍 Filtros de Vuelo")

            # 1. RUTA
            rutas_disp = sorted(datos['ruta_label'].dropna().unique().tolist())
            rutas_sel = st.sidebar.multiselect(
                "🗺️ Ruta (Ida y Vuelta):",
                options=rutas_disp,
                default=[]
            )

            # 2. SALIDA
            origenes_disp = sorted(datos['origen_label'].dropna().unique().tolist())
            origenes_sel = st.sidebar.multiselect(
                "🛫 Aeropuerto de Salida (Origen):",
                options=origenes_disp,
                default=[]
            )

            # 3. LLEGADA
            destinos_disp = sorted(datos['destino_label'].dropna().unique().tolist())
            destinos_sel = st.sidebar.multiselect(
                "🛬 Aeropuerto de Llegada (Destino):",
                options=destinos_disp,
                default=[]
            )

            # 4. FECHAS
            st.sidebar.divider()
            st.sidebar.subheader("📅 Fechas")
            fecha_min = datos['fecha'].min().date()
            fecha_max = datos['fecha'].max().date()

            c_f1, c_f2 = st.sidebar.columns(2)
            f_desde = c_f1.date_input("Desde:", value=fecha_min, min_value=fecha_min, max_value=fecha_max)
            f_hasta = c_f2.date_input("Hasta:", value=fecha_max, min_value=fecha_min, max_value=fecha_max)

            # 5. AEROLÍNEAS
            aerolineas_disp = sorted(datos['aerolinea'].dropna().unique().tolist())
            aerolineas_sel = st.sidebar.multiselect("Aerolíneas:", options=aerolineas_disp, default=[])

            # Opciones de gráfico
            st.sidebar.divider()
            metrica = st.sidebar.selectbox("Métrica:", ["Pasajeros", "Vuelos", "Load Factor (%)", "Pasajeros por Vuelo"])
            tipo_grafico = st.sidebar.radio("Gráfico:", ["Barras agrupadas", "Barras apiladas", "Líneas"])

            with st.sidebar.expander("ℹ️ Guía de Códigos IATA"):
                st.caption(
                    "**AEP:** Aeroparque (Bs. As.) | **EZE:** Ezeiza\n\n"
                    "**BRC:** Bariloche | **SLA:** Salta | **JUJ:** Jujuy\n\n"
                    "**COR:** Córdoba | **MDZ:** Mendoza | **IGR:** Iguazú\n\n"
                    "**TUC:** Tucumán | **NQN:** Neuquén | **FTE:** El Calafate"
                )

            # Aplicar filtros
            cond_ruta = datos['ruta_label'].isin(rutas_sel) if rutas_sel else True
            cond_orig = datos['origen_label'].isin(origenes_sel) if origenes_sel else True
            cond_dest = datos['destino_label'].isin(destinos_sel) if destinos_sel else True
            cond_aero = datos['aerolinea'].isin(aerolineas_sel) if aerolineas_sel else True
            cond_fecha = (datos['fecha'].dt.date >= f_desde) & (datos['fecha'].dt.date <= f_hasta)

            df_filtro = datos[cond_ruta & cond_orig & cond_dest & cond_aero & cond_fecha].copy()
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
                
                lf_global = f"{round((tot_pax / tot_asi) * 100, 1)}%" if tot_asi > 0 else "N/D"

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

                # Pestañas Gráficos vs Cuadros
                tab_graficos, tab_cuadros = st.tabs(["📊 Gráficos Visuales", "📋 Cuadros Estadísticos"])

                # -------------------------------------------------------------
                # 1. GRÁFICOS
                # -------------------------------------------------------------
                with tab_graficos:
                    # Agrupar para gráfico y asegurar orden cronológico
                    agrup_grafico = df_filtro.groupby(['periodo_orden', 'periodo_mes_es', 'aerolinea'], as_index=False).agg(
                        pasajeros=('pasajeros', 'sum'),
                        vuelos=('vuelos', 'sum'),
                        asientos=('asientos', 'sum')
                    ).sort_values(by='periodo_orden')

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

                    # Lista estricta de meses en español para que no se coma ninguno
                    meses_eje = agrup_grafico['periodo_mes_es'].unique().tolist()

                    if tipo_grafico == "Líneas":
                        fig_main = px.line(
                            agrup_grafico, x="periodo_mes_es", y=col_met, color="aerolinea",
                            markers=True, labels={"periodo_mes_es": "Mes", col_met: metrica, "aerolinea": "Aerolínea"},
                            template="plotly_white"
                        )
                    else:
                        fig_main = px.bar(
                            agrup_grafico, x="periodo_mes_es", y=col_met, color="aerolinea",
                            barmode=barmode_val, labels={"periodo_mes_es": "Mes", col_met: metrica, "aerolinea": "Aerolínea"},
                            template="plotly_white"
                        )
                    
                    # Forzar categoría y rotación a -45° para que aparezcan TODOS los meses en español
                    fig_main.update_xaxes(
                        type='category',
                        categoryorder='array',
                        categoryarray=meses_eje,
                        tickangle=-45,
                        dtick=1
                    )
                    st.plotly_chart(fig_main, use_container_width=True)

                    # Gráficos secundarios
                    c_g1, c_g2 = st.columns(2)
                    with c_g1:
                        st.subheader("🛫 Pasajeros por Tramo (Sentido)")
                        comp_tramos = df_filtro.groupby('tramo_label', as_index=False)['pasajeros'].sum().sort_values(by='pasajeros', ascending=False)
                        fig_tramos = px.bar(
                            comp_tramos, x="tramo_label", y="pasajeros", color="tramo_label",
                            labels={"tramo_label": "Tramo", "pasajeros": "Pasajeros"},
                            template="plotly_white"
                        )
                        fig_tramos.update_xaxes(tickangle=-30)
                        st.plotly_chart(fig_tramos, use_container_width=True)

                    with c_g2:
                        if df_filtro['aerolinea'].nunique() > 1:
                            st.subheader("🥧 Cuota de Mercado (% Pasajeros)")
                            fig_pie = px.pie(df_filtro, values="pasajeros", names="aerolinea", hole=0.4)
                            st.plotly_chart(fig_pie, use_container_width=True)

                # -------------------------------------------------------------
                # 2. CUADROS ESTADÍSTICOS (A ancho completo para que no se corten)
                # -------------------------------------------------------------
                with tab_cuadros:
                    st.subheader("📋 Cuadro 1: Matriz Mensual de Pasajeros por Aerolínea")
                    # Matriz pivot con orden cronológico
                    pivot_mes = df_filtro.pivot_table(
                        index=['periodo_orden', 'periodo_mes_es'],
                        columns='aerolinea',
                        values='pasajeros',
                        aggfunc='sum',
                        fill_value=0
                    ).reset_index()
                    pivot_mes = pivot_mes.sort_values(by='periodo_orden').drop(columns=['periodo_orden']).set_index('periodo_mes_es')
                    pivot_mes['TOTAL MES'] = pivot_mes.sum(axis=1)
                    st.dataframe(pivot_mes.style.format("{:,.0f}"), use_container_width=True)

                    st.divider()

                    st.subheader("🏢 Cuadro 2: Resumen por Aerolínea")
                    res_aero = df_filtro.groupby('aerolinea', as_index=False).agg(
                        pasajeros=('pasajeros', 'sum'),
                        vuelos=('vuelos', 'sum'),
                        asientos=('asientos', 'sum')
                    )
                    res_aero['market_share_%'] = ((res_aero['pasajeros'] / tot_pax) * 100).round(1)
                    res_aero['load_factor_%'] = np.where(res_aero['asientos'] > 0, 
                                                        (res_aero['pasajeros'] / res_aero['asientos']) * 100, 
                                                        0).round(1)
                    st.dataframe(res_aero.style.format({"pasajeros": "{:,.0f}", "vuelos": "{:,.0f}", "asientos": "{:,.0f}"}), use_container_width=True)

                    st.divider()

                    st.subheader("🔄 Cuadro 3: Resumen por Tramo (Sentido del Vuelo)")
                    res_tramo = df_filtro.groupby('tramo_label', as_index=False).agg(
                        pasajeros=('pasajeros', 'sum'),
                        vuelos=('vuelos', 'sum'),
                        asientos=('asientos', 'sum')
                    )
                    res_tramo['load_factor_%'] = np.where(res_tramo['asientos'] > 0, 
                                                          (res_tramo['pasajeros'] / res_tramo['asientos']) * 100, 
                                                          0).round(1)
                    st.dataframe(res_tramo.style.format({"pasajeros": "{:,.0f}", "vuelos": "{:,.0f}", "asientos": "{:,.0f}"}), use_container_width=True)

                    st.divider()

                    st.subheader("📄 Registros Detallados")
                    columnas_ver = [c for c in ['fecha', 'tramo_label', 'aerolinea', 'pasajeros', 'asientos', 'vuelos', 'load_factor'] if c in df_filtro.columns]
                    st.dataframe(df_filtro[columnas_ver].sort_values(by='fecha', ascending=False), use_container_width=True, height=300)
                    
                    csv_descarga = df_filtro.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Descargar datos filtrados (CSV)",
                        data=csv_descarga,
                        file_name="rutas_filtradas.csv",
                        mime="text/csv"
                    )

        except Exception as e:
            st.error(f"Error al procesar: {e}")
