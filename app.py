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
    'CPC': {'codigo': 'CPC', 'ciudad': 'San Martín de los Andes', 'keywords': ['CHAPELCO', 'SAN MARTIN DE LOS ANDES', 'SAN MARTÍN DE LOS ANDES', 'CARLOS CAMPOS', 'AVIADOR CARLOS CAMPOS', 'CPC']},
    'PMY': {'codigo': 'PMY', 'ciudad': 'Puerto Madryn', 'keywords': ['PUERTO MADRYN', 'MADRYN', 'EL TEHUELCHE', 'TEHUELCHE', 'PMY']},
    'VDM': {'codigo': 'VDM', 'ciudad': 'Viedma', 'keywords': ['VIEDMA', 'GOBERNADOR CASTELLO', 'EDGARDO CASTELLO', 'VDM']},
    'SDE': {'codigo': 'SDE', 'ciudad': 'Santiago del Estero', 'keywords': ['SANTIAGO DEL ESTERO', 'VICECOMODORO ARAGONES', 'ARAGONES', 'ARAGONÉS', 'SDE']},
    'RHD': {'codigo': 'RHD', 'ciudad': 'Termas de Río Hondo', 'keywords': ['TERMAS', 'RIO HONDO', 'RÍO HONDO', 'TERMAS DE RIO HONDO', 'RHD']},
    'UAQ': {'codigo': 'UAQ', 'ciudad': 'San Juan', 'keywords': ['SAN JUAN', 'DOMINGO FAUSTINO SARMIENTO', 'SARMIENTO', 'UAQ']},
    'LUQ': {'codigo': 'LUQ', 'ciudad': 'San Luis', 'keywords': ['SAN LUIS', 'BRIGADIER MAYOR CESAR RAUL OJEDA', 'CESAR RAUL OJEDA', 'CÉSAR RAÚL OJEDA', 'OJEDA', 'LUQ']},
    'RLO': {'codigo': 'RLO', 'ciudad': 'Valle del Conlara', 'keywords': ['VALLE DEL CONLARA', 'CONLARA', 'CONLA', 'MERLO', 'SANTA ROSA DEL CONLARA', 'RLO']},
    'CTC': {'codigo': 'CTC', 'ciudad': 'Catamarca', 'keywords': ['CATAMARCA', 'FELIPE VARELA', 'CORONEL FELIPE VARELA', 'JALIL HAMER', 'HAMER', 'CTC']},
    'IRJ': {'codigo': 'IRJ', 'ciudad': 'La Rioja', 'keywords': ['LA RIOJA', 'CAPITAN VICENTE ALMANDOS', 'CAP. VICENTE ALMANDOS', 'ALMANDOS', 'ALMAN', 'ALMONACID', 'IRJ']},
    'FMA': {'codigo': 'FMA', 'ciudad': 'Formosa', 'keywords': ['FORMOSA', 'EL PUCU', 'EL PUCÚ', 'FMA']},
    'RSA': {'codigo': 'RSA', 'ciudad': 'Santa Rosa', 'keywords': ['SANTA ROSA', 'RSA']},
    'RCU': {'codigo': 'RCU', 'ciudad': 'Río Cuarto', 'keywords': ['RIO CUARTO', 'RÍO CUARTO', 'AREA DE MATERIAL', 'RCU']},
    'PRA': {'codigo': 'PRA', 'ciudad': 'Paraná', 'keywords': ['PARANA', 'PARANÁ', 'URQUIZA', 'JUSTO JOSE DE URQUIZA', 'PRA']},
    'AFA': {'codigo': 'AFA', 'ciudad': 'San Rafael', 'keywords': ['SAN RAFAEL', 'SANTIAGO GERMANO', 'GERMANÓ', 'AFA']},
    'MLG': {'codigo': 'MLG', 'ciudad': 'Malargüe', 'keywords': ['MALARGUE', 'MALARGÜE', 'COMODORO RICARDO SALOMON', 'SALOMON', 'MLG']},
    'GPO': {'codigo': 'GPO', 'ciudad': 'General Pico', 'keywords': ['GENERAL PICO', 'PICO', 'GPO']},
    'RCQ': {'codigo': 'RCQ', 'ciudad': 'Reconquista', 'keywords': ['RECONQUISTA', 'DANIEL JUKIC', 'JUKIC', 'RCQ']},
    'OYA': {'codigo': 'OYA', 'ciudad': 'Goya', 'keywords': ['GOYA', 'OYA']},
    'CSZ': {'codigo': 'CSZ', 'ciudad': 'Sauce Viejo', 'keywords': ['SAUCE VIEJO', 'CSZ']},
    'PMQ': {'codigo': 'PMQ', 'ciudad': 'Perito Moreno', 'keywords': ['PERITO MORENO', 'PMQ']},
    'RYO': {'codigo': 'RYO', 'ciudad': 'Río Mayo', 'keywords': ['RIO MAYO', 'RÍO MAYO', 'RYO']},
    'JNI': {'codigo': 'JNI', 'ciudad': 'Junín', 'keywords': ['JUNIN', 'JUNÍN', 'JNI']}
}

def resolver_aeropuerto_texto(texto):
    if not texto or str(texto).strip() in ['', 'N/D', 'None', 'nan']:
        return "N/D", "Desconocido"
    t = str(texto).strip().upper()
    
    if t in AEROPUERTOS_EXHAUSTIVO:
        info = AEROPUERTOS_EXHAUSTIVO[t]
        return info['codigo'], info['ciudad']
        
    candidatos = []
    for code, info in AEROPUERTOS_EXHAUSTIVO.items():
        for kw in info['keywords']:
            if len(kw) > 3 and kw in t:
                candidatos.append((len(kw), info['codigo'], info['ciudad']))
            elif len(kw) <= 3 and re.search(r'\b' + re.escape(kw) + r'\b', t):
                candidatos.append((len(kw), info['codigo'], info['ciudad']))
                
    if candidatos:
        candidatos.sort(key=lambda x: x[0], reverse=True)
        return candidatos[0][1], candidatos[0][2]
        
    if len(t) == 3 and t.isalpha():
        return t, t
        
    limpio = t.replace('AEROPUERTO', '').replace('INT.', '').replace('INTERNACIONAL', '').strip().title()
    codigo_fallback = limpio[:3].upper() if len(limpio) >= 3 else t[:3].upper()
    return codigo_fallback, limpio[:18]

# -------------------------------------------------------------
# FORMATEADORES NUMÉRICOS ARGENTINOS
# -------------------------------------------------------------
def fmt_entero(val):
    try:
        if pd.isna(val):
            return "0"
        return f"{int(round(float(val))):,}".replace(",", ".")
    except Exception:
        return str(val)

def fmt_porcentaje(val):
    try:
        if pd.isna(val) or float(val) == 0:
            return "0,0%"
        num_str = f"{float(val):.1f}"
        return f"{num_str.replace('.', ',')}%"
    except Exception:
        return str(val)

def fmt_decimal(val):
    try:
        if pd.isna(val):
            return "0,0"
        num_str = f"{float(val):.1f}"
        return num_str.replace('.', ',')
    except Exception:
        return str(val)

# -------------------------------------------------------------
# LECTURA ROBUSTA DE ARCHIVOS (SIN INVENTAR DATOS)
# -------------------------------------------------------------
def extraer_bytes_fuente(fuente):
    if hasattr(fuente, 'getvalue'):
        return fuente.getvalue()
    if hasattr(fuente, 'seek'):
        fuente.seek(0)
    if hasattr(fuente, 'read'):
        data = fuente.read()
        if hasattr(fuente, 'seek'):
            fuente.seek(0)
        return data
    if isinstance(fuente, str) and os.path.exists(fuente):
        with open(fuente, 'rb') as f:
            return f.read()
    return None

@st.cache_data(show_spinner=False)
def procesar_dataset_bytes(raw_bytes, nombre_fuente="datos"):
    if not raw_bytes or len(raw_bytes) == 0:
        return pd.DataFrame()

    encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']
    separadores = [',', ';', '\t', '|']
    df = None

    for enc in encodings:
        try:
            texto = raw_bytes.decode(enc)
            lineas = [l for l in texto.splitlines() if l.strip()]
            if not lineas:
                continue
            primera_linea = lineas[0]
            sep_counts = {s: primera_linea.count(s) for s in separadores}
            mejor_sep = max(sep_counts, key=sep_counts.get)
            sep = mejor_sep if sep_counts[mejor_sep] >= 2 else None

            buf = io.StringIO(texto)
            try:
                if sep:
                    df = pd.read_csv(buf, sep=sep, engine='c', low_memory=False, on_bad_lines='skip', dtype=str)
                else:
                    df = pd.read_csv(buf, sep=None, engine='python', on_bad_lines='skip', dtype=str)
            except Exception:
                buf.seek(0)
                df = pd.read_csv(buf, sep=None, engine='python', on_bad_lines='skip', dtype=str)

            if df is not None and len(df.columns) >= 2 and len(df) > 0:
                break
        except Exception:
            continue

    if df is None or df.empty:
        return pd.DataFrame()

    cols_map = {c.strip(' "\'').lower().replace('ã±', 'ñ'): c for c in df.columns}
    df.rename(columns={v: k for k, v in cols_map.items()}, inplace=True)

    cand_aero = [c for c in df.columns if any(p in c for p in ['aerolinea', 'aerolínea', 'empresa', 'operador', 'linea', 'compania', 'compañía'])]
    if cand_aero:
        df['aerolinea'] = df[cand_aero[0]].fillna('Otras').astype(str).str.strip(' "\'')
    else:
        df['aerolinea'] = 'Todas las Aerolíneas (Total)'

    cand_pax = [c for c in df.columns if 'pasajero' in c or 'pax' in c]
    if cand_pax:
        s_pax = df[cand_pax[0]].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).str.strip(' "\'')
        df['pasajeros'] = pd.to_numeric(s_pax, errors='coerce').fillna(0).astype(np.int32)
    else:
        df['pasajeros'] = np.int32(0)

    cand_vue = [c for c in df.columns if 'vuelo' in c or 'movimiento' in c or 'operacion' in c]
    if cand_vue:
        s_vue = df[cand_vue[0]].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).str.strip(' "\'')
        df['vuelos'] = pd.to_numeric(s_vue, errors='coerce').fillna(1).astype(np.int16)
    else:
        df['vuelos'] = np.int16(1)

    cand_asi = [c for c in df.columns if 'asiento' in c or 'plaza' in c]
    if cand_asi:
        s_asi = df[cand_asi[0]].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).str.strip(' "\'')
        df['asientos'] = pd.to_numeric(s_asi, errors='coerce').fillna(0).astype(np.int32)
    else:
        df['asientos'] = np.int32(0)

    col_dia = next((c for c in df.columns if any(k in c for k in ['dia', 'día', 'day', 'da']) and 'diario' not in c), None)
    col_mes = next((c for c in df.columns if 'mes' in c or 'month' in c), None)
    col_ano = next((c for c in df.columns if any(k in c for k in ['año', 'aã±o', 'anio', 'year', 'ano', 'ao'])), None)
    col_fecha = next((c for c in df.columns if any(k in c for k in ['fecha', 'date', 'indice_tiempo', 'periodo'])), None)

    if col_ano and col_mes:
        s_ano_clean = df[col_ano].astype(str).str.strip(' "\'').str.replace(r'\.0$', '', regex=True).str.replace('.', '', regex=False).str.replace(',', '', regex=False)
        s_ano_ext = s_ano_clean.str.extract(r'(20\d{2}|19\d{2})')[0]
        num_ano = pd.to_numeric(s_ano_ext, errors='coerce')

        s_mes_str = df[col_mes].astype(str).str.strip(' "\'').str.lower()
        num_mes = s_mes_str.map(meses_map).fillna(pd.to_numeric(s_mes_str, errors='coerce')).fillna(1).clip(1, 12).astype(int)

        if col_dia:
            s_dia_num = pd.to_numeric(df[col_dia].astype(str).str.strip(' "\''), errors='coerce')
            num_dia = s_dia_num.fillna(1).clip(1, 31).astype(int)
        else:
            num_dia = 1

        df['fecha'] = pd.to_datetime(dict(year=num_ano, month=num_mes, day=num_dia), errors='coerce')
    elif col_fecha:
        df['fecha'] = pd.to_datetime(df[col_fecha], errors='coerce', dayfirst=True)
    else:
        df['fecha'] = pd.NaT

    df = df.dropna(subset=['fecha'])
    if df.empty:
        return pd.DataFrame()

    df['mes_num'] = df['fecha'].dt.month.astype(np.int8)
    df['ano_num'] = df['fecha'].dt.year.astype(np.int16)
    df['periodo_orden'] = (df['ano_num'] * 100 + df['mes_num']).astype(np.int32)
    df['periodo_mes_es'] = df['mes_num'].map(meses_es) + ' ' + df['ano_num'].astype(str)

    # Priorizar la columna 'Ruta' (Origen - Destino) para evitar nombres largos
    cand_ruta = next((c for c in df.columns if 'ruta' in c or 'trayecto' in c or 'puente' in c), None)
    col_dest = next((c for c in df.columns if any(k in c for k in ['destino', 'llegada']) and 'origen' not in c), None)
    col_orig = next((c for c in df.columns if any(k in c for k in ['origen', 'salida']) and 'destino' not in c), None)

    if cand_ruta:
        partes = df[cand_ruta].astype(str).str.strip(' "\'').str.split(r'\s*-\s*', expand=True)
        if partes.shape[1] >= 2:
            origen_raw = partes[0]
            destino_raw = partes[1]
        elif col_orig and col_dest:
            origen_raw = df[col_orig].astype(str).str.strip(' "\'')
            destino_raw = df[col_dest].astype(str).str.strip(' "\'')
        else:
            origen_raw = df[cand_ruta]
            destino_raw = df[cand_ruta]
    elif col_orig and col_dest:
        origen_raw = df[col_orig].astype(str).str.strip(' "\'')
        destino_raw = df[col_dest].astype(str).str.strip(' "\'')
    else:
        origen_raw = pd.Series(["AEP"] * len(df))
        destino_raw = pd.Series(["BRC"] * len(df))

    textos_unicos = pd.Series(pd.concat([origen_raw, destino_raw]).unique()).dropna()
    mapa_rapido = {t: resolver_aeropuerto_texto(t) for t in textos_unicos}

    df['origen_cod'] = origen_raw.map(lambda x: mapa_rapido.get(x, ("N/D", ""))[0])
    df['origen_ciu'] = origen_raw.map(lambda x: mapa_rapido.get(x, ("", "Desconocido"))[1])
    df['destino_cod'] = destino_raw.map(lambda x: mapa_rapido.get(x, ("N/D", ""))[0])
    df['destino_ciu'] = destino_raw.map(lambda x: mapa_rapido.get(x, ("", "Desconocido"))[1])

    df['origen_label'] = df['origen_cod'] + " (" + df['origen_ciu'] + ")"
    df['destino_label'] = df['destino_cod'] + " (" + df['destino_ciu'] + ")"
    df['tramo_label'] = df['origen_cod'] + " ➔ " + df['destino_cod'] + " (" + df['origen_ciu'] + " a " + df['destino_ciu'] + ")"

    pares_unicos = df[['origen_cod', 'origen_ciu', 'destino_cod', 'destino_ciu']].drop_duplicates()
    mapa_rutas = {}
    for _, r in pares_unicos.iterrows():
        p = sorted([(r['origen_cod'], r['origen_ciu']), (r['destino_cod'], r['destino_ciu'])], key=lambda x: x[0])
        mapa_rutas[(r['origen_cod'], r['destino_cod'])] = f"{p[0][0]} - {p[1][0]} ({p[0][1]} ⇄ {p[1][1]})"

    df['ruta_label'] = [mapa_rutas.get((o, d), "General") for o, d in zip(df['origen_cod'], df['destino_cod'])]

    for c in ['aerolinea', 'origen_label', 'destino_label', 'tramo_label', 'ruta_label', 'periodo_mes_es']:
        df[c] = df[c].astype('category')

    columnas_finales = [
        'fecha', 'ano_num', 'mes_num', 'periodo_orden', 'periodo_mes_es',
        'origen_cod', 'destino_cod', 'origen_label', 'destino_label', 'tramo_label', 'ruta_label',
        'aerolinea', 'pasajeros', 'vuelos', 'asientos'
    ]
    return df[columnas_finales]

# -------------------------------------------------------------
# SIDEBAR: FUENTE DE DATOS Y ENLACES OFICIALES
# -------------------------------------------------------------
st.sidebar.header("📁 Sincronización de Base Oficial")
st.sidebar.markdown(
    "Para garantizar estadísticas **100% reales y auditables**, este monitor se nutre "
    "exclusivamente de los registros oficiales de la Subsecretaría de Turismo y ANAC."
)

archivo_subido = st.sidebar.file_uploader(
    "Subir archivo CSV oficial de SINTA:",
    type=['csv', 'txt', 'gz', 'parquet'],
    help="Descargue el archivo 'conectividad_aerea.csv' desde el portal de SINTA y cárguelo aquí."
)

st.sidebar.markdown("---")
st.sidebar.subheader("🔗 Fuentes Oficiales de Datos")
st.sidebar.markdown("""
- 📊 [Tablero Conectividad Aérea SINTA](https://tableros.yvera.tur.ar/conectividad/)
- 🌐 [Datos Abiertos de Turismo (Yvera)](https://datos.yvera.gob.ar/dataset/conectividad-aerea)
- ✈️ [Estadísticas DNTA - ANAC](https://consultas-publicas.anac.gob.ar/estadisticas-dnta/)
- 📑 [Aterrizajes y Despegues (Transporte)](https://datos.transporte.gob.ar/dataset/aterrizajes-y-despegues-procesados-por-la-administracion-nacional-de-aviacion-civil-anac)
""")

# -------------------------------------------------------------
# CARGA DE DATOS (SIN SIMULACIÓN - DATOS INVENTADOS PROHIBIDOS)
# -------------------------------------------------------------
fuente_activa = None
df_raw = pd.DataFrame()

# 1. Intentar con archivo subido por el usuario en la sesión
if archivo_subido is not None:
    raw_b = extraer_bytes_fuente(archivo_subido)
    if raw_b and len(raw_b) > 0:
        df_raw = procesar_dataset_bytes(raw_b, archivo_subido.name)
        if not df_raw.empty:
            fuente_activa = f"Archivo subido: '{archivo_subido.name}'"
        else:
            st.sidebar.error(f"⚠️ El archivo '{archivo_subido.name}' ({len(raw_b):,} bytes) no pudo ser procesado.")
            try:
                preview = raw_b[:300].decode('utf-8', errors='replace')
                st.sidebar.caption("Primeros caracteres del archivo recibido:")
                st.sidebar.code(preview)
            except Exception:
                pass

# 2. Si no hay archivo subido, buscar automáticamente en el repositorio GitHub
if df_raw.empty:
    candidatos_locales = [
        'conectividad_aerea.csv', 'conectividad-aerea.csv',
        'datos_cabotaje.csv', 'datos_sinta.csv', 'base_cabotaje.csv'
    ]
    try:
        for f in os.listdir('.'):
            if f.lower().endswith('.csv') and f not in candidatos_locales:
                candidatos_locales.append(f)
    except Exception:
        pass

    for nom in candidatos_locales:
        if os.path.exists(nom):
            raw_b = extraer_bytes_fuente(nom)
            if raw_b and len(raw_b) > 0:
                df_cand = procesar_dataset_bytes(raw_b, nom)
                if not df_cand.empty:
                    df_raw = df_cand
                    fuente_activa = f"Archivo en repositorio: '{nom}'"
                    break

# -------------------------------------------------------------
# PANTALLA PRINCIPAL
# -------------------------------------------------------------
st.title("✈️ Monitor de Rutas Aéreas de Cabotaje")
st.markdown("Visualización, análisis competitivo, estacionalidad y benchmarking de conectividad aérea a partir de microdatos oficiales.")

# COMPROBACIÓN ESTRICTA: SI NO HAY DATOS REALES, DETENERSE
if df_raw.empty:
    st.error("⛔ **NO HAY BASE DE DATOS OFICIAL CARGADA**")
    st.warning(
        "Está terminantemente prohibido generar o inventar datos ficticios. "
        "Para utilizar el monitor con información verídica:\n\n"
        "1. **Cargue su archivo oficial** `conectividad_aerea.csv` en el panel lateral izquierdo.\n"
        "2. **O coloque el archivo** `conectividad_aerea.csv` en la carpeta principal de su repositorio en GitHub para que esté disponible de forma permanente.\n\n"
        "Puede descargar la base actualizada desde:\n"
        "- [Tablero de Conectividad Aérea SINTA](https://tableros.yvera.tur.ar/conectividad/)\n"
        "- [Portal de Datos Abiertos de Turismo](https://datos.yvera.gob.ar/dataset/conectividad-aerea)"
    )
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
# FILTROS DE BÚSQUEDA Y BOTÓN BUSCAR VUELOS
# -------------------------------------------------------------
st.subheader("🔍 Filtros de Búsqueda de Vuelos")

rutas_disponibles = sorted(df_raw['ruta_label'].dropna().unique().tolist())
origenes_disponibles = sorted(df_raw['origen_label'].dropna().unique().tolist())
destinos_disponibles = sorted(df_raw['destino_label'].dropna().unique().tolist())

col_f1, col_f2, col_f3 = st.columns([2, 1, 1])

with col_f1:
    sel_rutas = st.multiselect(
        "🗺️ Ruta (Ida y Vuelta):",
        options=rutas_disponibles,
        help="Agrupa ambos sentidos de vuelo (ej. Bariloche ⇄ Ezeiza, Jujuy ⇄ Aeroparque)."
    )

with col_f2:
    sel_origenes = st.multiselect(
        "🛫 Aeropuerto de Salida (Origen):",
        options=origenes_disponibles
    )

with col_f3:
    sel_destinos = st.multiselect(
        "🛬 Aeropuerto de Llegada (Destino):",
        options=destinos_disponibles
    )

# Rango de fechas ajustado automáticamente a las fechas reales de la base
col_d1, col_d2 = st.columns(2)

def_desde = max(f_min_total, date(f_max_total.year, 1, 1)) if (f_max_total - f_min_total).days > 365 else f_min_total
def_hasta = f_max_total

with col_d1:
    f_desde = st.date_input(
        "📅 Desde:",
        value=def_desde,
        min_value=f_min_total,
        max_value=f_max_total,
        help=f"Fecha inicial dentro de la base oficial ({f_min_total.strftime('%d/%m/%Y')} a {f_max_total.strftime('%d/%m/%Y')})."
    )

with col_d2:
    f_hasta = st.date_input(
        "📅 Hasta:",
        value=def_hasta,
        min_value=f_min_total,
        max_value=f_max_total,
        help=f"Fecha final dentro de la base oficial ({f_min_total.strftime('%d/%m/%Y')} a {f_max_total.strftime('%d/%m/%Y')})."
    )

# Botones de control solicitados
col_b1, col_b2 = st.columns([1, 4])
with col_b1:
    btn_buscar = st.button("🔍 Buscar Vuelos", type="primary", use_container_width=True)

# Mantener estado de búsqueda activo una vez presionado
if 'busqueda_realizada' not in st.session_state:
    st.session_state['busqueda_realizada'] = True

if btn_buscar:
    st.session_state['busqueda_realizada'] = True

# Aplicar filtros
mask = (df_raw['fecha'].dt.date >= f_desde) & (df_raw['fecha'].dt.date <= f_hasta)

if sel_rutas:
    mask &= df_raw['ruta_label'].isin(sel_rutas)
if sel_origenes:
    mask &= df_raw['origen_label'].isin(sel_origenes)
if sel_destinos:
    mask &= df_raw['destino_label'].isin(sel_destinos)

df_filtrado = df_raw[mask].copy()

if df_filtrado.empty:
    st.warning(
        f"⚠️ **No se encontraron vuelos para los criterios y rango de fechas seleccionados.**  \n"
        f"• Verifique que el rango de fechas seleccionado ({f_desde.strftime('%d/%m/%Y')} a {f_hasta.strftime('%d/%m/%Y')}) "
        f"corresponda al período del dataset cargado ({f_min_total.strftime('%d/%m/%Y')} a {f_max_total.strftime('%d/%m/%Y')}).  \n"
        f"• Si seleccionó una ruta específica, pruebe dejando vacíos los selectores individuales de Origen/Destino o ampliando las fechas."
    )
    st.stop()

# -------------------------------------------------------------
# KPIs PRINCIPALES
# -------------------------------------------------------------
st.markdown("---")
st.subheader("📈 Resumen Ejecutivo de Operación")

total_pax = df_filtrado['pasajeros'].sum()
total_vue = df_filtrado['vuelos'].sum()
total_asi = df_filtrado['asientos'].sum()
prom_pax_vuelo = total_pax / total_vue if total_vue > 0 else 0
load_factor_global = (total_pax / total_asi * 100) if total_asi > 0 else 0

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Pasajeros Transportados", fmt_entero(total_pax))
k2.metric("Vuelos Realizados", fmt_entero(total_vue))
k3.metric("Asientos Ofrecidos", fmt_entero(total_asi))
k4.metric("Ocupación Promedio", fmt_porcentaje(load_factor_global))
k5.metric("Promedio Pax / Vuelo", fmt_decimal(prom_pax_vuelo))

# -------------------------------------------------------------
# TABS DE ANÁLISIS
# -------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Evolución Temporal",
    "🏢 Cuotas de Mercado & HHI",
    "🛫 Desglose por Tramo / Sentido",
    "📋 Matriz Detallada",
    "📥 Descargar Datos Oficiales"
])

# TAB 1: EVOLUCIÓN TEMPORAL
with tab1:
    st.markdown("### Evolución Mensual de Pasajeros y Vuelos")
    df_tempo = df_filtrado.groupby(['periodo_orden', 'periodo_mes_es', 'aerolinea'], observed=True).agg(
        pasajeros=('pasajeros', 'sum'),
        vuelos=('vuelos', 'sum'),
        asientos=('asientos', 'sum')
    ).reset_index().sort_values(by='periodo_orden')

    if not df_tempo.empty and df_tempo['pasajeros'].sum() > 0:
        fig_bar = px.bar(
            df_tempo,
            x='periodo_mes_es',
            y='pasajeros',
            color='aerolinea',
            title="Pasajeros Mensuales por Aerolínea",
            labels={'periodo_mes_es': 'Período', 'pasajeros': 'Pasajeros', 'aerolinea': 'Aerolínea'},
            barmode='stack'
        )
        fig_bar.update_layout(xaxis_tickangle=-45, legend_title_text='Aerolínea')
        st.plotly_chart(fig_bar, use_container_width=True)

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
            title="Factor de Ocupación Promedio (%) Mensual",
            labels={'periodo_mes_es': 'Período', 'ocupacion_%': 'Ocupación (%)'},
            markers=True
        )
        fig_line.update_layout(yaxis_range=[0, 105], xaxis_tickangle=-45)
        st.plotly_chart(fig_line, use_container_width=True)

# TAB 2: CUOTAS DE MERCADO & HHI
with tab2:
    st.markdown("### Participación de Mercado y Concentración (HHI)")
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

    hhi = (df_aero['cuota_pax_%'] ** 2).sum()
    if hhi < 1500:
        hhi_cat = "Mercado Competitivo / Desconcentrado"
    elif hhi <= 2500:
        hhi_cat = "Mercado Moderadamente Concentrado"
    else:
        hhi_cat = "Mercado Altamente Concentrado / Oligopólico"

    col_h1, col_h2 = st.columns([1, 2])
    with col_h1:
        st.metric("Índice HHI de Concentración", f"{hhi:.0f} pts")
        st.info(f"**Categoría:** {hhi_cat}")
        
        fig_pie = px.pie(
            df_aero,
            names='aerolinea',
            values='pasajeros',
            title="Market Share de Pasajeros",
            hole=0.4
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_h2:
        st.markdown("**Tabla de Competitividad por Operador**")
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

# TAB 3: DESGLOSE POR TRAMO
with tab3:
    st.markdown("### Comparación por Sentido de Vuelo (Ida vs. Vuelta)")
    df_tramo = df_filtrado.groupby(['tramo_label', 'aerolinea'], observed=True).agg(
        pasajeros=('pasajeros', 'sum'),
        vuelos=('vuelos', 'sum'),
        asientos=('asientos', 'sum')
    ).reset_index()
    df_tramo = df_tramo[df_tramo['vuelos'] > 0]
    df_tramo['ocupacion_%'] = np.where(df_tramo['asientos'] > 0, (df_tramo['pasajeros'] / df_tramo['asientos']) * 100, 0)
    df_tramo['prom_pax_vuelo'] = np.where(df_tramo['vuelos'] > 0, df_tramo['pasajeros'] / df_tramo['vuelos'], 0)

    fig_tramo = px.bar(
        df_tramo,
        x='tramo_label',
        y='pasajeros',
        color='aerolinea',
        title="Pasajeros por Tramo y Aerolínea",
        labels={'tramo_label': 'Tramo de Vuelo', 'pasajeros': 'Pasajeros', 'aerolinea': 'Aerolínea'},
        barmode='group'
    )
    fig_tramo.update_layout(xaxis_tickangle=-25)
    st.plotly_chart(fig_tramo, use_container_width=True)

    df_t_disp = df_tramo.copy()
    df_t_disp['Pasajeros'] = df_t_disp['pasajeros'].apply(fmt_entero)
    df_t_disp['Vuelos'] = df_t_disp['vuelos'].apply(fmt_entero)
    df_t_disp['Asientos'] = df_t_disp['asientos'].apply(fmt_entero)
    df_t_disp['Ocupación'] = df_t_disp['ocupacion_%'].apply(fmt_porcentaje)
    df_t_disp['Pax/Vuelo'] = df_t_disp['prom_pax_vuelo'].apply(fmt_decimal)

    st.dataframe(
        df_t_disp[['tramo_label', 'aerolinea', 'Pasajeros', 'Vuelos', 'Asientos', 'Ocupación', 'Pax/Vuelo']].rename(
            columns={'tramo_label': 'Tramo', 'aerolinea': 'Aerolínea'}
        ),
        use_container_width=True,
        hide_index=True
    )

# TAB 4: MATRIZ DETALLADA CON TOTALES
with tab4:
    st.markdown("### Matriz de Pasajeros por Período y Aerolínea")
    
    pivot_pax = df_filtrado.pivot_table(
        index='periodo_mes_es',
        columns='aerolinea',
        values='pasajeros',
        aggfunc='sum',
        fill_value=0,
        observed=True
    )
    orden_periodos = df_filtrado.sort_values(by='periodo_orden')['periodo_mes_es'].unique().tolist()
    pivot_pax = pivot_pax.reindex([p for p in orden_periodos if p in pivot_pax.index])

    pivot_pax['TOTAL FILA'] = pivot_pax.sum(axis=1)
    fila_total = pivot_pax.sum(axis=0)
    fila_total.name = 'TOTAL GENERAL'
    pivot_pax_con_total = pd.concat([pivot_pax, pd.DataFrame(fila_total).T])

    try:
        pivot_disp = pivot_pax_con_total.map(fmt_entero)
    except AttributeError:
        pivot_disp = pivot_pax_con_total.applymap(fmt_entero)
        
    st.dataframe(pivot_disp, use_container_width=True)

# TAB 5: DESCARGAS DE DATOS AUDITADOS
with tab5:
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
    output_excel.seek(0)

    with col_exp2:
        st.download_button(
            label="📥 Descargar Reporte Completo (Excel)",
            data=output_excel.getvalue(),
            file_name=f"reporte_conectividad_oficial_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
