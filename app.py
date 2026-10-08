# -*- coding: utf-8 -*-
import io
import re
import os
from datetime import datetime, date
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Monitor de Rutas Aéreas de Cabotaje",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------------------
# DICCIONARIOS Y CONFIGURACIONES
# -------------------------------------------------------------
meses_es = {
    1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
    7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'
}

meses_map = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
    'julio': 7, 'agosto': 8, 'septiembre': 9, 'setiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12,
    'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'ago': 8, 'sep': 9, 'set': 9, 'oct': 10, 'nov': 11, 'dic': 12
}

AEROPUERTOS_EXHAUSTIVO = {
    'AEP': {'codigo': 'AEP', 'ciudad': 'Aeroparque', 'keywords': ['AEROPARQUE', 'JORGE NEWBERY', 'BUENOS AIRES', 'CABA', 'AEP', 'AER']},
    'EZE': {'codigo': 'EZE', 'ciudad': 'Ezeiza', 'keywords': ['EZEIZA', 'PISTARINI', 'MINISTRO PISTARINI', 'EZE']},
    'EPA': {'codigo': 'EPA', 'ciudad': 'El Palomar', 'keywords': ['PALOMAR', 'EPA']},
    'FDO': {'codigo': 'FDO', 'ciudad': 'San Fernando', 'keywords': ['SAN FERNANDO', 'FDO']},
    'BRC': {'codigo': 'BRC', 'ciudad': 'Bariloche', 'keywords': ['BARILOCHE', 'SAN CARLOS DE BARILOCHE', 'CANDELARIA', 'LUIS CANDELARIA', 'BRC']},
    'COR': {'codigo': 'COR', 'ciudad': 'Córdoba', 'keywords': ['CORDOBA', 'CÓRDOBA', 'TARAVELLA', 'PAJAS BLANCAS', 'AMBROSIO', 'COR', 'CBA']},
    'MDZ': {'codigo': 'MDZ', 'ciudad': 'Mendoza', 'keywords': ['MENDOZA', 'PLUMERILLO', 'EL PLUMERILLO', 'GABRIELLI', 'MDZ']},
    'SLA': {'codigo': 'SLA', 'ciudad': 'Salta', 'keywords': ['SALTA', 'GUEMES', 'GÜEMES', 'MARTIN MIGUEL', 'MARTÍN MIGUEL', 'SLA']},
    'JUJ': {'codigo': 'JUJ', 'ciudad': 'Jujuy', 'keywords': ['JUJUY', 'SAN SALVADOR', 'GUZMAN', 'GUZMÁN', 'HORACIO GUZMAN', 'HORACIO GUZMÁN', 'GDOR. HORACIO', 'JUJ']},
    'IGR': {'codigo': 'IGR', 'ciudad': 'Iguazú', 'keywords': ['IGUAZU', 'IGUAZÚ', 'CATARATAS', 'PUERTO IGUAZU', 'PUERTO IGUAZÚ', 'IGR']},
    'USH': {'codigo': 'USH', 'ciudad': 'Ushuaia', 'keywords': ['USHUAIA', 'MALVINAS ARGENTINAS', 'USH']},
    'FTE': {'codigo': 'FTE', 'ciudad': 'El Calafate', 'keywords': ['CALAFATE', 'EL CALAFATE', 'ARMANDO TOLA', 'TOLA', 'FTE']},
    'NQN': {'codigo': 'NQN', 'ciudad': 'Neuquén', 'keywords': ['NEUQUEN', 'NEUQUÉN', 'PERON', 'PERÓN', 'PRESIDENTE PERON', 'NQN']},
    'TUC': {'codigo': 'TUC', 'ciudad': 'Tucumán', 'keywords': ['TUCUMAN', 'TUCUMÁN', 'MATIENZO', 'BENJAMIN', 'BENJAMÍN', 'BENJAMI', 'BENJAMÍ', 'TUC']},
    'MDQ': {'codigo': 'MDQ', 'ciudad': 'Mar del Plata', 'keywords': ['MAR DEL PLATA', 'PIAZZOLLA', 'PIAZZOLA', 'PIAZOLA', 'ASTOR', 'MDQ', 'MDP']},
    'BHI': {'codigo': 'BHI', 'ciudad': 'Bahía Blanca', 'keywords': ['BAHIA BLANCA', 'BAHÍA BLANCA', 'ESPORA', 'COMANDANTE ESPORA', 'BHI']},
    'CRD': {'codigo': 'CRD', 'ciudad': 'Comodoro Rivadavia', 'keywords': ['COMODORO', 'COMODORO RIVADAVIA', 'MOSCONI', 'GENERAL MOSCONI', 'CRD']},
    'REL': {'codigo': 'REL', 'ciudad': 'Trelew', 'keywords': ['TRELEW', 'ALMIRANTE ZAR', 'ZAR', 'REL']},
    'ROS': {'codigo': 'ROS', 'ciudad': 'Rosario', 'keywords': ['ROSARIO', 'ISLAS MALVINAS', 'ROS']},
    'SFN': {'codigo': 'SFN', 'ciudad': 'Santa Fe', 'keywords': ['SANTA FE', 'SAUCE VIEJO', 'SFN']},
    'CNQ': {'codigo': 'CNQ', 'ciudad': 'Corrientes', 'keywords': ['CORRIENTES', 'PIRAGINE', 'PIRAGINE NIVEYRO', 'PIRAG', 'FERNANDO PIRAG', 'CNQ']},
    'PSS': {'codigo': 'PSS', 'ciudad': 'Posadas', 'keywords': ['POSADAS', 'LIBERTADOR GENERAL SAN MARTIN', 'JOSE DE SAN MARTIN', 'SAN MARTIN', 'PSS']},
    'RES': {'codigo': 'RES', 'ciudad': 'Resistencia', 'keywords': ['RESISTENCIA', 'JOSE DE SAN MARTIN', 'RES']},
    'RGL': {'codigo': 'RGL', 'ciudad': 'Río Gallegos', 'keywords': ['RIO GALLEGOS', 'RÍO GALLEGOS', 'NORBERTO FERNANDEZ', 'NORBERTO FERNÁNDEZ', 'PILOTO CIVIL NORBE', 'NORBE', 'RGL']},
    'RGA': {'codigo': 'RGA', 'ciudad': 'Río Grande', 'keywords': ['RIO GRANDE', 'RÍO GRANDE', 'HERMES QUIJADA', 'RAMON TREJO', 'TREJO NOEL', 'RGA']},
    'EQS': {'codigo': 'EQS', 'ciudad': 'Esquel', 'keywords': ['ESQUEL', 'BRIGADIER GENERAL ANTONIO PARODI', 'PARODI', 'EQS']},
    'PMY': {'codigo': 'PMY', 'ciudad': 'Puerto Madryn', 'keywords': ['PUERTO MADRYN', 'MADRYN', 'EL TEHUELCHE', 'TEHUELCHE', 'PMY']},
    'VDM': {'codigo': 'VDM', 'ciudad': 'Viedma', 'keywords': ['VIEDMA', 'GOBERNADOR CASTELLO', 'CASTELLO', 'VDM']},
    'CPC': {'codigo': 'CPC', 'ciudad': 'San Martín de los Andes', 'keywords': ['SAN MARTIN DE LOS ANDES', 'CHAPELCO', 'CARLOS CAMPOS', 'CPC']},
    'IRJ': {'codigo': 'IRJ', 'ciudad': 'La Rioja', 'keywords': ['LA RIOJA', 'CAPITAN VICENTE ALMANDOS', 'ALMANDOS', 'VICENTE ALMANDOS', 'IRJ']},
    'CTC': {'codigo': 'CTC', 'ciudad': 'Catamarca', 'keywords': ['CATAMARCA', 'SAN FERNANDO DEL VALLE', 'FELIPE VARELA', 'VARELA', 'CTC']},
    'SDE': {'codigo': 'SDE', 'ciudad': 'Santiago del Estero', 'keywords': ['SANTIAGO DEL ESTERO', 'VICECOMODORO ARAGONES', 'ARAGONES', 'ARAGONÉS', 'SDE']},
    'RHD': {'codigo': 'RHD', 'ciudad': 'Termas de Río Hondo', 'keywords': ['TERMAS', 'RIO HONDO', 'RÍO HONDO', 'LAS TERMAS', 'RHD']},
    'UAQ': {'codigo': 'UAQ', 'ciudad': 'San Juan', 'keywords': ['SAN JUAN', 'DOMINGO FAUSTINO SARMIENTO', 'SARMIENTO', 'UAQ']},
    'LUQ': {'codigo': 'LUQ', 'ciudad': 'San Luis', 'keywords': ['SAN LUIS', 'BRIGADIER MAYOR CESAR RAUL OJEDA', 'CESAR RAUL OJEDA', 'OJEDA', 'LUQ']},
    'VME': {'codigo': 'VME', 'ciudad': 'Villa Reynolds', 'keywords': ['VILLA REYNOLDS', 'REYNOLDS', 'VME']},
    'VLG': {'codigo': 'VLG', 'ciudad': 'Villa Gesell', 'keywords': ['VILLA GESELL', 'GESELL', 'VLG']},
    'PRA': {'codigo': 'PRA', 'ciudad': 'Paraná', 'keywords': ['PARANA', 'PARANÁ', 'GENERAL JUSTO JOSE DE URQUIZA', 'URQUIZA', 'PRA']},
    'FMA': {'codigo': 'FMA', 'ciudad': 'Formosa', 'keywords': ['FORMOSA', 'EL PUCU', 'EL PUCÚ', 'FMA']},
    'GPO': {'codigo': 'GPO', 'ciudad': 'General Pico', 'keywords': ['GENERAL PICO', 'PICO', 'GPO']},
    'RSA': {'codigo': 'RSA', 'ciudad': 'Santa Rosa', 'keywords': ['SANTA ROSA', 'RSA']},
    'AFA': {'codigo': 'AFA', 'ciudad': 'San Rafael', 'keywords': ['SAN RAFAEL', 'SANTIAGO GERMANO', 'GERMANO', 'AFA']},
    'MLG': {'codigo': 'MLG', 'ciudad': 'Malargüe', 'keywords': ['MALARGUE', 'MALARGÜE', 'COMODORO RICARDO SALOMON', 'SALOMON', 'SALOMÓN', 'MLG']},
    'RCU': {'codigo': 'RCU', 'ciudad': 'Río Cuarto', 'keywords': ['RIO CUARTO', 'RÍO CUARTO', 'AREA DE MATERIAL', 'RCU']},
    'OYO': {'codigo': 'OYO', 'ciudad': 'Tres Arroyos', 'keywords': ['TRES ARROYOS', 'OYO']},
    'OVR': {'codigo': 'OVR', 'ciudad': 'Olavarría', 'keywords': ['OLAVARRIA', 'OLAVARRÍA', 'OVR']},
    'TDL': {'codigo': 'TDL', 'ciudad': 'Tandil', 'keywords': ['TANDIL', 'TDL']},
    'NEC': {'codigo': 'NEC', 'ciudad': 'Necochea', 'keywords': ['NECOCHEA', 'NEC']},
    'PEH': {'codigo': 'PEH', 'ciudad': 'Pehuajó', 'keywords': ['PEHUAJO', 'PEHUAJÓ', 'PEH']},
    'CSZ': {'codigo': 'CSZ', 'ciudad': 'Brigadier Lopez', 'keywords': ['COCHICO', 'CSZ']},
    'RYO': {'codigo': 'RYO', 'ciudad': 'Río Turbio', 'keywords': ['RIO TURBIO', 'RÍO TURBIO', 'RYO']},
    'PMQ': {'codigo': 'PMQ', 'ciudad': 'Perito Moreno', 'keywords': ['PERITO MORENO', 'PMQ']},
    'GGS': {'codigo': 'GGS', 'ciudad': 'Gobernador Gregores', 'keywords': ['GOBERNADOR GREGORES', 'GREGORES', 'GGS']},
    'ULA': {'codigo': 'ULA', 'ciudad': 'San Julián', 'keywords': ['SAN JULIAN', 'SAN JULIÁN', 'ULA']},
    'SZT': {'codigo': 'SZT', 'ciudad': 'San Cristóbal', 'keywords': ['SAN CRISTOBAL', 'SZT']},
    'RDS': {'codigo': 'RDS', 'ciudad': 'Rincón de los Sauces', 'keywords': ['RINCON DE LOS SAUCES', 'RDS']},
    'APZ': {'codigo': 'APZ', 'ciudad': 'Zapala', 'keywords': ['ZAPALA', 'APZ']},
    'CUT': {'codigo': 'CUT', 'ciudad': 'Cutral Có', 'keywords': ['CUTRAL CO', 'CUTRAL CÓ', 'CUT']}
}

def normalizar_texto_aeropuerto(texto):
    if not isinstance(texto, str):
        return ""
    txt = texto.upper().strip()
    txt = re.sub(r'[ÁÀÄÂ]', 'A', txt)
    txt = re.sub(r'[ÉÈËÊ]', 'E', txt)
    txt = re.sub(r'[ÍÌÏÎ]', 'I', txt)
    txt = re.sub(r'[ÓÒÖÔ]', 'O', txt)
    txt = re.sub(r'[ÚÙÜÛ]', 'U', txt)
    txt = re.sub(r'[^A-Z0-9\s]', ' ', txt)
    return ' '.join(txt.split())

def obtener_sigla_y_ciudad(nombre_aeropuerto):
    if not isinstance(nombre_aeropuerto, str) or not nombre_aeropuerto.strip():
        return "DES", "Desconocido"

    norm = normalizar_texto_aeropuerto(nombre_aeropuerto)

    for iata, datos in AEROPUERTOS_EXHAUSTIVO.items():
        if re.search(r'\b' + re.escape(iata) + r'\b', norm):
            return datos['codigo'], datos['ciudad']

    for iata, datos in AEROPUERTOS_EXHAUSTIVO.items():
        for kw in datos['keywords']:
            kw_norm = normalizar_texto_aeropuerto(kw)
            if kw_norm and re.search(r'\b' + re.escape(kw_norm) + r'\b', norm):
                return datos['codigo'], datos['ciudad']

    primer_token = norm.split()[0] if norm.split() else "DES"
    sigla_fallback = primer_token[:3] if len(primer_token) >= 3 else primer_token
    nombre_limpio = nombre_aeropuerto.strip()
    return sigla_fallback, nombre_limpio

def construir_etiqueta_aeropuerto(nombre_aeropuerto):
    sigla, ciudad = obtener_sigla_y_ciudad(nombre_aeropuerto)
    return f"{sigla} ({ciudad})"

# Formateadores estándar
fmt_entero = lambda x: f"{int(round(x)):,}".replace(",", ".")
fmt_decimal = lambda x: f"{x:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
fmt_porcentaje = lambda x: f"{x:.1f}%".replace(".", ",")

# -------------------------------------------------------------
# DETECCIÓN Y CARGA ESTRICTA DE DATOS REALES
# -------------------------------------------------------------
@st.cache_data(show_spinner=False)
def procesar_dataframe_oficial(df_in):
    df = df_in.copy()
    
    col_map = {}
    for c in df.columns:
        c_norm = normalizar_texto_aeropuerto(str(c))
        if 'ANO' in c_norm or 'YEAR' in c_norm or c_norm == 'A':
            col_map[c] = 'ano_raw'
        elif 'MES' in c_norm or 'MONTH' in c_norm:
            col_map[c] = 'mes_raw'
        elif 'DIA' in c_norm or 'DAY' in c_norm:
            col_map[c] = 'dia_raw'
        elif 'FECHA' in c_norm or 'DATE' in c_norm:
            col_map[c] = 'fecha_raw'
        elif 'ORIGEN' in c_norm or 'ORIG' in c_norm:
            col_map[c] = 'origen_raw'
        elif 'DESTINO' in c_norm or 'DEST' in c_norm:
            col_map[c] = 'destino_raw'
        elif 'EMPRESA' in c_norm or 'AEROLINEA' in c_norm or 'OPERADOR' in c_norm:
            col_map[c] = 'aerolinea_raw'
        elif 'PASAJERO' in c_norm or 'PAX' in c_norm:
            col_map[c] = 'pasajeros_raw'
        elif 'VUELO' in c_norm or 'FLIGHT' in c_norm or 'ETAPAS' in c_norm:
            col_map[c] = 'vuelos_raw'
        elif 'ASIENTO' in c_norm or 'SEAT' in c_norm or 'CAPACIDAD' in c_norm:
            col_map[c] = 'asientos_raw'

    df.rename(columns=col_map, inplace=True)

    cols_esenciales = ['origen_raw', 'destino_raw']
    for req in cols_esenciales:
        if req not in df.columns:
            return None, f"El archivo no contiene la columna esencial de '{req}'."

    # Aerolínea
    if 'aerolinea_raw' in df.columns:
        df['aerolinea'] = df['aerolinea_raw'].astype(str).str.strip().replace({'nan': 'Otras Aerolíneas', '': 'Otras Aerolíneas'})
    else:
        df['aerolinea'] = 'Línea Regular'

    # Métricas numéricas
    for col_met, col_dest in [('pasajeros_raw', 'pasajeros'), ('vuelos_raw', 'vuelos'), ('asientos_raw', 'asientos')]:
        if col_met in df.columns:
            df[col_dest] = pd.to_numeric(df[col_met].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).str.strip(), errors='coerce').fillna(0)
        else:
            df[col_dest] = 0

    # Fechas
    if 'fecha_raw' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha_raw'], errors='coerce')
    else:
        df['fecha'] = pd.NaT

    filas_nat = df['fecha'].isna()
    if filas_nat.any() and 'ano_raw' in df.columns and 'mes_raw' in df.columns:
        def armar_fecha(row):
            try:
                y = int(float(str(row['ano_raw']).strip()))
                m_val = str(row['mes_raw']).strip().lower()
                if m_val.isdigit():
                    m = int(m_val)
                else:
                    m = meses_map.get(m_val, 1)
                
                d = 1
                if 'dia_raw' in row and pd.notna(row['dia_raw']):
                    d_str = str(row['dia_raw']).strip()
                    if d_str.isdigit():
                        d = max(1, min(int(d_str), 28))
                return datetime(y, m, d)
            except Exception:
                return pd.NaT

        df.loc[filas_nat, 'fecha'] = df[filas_nat].apply(armar_fecha, axis=1)

    df = df[df['fecha'].notna()].copy()
    if df.empty:
        return None, "No se pudieron construir fechas válidas a partir de los datos."

    df['ano_num'] = df['fecha'].dt.year
    df['mes_num'] = df['fecha'].dt.month
    df['periodo_orden'] = df['fecha'].dt.strftime('%Y-%m')
    df['periodo_mes_es'] = df['fecha'].apply(lambda d: f"{meses_es.get(d.month, '')}-{str(d.year)[2:]}")

    # Etiquetas de aeropuertos con sigla oficial estricta
    cache_etiquetas = {}
    def cached_etiqueta(nombre):
        if nombre not in cache_etiquetas:
            cache_etiquetas[nombre] = construir_etiqueta_aeropuerto(nombre)
        return cache_etiquetas[nombre]

    df['origen_label'] = df['origen_raw'].apply(cached_etiqueta)
    df['destino_label'] = df['destino_raw'].apply(cached_etiqueta)

    # Identificación estricta de sentido y corredor bidireccional
    def crear_par_ordenado(row):
        pts = sorted([row['origen_label'], row['destino_label']])
        return f"{pts[0]} ⇄ {pts[1]}"

    df['ruta_label'] = df.apply(crear_par_ordenado, axis=1)
    df['tramo_label'] = df['origen_label'] + " ➔ " + df['destino_label']

    return df, None

def cargar_archivo_en_memoria(archivo_bytes_o_path):
    encodings = ['utf-8', 'utf-8-sig', 'latin1', 'iso-8859-1', 'cp1252']
    separadores = [',', ';', '\t']

    for enc in encodings:
        for sep in separadores:
            try:
                if isinstance(archivo_bytes_o_path, str):
                    df = pd.read_csv(archivo_bytes_o_path, sep=sep, encoding=enc, nrows=100)
                else:
                    archivo_bytes_o_path.seek(0)
                    df = pd.read_csv(archivo_bytes_o_path, sep=sep, encoding=enc, nrows=100)

                if len(df.columns) >= 4:
                    if isinstance(archivo_bytes_o_path, str):
                        df_completo = pd.read_csv(archivo_bytes_o_path, sep=sep, encoding=enc, low_memory=False)
                    else:
                        archivo_bytes_o_path.seek(0)
                        df_completo = pd.read_csv(archivo_bytes_o_path, sep=sep, encoding=enc, low_memory=False)
                    return df_completo, None
            except Exception:
                continue

    return None, "No se pudo interpretar el archivo CSV con los codificadores habituales."

# -------------------------------------------------------------
# BARRA LATERAL: FUENTES DE DATOS
# -------------------------------------------------------------
st.sidebar.title("✈️ Conectividad Aérea")
st.sidebar.markdown("**Monitor Oficial de Vuelos de Cabotaje**")
st.sidebar.markdown("---")

df_raw = None
fuente_activa = None

subido = st.sidebar.file_uploader(
    "📂 Cargar microdatos (CSV oficial)",
    type=['csv', 'txt'],
    help="Suba la base oficial descargada de ANAC o del repositorio."
)

if subido is not None:
    df_leido, err = cargar_archivo_en_memoria(subido)
    if err:
        st.sidebar.error(err)
    else:
        df_procesado, err_proc = procesar_dataframe_oficial(df_leido)
        if err_proc:
            st.sidebar.error(err_proc)
        else:
            df_raw = df_procesado
            fuente_activa = f"Archivo subido manualmente ({subido.name})"
else:
    posibles_rutas = [
        "conectividad_aerea.csv",
        "data/conectividad_aerea.csv",
        "datos/conectividad_aerea.csv",
        "base_anac.csv",
        "cabotaje.csv"
    ]
    for ruta in posibles_rutas:
        if os.path.exists(ruta):
            df_leido, err = cargar_archivo_en_memoria(ruta)
            if not err:
                df_procesado, err_proc = procesar_dataframe_oficial(df_leido)
                if not err_proc:
                    df_raw = df_procesado
                    fuente_activa = f"Repositorio GitHub ({ruta})"
                    break

# -------------------------------------------------------------
# CABECERA Y REGLA ESTRICTA CONTRA DATOS INVENTADOS
# -------------------------------------------------------------
st.title("🛫 Monitor de Rutas Aéreas y Tráfico de Cabotaje")
st.markdown("Herramienta de análisis analítico basada **únicamente en estadísticas oficiales reales**.")

if df_raw is None or df_raw.empty:
    st.error(
        "⛔ **NO HAY DATOS REALES CARGADOS O VÁLIDOS**  \n\n"
        "Esta aplicación tiene **estrictamente prohibido generar, simular o inventar datos**.  \n"
        "Para visualizar información, realice una de las siguientes acciones:  \n"
        "1. Asegúrese de que el archivo oficial `conectividad_aerea.csv` esté en la raíz del repositorio de GitHub.  \n"
        "2. O bien, suba el archivo CSV oficial en el menú lateral izquierdo."
    )
    st.info("ℹ️ Una vez cargado el archivo oficial con columnas de fecha, aerolínea, origen, destino, pasajeros y vuelos, se habilitará el monitor.")
    st.stop()

# Si hay datos reales cargados:
f_min_total = df_raw['fecha'].min().date()
f_max_total = df_raw['fecha'].max().date()
total_registros = len(df_raw)

st.success(
    f"🟢 **Fuente de Datos Activa:** {fuente_activa}  \n"
    f"📊 **Registros oficiales procesados:** {fmt_entero(total_registros)} filas.  \n"
    f"📅 **Período con estadísticas disponibles:** desde el **{f_min_total.strftime('%d/%m/%Y')}** hasta el **{f_max_total.strftime('%d/%m/%Y')}**."
)

# -------------------------------------------------------------
# FILTROS DE BÚSQUEDA Y BOTÓN BUSCAR VUELOS ACTIVO
# -------------------------------------------------------------
st.subheader("🔍 Filtros de Búsqueda de Vuelos")

rutas_disponibles = sorted(df_raw['ruta_label'].dropna().unique().tolist())
origenes_disponibles = sorted(df_raw['origen_label'].dropna().unique().tolist())
destinos_disponibles = sorted(df_raw['destino_label'].dropna().unique().tolist())

# Callback seguro para invertir Origen y Destino sin error de widget
def intercambiar_origen_destino():
    st.session_state['sel_origenes_key'], st.session_state['sel_destinos_key'] = (
        st.session_state.get('sel_destinos_key', []),
        st.session_state.get('sel_origenes_key', [])
    )
    if 'criterios_activos' in st.session_state:
        st.session_state['criterios_activos']['origenes'] = st.session_state['sel_origenes_key']
        st.session_state['criterios_activos']['destinos'] = st.session_state['sel_destinos_key']

if 'sel_origenes_key' not in st.session_state:
    st.session_state['sel_origenes_key'] = []
if 'sel_destinos_key' not in st.session_state:
    st.session_state['sel_destinos_key'] = []

def_desde = max(f_min_total, date(f_max_total.year, 1, 1)) if (f_max_total - f_min_total).days > 365 else f_min_total
def_hasta = f_max_total

if 'criterios_activos' not in st.session_state:
    st.session_state['criterios_activos'] = {
        'rutas': [],
        'origenes': [],
        'destinos': [],
        'desde': def_desde,
        'hasta': def_hasta
    }

# 1. Selector de Ruta
sel_rutas = st.multiselect(
    "🗺️ Ruta (Ida y Vuelta):",
    options=rutas_disponibles,
    default=st.session_state['criterios_activos']['rutas'],
    help="Agrupa ambos sentidos de vuelo del corredor (ej. Aeroparque ⇄ Jujuy incluye tanto idas como vueltas)."
)

# 2. Selectores de Origen, Invertir y Destino
col_orig, col_inv, col_dest = st.columns([5, 2, 5])

with col_orig:
    sel_origenes = st.multiselect(
        "🛫 Aeropuerto de Salida (Origen):",
        options=origenes_disponibles,
        key='sel_origenes_key',
        help="Filtra estrictamente los despegues desde este aeropuerto."
    )

with col_inv:
    st.write("")
    st.write("")
    st.button("⇄ Invertir", on_click=intercambiar_origen_destino, use_container_width=True, help="Intercambia Origen y Destino")

with col_dest:
    sel_destinos = st.multiselect(
        "🛬 Aeropuerto de Llegada (Destino):",
        options=destinos_disponibles,
        key='sel_destinos_key',
        help="Filtra estrictamente los aterrizajes en este aeropuerto."
    )

# 3. Rango de Fechas
col_d1, col_d2 = st.columns(2)
with col_d1:
    f_desde = st.date_input(
        "📅 Desde:",
        value=st.session_state['criterios_activos']['desde'],
        min_value=f_min_total,
        max_value=f_max_total,
        help=f"Fecha inicial dentro de la base oficial ({f_min_total.strftime('%d/%m/%Y')} a {f_max_total.strftime('%d/%m/%Y')})."
    )
with col_d2:
    f_hasta = st.date_input(
        "📅 Hasta:",
        value=st.session_state['criterios_activos']['hasta'],
        min_value=f_min_total,
        max_value=f_max_total,
        help=f"Fecha final dentro de la base oficial ({f_min_total.strftime('%d/%m/%Y')} a {f_max_total.strftime('%d/%m/%Y')})."
    )

# 4. Botones de acción
col_b1, col_b2, col_b3 = st.columns([2, 2, 6])
with col_b1:
    btn_buscar = st.button("🔍 Buscar Vuelos", type="primary", use_container_width=True)
with col_b2:
    btn_reset = st.button("🔄 Restablecer Filtros", use_container_width=True)

if btn_reset:
    st.session_state['sel_origenes_key'] = []
    st.session_state['sel_destinos_key'] = []
    st.session_state['criterios_activos'] = {
        'rutas': [],
        'origenes': [],
        'destinos': [],
        'desde': f_min_total,
        'hasta': f_max_total
    }
    st.rerun()

# Actualizar criterios al pulsar Buscar Vuelos
if btn_buscar:
    st.session_state['criterios_activos'] = {
        'rutas': sel_rutas,
        'origenes': st.session_state['sel_origenes_key'],
        'destinos': st.session_state['sel_destinos_key'],
        'desde': f_desde,
        'hasta': f_hasta
    }

filtros = st.session_state['criterios_activos']

# Aplicar el filtrado con las reglas estrictas de diferenciación
mascara = (df_raw['fecha'].dt.date >= filtros['desde']) & (df_raw['fecha'].dt.date <= filtros['hasta'])

if filtros['rutas']:
    mascara &= df_raw['ruta_label'].isin(filtros['rutas'])
if filtros['origenes']:
    mascara &= df_raw['origen_label'].isin(filtros['origenes'])
if filtros['destinos']:
    mascara &= df_raw['destino_label'].isin(filtros['destinos'])

df_filtrado = df_raw[mascara].copy()

# -------------------------------------------------------------
# VALIDACIÓN DE RESULTADOS ENCONTRADOS
# -------------------------------------------------------------
if df_filtrado.empty:
    st.warning("⚠️ No se encontraron vuelos para los criterios seleccionados. Ajuste los filtros y pulse **Buscar Vuelos**.")
    st.stop()

# -------------------------------------------------------------
# KPIs GLOBALES Y RETORNO DEL ÍNDICE HHI
# -------------------------------------------------------------
st.markdown("---")
st.subheader("📌 Resumen Ejecutivo del Segmento Seleccionado")

pax_total = df_filtrado['pasajeros'].sum()
vuelos_total = df_filtrado['vuelos'].sum()
asientos_total = df_filtrado['asientos'].sum()
factor_ocupacion = (pax_total / asientos_total * 100) if asientos_total > 0 else 0
pax_por_vuelo = (pax_total / vuelos_total) if vuelos_total > 0 else 0

# Cálculo del Índice HHI (Herfindahl-Hirschman Index)
cuotas_pax = df_filtrado.groupby('aerolinea')['pasajeros'].sum()
if pax_total > 0:
    shares_pct = (cuotas_pax / pax_total) * 100
    hhi_val = int(round((shares_pct ** 2).sum()))
else:
    hhi_val = 0

if hhi_val < 1500:
    hhi_desc = "Baja (Competitivo)"
elif hhi_val <= 2500:
    hhi_desc = "Moderada"
else:
    hhi_desc = "Alta (Concentrado)"

kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
kpi1.metric("Pasajeros", fmt_entero(pax_total))
kpi2.metric("Vuelos", fmt_entero(vuelos_total))
kpi3.metric("Asientos", fmt_entero(asientos_total))
kpi4.metric("Ocupación", fmt_porcentaje(factor_ocupacion))
kpi5.metric("Pax / Vuelo", fmt_decimal(pax_por_vuelo))
kpi6.metric("Concentración (HHI)", f"{hhi_val:,}".replace(",", "."), help=f"Índice de Concentración de Mercado: {hhi_desc}")

# -------------------------------------------------------------
# ESTRUCTURA ORGANIZADA POR PESTAÑAS FUNCIONALES
# -------------------------------------------------------------
st.markdown("---")

tab_graficos, tab_cuadros, tab_estacionalidad, tab_comparador, tab_descargas = st.tabs([
    "📊 Gráficos Básicos",
    "📋 Cuadros de Datos",
    "📅 Estacionalidad",
    "⚖️ Comparación Interanual (YoY)",
    "📥 Descarga de Datos"
])

# =============================================================
# SECCIÓN 1: GRÁFICOS CON INFORMACIÓN BÁSICA
# =============================================================
with tab_graficos:
    st.markdown("### Métricas Visuales Básicas")
    
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        # 1. Pasajeros mensuales por aerolínea
        df_mes_aero = df_filtrado.groupby(['periodo_orden', 'periodo_mes_es', 'aerolinea'], observed=True)['pasajeros'].sum().reset_index()
        df_mes_aero = df_mes_aero.sort_values(by=['periodo_orden', 'pasajeros'], ascending=[True, False])
        
        fig_bar = px.bar(
            df_mes_aero,
            x='periodo_mes_es',
            y='pasajeros',
            color='aerolinea',
            title="Evolución Mensual de Pasajeros por Operador",
            labels={'periodo_mes_es': 'Mes', 'pasajeros': 'Pasajeros'},
            barmode='stack'
        )
        fig_bar.update_layout(xaxis_tickangle=-45, legend_title_text='Aerolínea')
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_g2:
        # 2. Ocupación mensual promedio
        df_mes_total = df_filtrado.groupby(['periodo_orden', 'periodo_mes_es'], observed=True).agg(
            pasajeros=('pasajeros', 'sum'),
            asientos=('asientos', 'sum')
        ).reset_index().sort_values(by='periodo_orden')
        df_mes_total['ocupacion_%'] = np.where(df_mes_total['asientos'] > 0,
                                               (df_mes_total['pasajeros'] / df_mes_total['asientos']) * 100, 0)

        fig_line = px.line(
            df_mes_total,
            x='periodo_mes_es',
            y='ocupacion_%',
            title="Factor de Ocupación Promedio (%) Mes a Mes",
            labels={'periodo_mes_es': 'Período', 'ocupacion_%': 'Ocupación (%)'},
            markers=True
        )
        fig_line.update_layout(yaxis_range=[0, 105], xaxis_tickangle=-45)
        st.plotly_chart(fig_line, use_container_width=True)

    col_g3, col_g4 = st.columns(2)
    
    with col_g3:
        # 3. Market Share de Pasajeros
        df_aero_pie = df_filtrado.groupby('aerolinea', observed=True)['pasajeros'].sum().reset_index()
        fig_pie = px.pie(
            df_aero_pie[df_aero_pie['pasajeros'] > 0],
            names='aerolinea',
            values='pasajeros',
            title="Market Share de Pasajeros (Cuota de Mercado)",
            hole=0.4
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_g4:
        # 4. Gráfico por Sentido de Vuelo (Ida vs Vuelta)
        df_tramo_graf = df_filtrado.groupby(['tramo_label', 'aerolinea'], observed=True)['pasajeros'].sum().reset_index()
        df_tramo_graf = df_tramo_graf[df_tramo_graf['pasajeros'] > 0]
        fig_tramo = px.bar(
            df_tramo_graf,
            x='tramo_label',
            y='pasajeros',
            color='aerolinea',
            title="Pasajeros por Sentido de Vuelo (Ida vs. Vuelta)",
            labels={'tramo_label': 'Tramo', 'pasajeros': 'Pasajeros'},
            barmode='group'
        )
        fig_tramo.update_layout(xaxis_tickangle=-25)
        st.plotly_chart(fig_tramo, use_container_width=True)

# =============================================================
# SECCIÓN 2: CUADROS CON INFORMACIÓN BÁSICA
# =============================================================
with tab_cuadros:
    st.markdown("### Cuadros Estadísticos y Tabulaciones Oficiales")

    # Cuadro 1: Desempeño Comercial por Operador
    st.subheader("1. Desempeño Comercial por Operador")
    df_aero = df_filtrado.groupby('aerolinea', observed=True).agg(
        pasajeros=('pasajeros', 'sum'),
        vuelos=('vuelos', 'sum'),
        asientos=('asientos', 'sum')
    ).reset_index()
    df_aero = df_aero[df_aero['vuelos'] > 0].sort_values(by='pasajeros', ascending=False)

    total_p = df_aero['pasajeros'].sum()
    df_aero['cuota_pax_%'] = (df_aero['pasajeros'] / total_p * 100) if total_p > 0 else 0
    df_aero['ocupacion_%'] = np.where(df_aero['asientos'] > 0, (df_aero['pasajeros'] / df_aero['asientos']) * 100, 0)
    df_aero['prom_pax_vuelo'] = np.where(df_aero['vuelos'] > 0, df_aero['pasajeros'] / df_aero['vuelos'], 0)

    df_aero_disp = df_aero.copy()
    df_aero_disp['Pasajeros'] = df_aero_disp['pasajeros'].apply(fmt_entero)
    df_aero_disp['Vuelos'] = df_aero_disp['vuelos'].apply(fmt_entero)
    df_aero_disp['Asientos'] = df_aero_disp['asientos'].apply(fmt_entero)
    df_aero_disp['Share Pax'] = df_aero_disp['cuota_pax_%'].apply(fmt_porcentaje)
    df_aero_disp['Ocupación'] = df_aero_disp['ocupacion_%'].apply(fmt_porcentaje)
    df_aero_disp['Pax/Vuelo'] = df_aero_disp['prom_pax_vuelo'].apply(fmt_decimal)

    st.dataframe(
        df_aero_disp[['aerolinea', 'Pasajeros', 'Share Pax', 'Vuelos', 'Asientos', 'Ocupación', 'Pax/Vuelo']].rename(
            columns={'aerolinea': 'Aerolínea'}
        ),
        use_container_width=True,
        hide_index=True
    )

    # Cuadro 2: Desglose por Sentido (Ida vs. Vuelta)
    st.subheader("2. Desglose por Sentido de Vuelo (Ida vs. Vuelta)")
    df_tramo = df_filtrado.groupby(['tramo_label', 'aerolinea'], observed=True).agg(
        pasajeros=('pasajeros', 'sum'),
        vuelos=('vuelos', 'sum'),
        asientos=('asientos', 'sum')
    ).reset_index()
    df_tramo = df_tramo[df_tramo['vuelos'] > 0]
    df_tramo['ocupacion_%'] = np.where(df_tramo['asientos'] > 0, (df_tramo['pasajeros'] / df_tramo['asientos']) * 100, 0)
    df_tramo['prom_pax_vuelo'] = np.where(df_tramo['vuelos'] > 0, df_tramo['pasajeros'] / df_tramo['vuelos'], 0)

    df_t_disp = df_tramo.copy()
    df_t_disp['Pasajeros'] = df_t_disp['pasajeros'].apply(fmt_entero)
    df_t_disp['Vuelos'] = df_t_disp['vuelos'].apply(fmt_entero)
    df_t_disp['Asientos'] = df_t_disp['asientos'].apply(fmt_entero)
    df_t_disp['Ocupación'] = df_t_disp['ocupacion_%'].apply(fmt_porcentaje)
    df_t_disp['Pax/Vuelo'] = df_t_disp['prom_pax_vuelo'].apply(fmt_decimal)

    st.dataframe(
        df_t_disp[['tramo_label', 'aerolinea', 'Pasajeros', 'Vuelos', 'Asientos', 'Ocupación', 'Pax/Vuelo']].rename(
            columns={'tramo_label': 'Tramo Operado', 'aerolinea': 'Aerolínea'}
        ),
        use_container_width=True,
        hide_index=True
    )

    # Cuadro 3: Matriz Mensual Detallada
    st.subheader("3. Matriz Mensual de Pasajeros por Operador")
    pivot_pax = df_filtrado.pivot_table(
        index='aerolinea',
        columns='periodo_mes_es',
        values='pasajeros',
        aggfunc='sum',
        fill_value=0,
        observed=True
    )

    # Orden cronológico de las columnas
    meses_presentes = df_filtrado[['periodo_orden', 'periodo_mes_es']].drop_duplicates().sort_values('periodo_orden')['periodo_mes_es'].tolist()
    columnas_ordenadas = [m for m in meses_presentes if m in pivot_pax.columns]
    pivot_pax = pivot_pax[columnas_ordenadas]

    # Fila y columna de totales
    pivot_pax_con_total = pivot_pax.copy()
    pivot_pax_con_total['Total General'] = pivot_pax_con_total.sum(axis=1)
    fila_total = pivot_pax_con_total.sum(axis=0)
    fila_total.name = 'Total Mercado'
    pivot_pax_con_total = pd.concat([pivot_pax_con_total, fila_total.to_frame().T])

    pivot_pax_fmt = pivot_pax_con_total.applymap(fmt_entero)
    st.dataframe(pivot_pax_fmt, use_container_width=True)

# =============================================================
# SECCIÓN 3: ESTACIONALIDAD DE LA RUTA
# =============================================================
with tab_estacionalidad:
    st.markdown("### Análisis de Estacionalidad de la Demanda")
    st.markdown("Permite observar el comportamiento intra-anual típico de la ruta agrupando los datos por mes del año (Enero a Diciembre).")

    # Agrupación por mes calendario
    df_est = df_filtrado.groupby('mes_num', observed=True).agg(
        pasajeros=('pasajeros', 'sum'),
        vuelos=('vuelos', 'sum'),
        asientos=('asientos', 'sum')
    ).reset_index()

    if not df_est.empty and df_est['pasajeros'].sum() > 0:
        promedio_mensual_pax = df_est['pasajeros'].mean()
        df_est['mes_nombre'] = df_est['mes_num'].map(meses_es)
        df_est['indice_estacionalidad_%'] = (df_est['pasajeros'] / promedio_mensual_pax) * 100
        df_est['ocupacion_%'] = np.where(df_est['asientos'] > 0, (df_est['pasajeros'] / df_est['asientos']) * 100, 0)
        df_est = df_est.sort_values(by='mes_num')

        col_est1, col_est2 = st.columns([6, 4])

        with col_est1:
            fig_est = px.bar(
                df_est,
                x='mes_nombre',
                y='pasajeros',
                title="Curva de Estacionalidad Mensual Acumulada",
                labels={'mes_nombre': 'Mes', 'pasajeros': 'Pasajeros Acumulados'},
                text=df_est['pasajeros'].apply(fmt_entero)
            )
            fig_est.update_traces(textposition='outside')
            st.plotly_chart(fig_est, use_container_width=True)

        with col_est2:
            st.markdown("#### Índices de Temporada")
            df_est_disp = df_est.copy()
            df_est_disp['Pasajeros Totales'] = df_est_disp['pasajeros'].apply(fmt_entero)
            df_est_disp['Vuelos Totales'] = df_est_disp['vuelos'].apply(fmt_entero)
            df_est_disp['Ocupación Promedio'] = df_est_disp['ocupacion_%'].apply(fmt_porcentaje)
            df_est_disp['Índice Estacional'] = df_est_disp['indice_estacionalidad_%'].apply(lambda x: f"{x:.1f}%")

            st.dataframe(
                df_est_disp[['mes_nombre', 'Pasajeros Totales', 'Vuelos Totales', 'Ocupación Promedio', 'Índice Estacional']].rename(
                    columns={'mes_nombre': 'Mes'}
                ),
                use_container_width=True,
                hide_index=True
            )
            st.caption("💡 *Un índice estacional superior al 100% representa meses de temporada alta (demanda por encima de la media anual).*")
    else:
        st.info("No hay suficientes datos temporales para calcular la estacionalidad en el período seleccionado.")

# =============================================================
# SECCIÓN 4: COMPARACIÓN INTERANUAL (YoY) / ABSORCIÓN DE MERCADO
# =============================================================
with tab_comparador:
    st.markdown("### Comparación Interanual (YoY) y Shift de Participación")
    st.markdown(
        "Permite contrastar un mes idéntico (por ejemplo, **Julio 2025 vs. Julio 2026**) "
        "para evaluar cómo variaron los vuelos y pasajeros, y si **una aerolínea absorbió la cuota de otra**."
    )

    anos_disponibles = sorted(df_raw['ano_num'].unique().tolist())

    if len(anos_disponibles) >= 2:
        col_c1, col_c2, col_c3 = st.columns(3)

        nombres_meses_opciones = ["Todos los Meses (Año Completo)"] + [meses_es[m] for m in range(1, 13)]
        
        with col_c1:
            mes_sel_str = st.selectbox("Mes a Comparar:", options=nombres_meses_opciones, index=7) # Por defecto Julio (índice 7)
        with col_c2:
            ano_base = st.selectbox("Año Base (Anterior):", options=anos_disponibles, index=max(0, len(anos_disponibles) - 2))
        with col_c3:
            ano_comp = st.selectbox("Año Comparado (Reciente):", options=anos_disponibles, index=len(anos_disponibles) - 1)

        # Filtrar datos de la ruta elegida para ambos años
        mask_yoy = df_raw['ano_num'].isin([ano_base, ano_comp])
        if filtros['rutas']:
            mask_yoy &= df_raw['ruta_label'].isin(filtros['rutas'])
        if filtros['origenes']:
            mask_yoy &= df_raw['origen_label'].isin(filtros['origenes'])
        if filtros['destinos']:
            mask_yoy &= df_raw['destino_label'].isin(filtros['destinos'])

        if mes_sel_str != "Todos los Meses (Año Completo)":
            mes_num_target = next(k for k, v in meses_es.items() if v == mes_sel_str)
            mask_yoy &= (df_raw['mes_num'] == mes_num_target)

        df_yoy = df_raw[mask_yoy].copy()

        if not df_yoy.empty:
            piv_pax = df_yoy.pivot_table(index='aerolinea', columns='ano_num', values='pasajeros', aggfunc='sum', fill_value=0, observed=True)
            piv_vue = df_yoy.pivot_table(index='aerolinea', columns='ano_num', values='vuelos', aggfunc='sum', fill_value=0, observed=True)
            piv_asi = df_yoy.pivot_table(index='aerolinea', columns='ano_num', values='asientos', aggfunc='sum', fill_value=0, observed=True)

            # Asegurar columnas de ambos años
            for col_y in [ano_base, ano_comp]:
                if col_y not in piv_pax.columns:
                    piv_pax[col_y] = 0
                if col_y not in piv_vue.columns:
                    piv_vue[col_y] = 0
                if col_y not in piv_asi.columns:
                    piv_asi[col_y] = 0

            # Totales globales de la ruta para calcular métricas
            tot_pax_base = piv_pax[ano_base].sum()
            tot_pax_comp = piv_pax[ano_comp].sum()
            tot_vue_base = piv_vue[ano_base].sum()
            tot_vue_comp = piv_vue[ano_comp].sum()

            dif_pax_global = tot_pax_comp - tot_pax_base
            var_pax_global = (dif_pax_global / tot_pax_base * 100) if tot_pax_base > 0 else 0
            dif_vue_global = tot_vue_comp - tot_vue_base

            # Tarjetas resumen de la comparación
            k_c1, k_c2, k_c3 = st.columns(3)
            k_c1.metric(f"Total Pasajeros ({ano_comp})", fmt_entero(tot_pax_comp), delta=f"{var_pax_global:+.1f}% vs {ano_base}")
            k_c2.metric(f"Total Vuelos ({ano_comp})", fmt_entero(tot_vue_comp), delta=f"{dif_vue_global:+d} vuelos vs {ano_base}")
            k_c3.metric(f"Pasajeros {ano_base}", fmt_entero(tot_pax_base))

            # Tabla comparativa detallada por aerolínea
            comp_df = pd.DataFrame(index=piv_pax.index)
            comp_df[f'Vuelos {ano_base}'] = piv_vue[ano_base]
            comp_df[f'Vuelos {ano_comp}'] = piv_vue[ano_comp]
            comp_df['Δ Vuelos'] = comp_df[f'Vuelos {ano_comp}'] - comp_df[f'Vuelos {ano_base}']

            comp_df[f'Pax {ano_base}'] = piv_pax[ano_base]
            comp_df[f'Pax {ano_comp}'] = piv_pax[ano_comp]
            comp_df['Δ Pax'] = comp_df[f'Pax {ano_comp}'] - comp_df[f'Pax {ano_base}']

            # Market Share en cada período
            comp_df[f'Share {ano_base}'] = np.where(tot_pax_base > 0, (comp_df[f'Pax {ano_base}'] / tot_pax_base) * 100, 0)
            comp_df[f'Share {ano_comp}'] = np.where(tot_pax_comp > 0, (comp_df[f'Pax {ano_comp}'] / tot_pax_comp) * 100, 0)
            comp_df['Shift Share (pts)'] = comp_df[f'Share {ano_comp}'] - comp_df[f'Share {ano_base}']

            # Ocupación en cada período
            comp_df[f'Ocup {ano_base}'] = np.where(piv_asi[ano_base] > 0, (comp_df[f'Pax {ano_base}'] / piv_asi[ano_base]) * 100, 0)
            comp_df[f'Ocup {ano_comp}'] = np.where(piv_asi[ano_comp] > 0, (comp_df[f'Pax {ano_comp}'] / piv_asi[ano_comp]) * 100, 0)

            # Filtrar solo aerolíneas que hayan operado en alguno de los dos años
            comp_df = comp_df[(comp_df[f'Vuelos {ano_base}'] > 0) | (comp_df[f'Vuelos {ano_comp}'] > 0)].sort_values(by=f'Pax {ano_comp}', ascending=False)

            st.markdown(f"#### Comparativa por Operador: {mes_sel_str} {ano_base} vs. {ano_comp}")

            # Mostrar tabla formateada
            comp_disp = pd.DataFrame(index=comp_df.index)
            comp_disp[f'Vuelos {ano_base}'] = comp_df[f'Vuelos {ano_base}'].apply(fmt_entero)
            comp_disp[f'Vuelos {ano_comp}'] = comp_df[f'Vuelos {ano_comp}'].apply(fmt_entero)
            comp_disp['Δ Vuelos'] = comp_df['Δ Vuelos'].apply(lambda x: f"{x:+d}")

            comp_disp[f'Pax {ano_base}'] = comp_df[f'Pax {ano_base}'].apply(fmt_entero)
            comp_disp[f'Pax {ano_comp}'] = comp_df[f'Pax {ano_comp}'].apply(fmt_entero)
            comp_disp['Δ Pax'] = comp_df['Δ Pax'].apply(lambda x: f"{x:+,}".replace(",", "."))

            comp_disp[f'Share {ano_base}'] = comp_df[f'Share {ano_base}'].apply(fmt_porcentaje)
            comp_disp[f'Share {ano_comp}'] = comp_df[f'Share {ano_comp}'].apply(fmt_porcentaje)
            comp_disp['Shift Share'] = comp_df['Shift Share (pts)'].apply(lambda x: f"{x:+.1f} pts".replace(".", ","))

            comp_disp[f'Ocup {ano_base}'] = comp_df[f'Ocup {ano_base}'].apply(fmt_porcentaje)
            comp_disp[f'Ocup {ano_comp}'] = comp_df[f'Ocup {ano_comp}'].apply(fmt_porcentaje)

            st.dataframe(comp_disp.reset_index().rename(columns={'aerolinea': 'Aerolínea'}), use_container_width=True, hide_index=True)

            # Gráfico de barras comparativo lado a lado
            df_plot_yoy = df_yoy.groupby(['aerolinea', 'ano_num'], observed=True)['pasajeros'].sum().reset_index()
            df_plot_yoy['ano_num'] = df_plot_yoy['ano_num'].astype(str)
            fig_yoy = px.bar(
                df_plot_yoy,
                x='aerolinea',
                y='pasajeros',
                color='ano_num',
                barmode='group',
                title=f"Comparativa de Pasajeros por Aerolínea ({ano_base} vs. {ano_comp})",
                labels={'aerolinea': 'Aerolínea', 'pasajeros': 'Pasajeros', 'ano_num': 'Año'}
            )
            st.plotly_chart(fig_yoy, use_container_width=True)

        else:
            st.warning("No se encontraron registros para la combinación de años y meses seleccionada.")
    else:
        st.info("💡 Para utilizar el comparador interanual (YoY), asegúrese de que la base oficial contenga datos de al menos dos años diferentes.")

# =============================================================
# SECCIÓN 5: DESCARGAS OFICIALES
# =============================================================
with tab_descargas:
    st.markdown("### Descarga de Datos Oficiales Filtrados")
    st.markdown("Exporte los microdatos reales correspondientes al filtro aplicado para su análisis en Excel o Python.")

    col_exp1, col_exp2 = st.columns(2)
    
    csv_bytes = df_filtrado.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
    with col_exp1:
        st.download_button(
            label="📥 Descargar Microdatos Oficiales (CSV)",
            data=csv_bytes,
            file_name=f"conectividad_oficial_filtrada_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

    output_excel = io.BytesIO()
    with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
        df_filtrado.to_excel(writer, sheet_name='Microdatos', index=False)
        pivot_pax_con_total.to_excel(writer, sheet_name='Matriz_Pasajeros')
        df_aero.to_excel(writer, sheet_name='Resumen_Operadores', index=False)
    output_excel.seek(0)

    with col_exp2:
        st.download_button(
            label="📥 Descargar Reporte Completo (Excel)",
            data=output_excel.getvalue(),
            file_name=f"reporte_conectividad_oficial_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
