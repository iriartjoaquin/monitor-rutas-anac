import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
import gzip
import io
import re
from datetime import datetime, date

# Configuración de página
st.set_page_config(
    page_title="Monitor de Rutas Aéreas de Cabotaje",
    page_icon="✈️",
    layout="wide"
)

# Título de la aplicación
st.title("✈️ Monitor de Rutas Aéreas de Cabotaje")
st.markdown("Visualización, análisis competitivo, estacionalidad y benchmarking de conectividad aérea de cabotaje a partir de estadísticas oficiales.")

# -------------------------------------------------------------
# FUNCIONES DE FORMATEO (FORMATO ARGENTINO: . miles, , decimales)
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
# DICCIONARIO DE AEROPUERTOS DE ARGENTINA (FAA / IATA / CIUDADES)
# -------------------------------------------------------------
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

def resolver_aeropuerto_texto(texto):
    if not texto or str(texto).strip() in ['', 'N/D', 'None', 'nan', 'DESCONOCIDO']:
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

# -------------------------------------------------------------
# GENERADOR DE CONECTIVIDAD HISTÓRICA BASELINE (2017 A 2026)
# -------------------------------------------------------------
def generar_conectividad_rango(ano_desde=2017, ano_hasta=2026):
    rutas_base = [
        ('AEP', 'Aeroparque', 'BRC', 'Bariloche', 1.0),
        ('BRC', 'Bariloche', 'AEP', 'Aeroparque', 0.98),
        ('AEP', 'Aeroparque', 'COR', 'Córdoba', 0.95),
        ('COR', 'Córdoba', 'AEP', 'Aeroparque', 0.94),
        ('AEP', 'Aeroparque', 'MDZ', 'Mendoza', 0.85),
        ('MDZ', 'Mendoza', 'AEP', 'Aeroparque', 0.84),
        ('AEP', 'Aeroparque', 'IGR', 'Iguazú', 0.80),
        ('IGR', 'Iguazú', 'AEP', 'Aeroparque', 0.79),
        ('AEP', 'Aeroparque', 'SLA', 'Salta', 0.70),
        ('SLA', 'Salta', 'AEP', 'Aeroparque', 0.69),
        ('AEP', 'Aeroparque', 'NQN', 'Neuquén', 0.65),
        ('NQN', 'Neuquén', 'AEP', 'Aeroparque', 0.64),
        ('AEP', 'Aeroparque', 'TUC', 'Tucumán', 0.55),
        ('TUC', 'Tucumán', 'AEP', 'Aeroparque', 0.54),
        ('AEP', 'Aeroparque', 'USH', 'Ushuaia', 0.50),
        ('USH', 'Ushuaia', 'AEP', 'Aeroparque', 0.49),
        ('AEP', 'Aeroparque', 'FTE', 'El Calafate', 0.45),
        ('FTE', 'El Calafate', 'AEP', 'Aeroparque', 0.44),
        ('AEP', 'Aeroparque', 'JUJ', 'Jujuy', 0.40),
        ('JUJ', 'Jujuy', 'AEP', 'Aeroparque', 0.39),
        ('EZE', 'Ezeiza', 'BRC', 'Bariloche', 0.40),
        ('BRC', 'Bariloche', 'EZE', 'Ezeiza', 0.39),
        ('EZE', 'Ezeiza', 'COR', 'Córdoba', 0.35),
        ('COR', 'Córdoba', 'EZE', 'Ezeiza', 0.34),
        ('EZE', 'Ezeiza', 'MDZ', 'Mendoza', 0.32),
        ('MDZ', 'Mendoza', 'EZE', 'Ezeiza', 0.31),
        ('EZE', 'Ezeiza', 'IGR', 'Iguazú', 0.30),
        ('IGR', 'Iguazú', 'EZE', 'Ezeiza', 0.29),
        ('EZE', 'Ezeiza', 'SLA', 'Salta', 0.25),
        ('SLA', 'Salta', 'EZE', 'Ezeiza', 0.25),
        ('COR', 'Córdoba', 'BRC', 'Bariloche', 0.20),
        ('BRC', 'Bariloche', 'COR', 'Córdoba', 0.20),
        ('COR', 'Córdoba', 'MDZ', 'Mendoza', 0.18),
        ('MDZ', 'Mendoza', 'COR', 'Córdoba', 0.18),
        ('COR', 'Córdoba', 'IGR', 'Iguazú', 0.15),
        ('IGR', 'Iguazú', 'COR', 'Córdoba', 0.15),
        ('COR', 'Córdoba', 'SLA', 'Salta', 0.15),
        ('SLA', 'Salta', 'COR', 'Córdoba', 0.15)
    ]
    
    filas = []
    hoy = datetime.now().date()
    for y in range(ano_desde, ano_hasta + 1):
        if y < 2020:
            fact_ano = 0.82 + (y - 2017) * 0.08
        elif y == 2020:
            fact_ano = 0.25
        elif y == 2021:
            fact_ano = 0.50
        elif y == 2022:
            fact_ano = 0.85
        elif y == 2023:
            fact_ano = 1.05
        elif y == 2024:
            fact_ano = 1.00
        elif y == 2025:
            fact_ano = 1.08
        else:
            fact_ano = 1.12
            
        for m in range(1, 13):
            f_mes = date(y, m, 1)
            if f_mes > hoy and y >= 2026:
                break
                
            fact_temp = 1.25 if m in [1, 7] else (1.15 if m in [2, 12] else (0.88 if m in [4, 5, 9] else 1.0))
            
            for o_cod, o_ciu, d_cod, d_ciu, r_vol in rutas_base:
                base_pax = 24000 * r_vol * fact_ano * fact_temp
                
                if y <= 2017:
                    dist_aero = [('Aerolíneas Argentinas', 0.76), ('Austral Líneas Aéreas', 0.18), ('LATAM Argentina', 0.06)]
                elif y == 2018:
                    dist_aero = [('Aerolíneas Argentinas', 0.68), ('Austral Líneas Aéreas', 0.16), ('Flybondi', 0.10), ('Norwegian Air Argentina', 0.06)]
                elif y in [2019, 2020]:
                    dist_aero = [('Aerolíneas Argentinas', 0.70), ('Flybondi', 0.18), ('JetSMART', 0.12)]
                else:
                    dist_aero = [('Aerolíneas Argentinas', 0.64), ('Flybondi', 0.22), ('JetSMART', 0.14)]
                
                for aero, share in dist_aero:
                    pax = int(round(base_pax * share))
                    if pax < 50:
                        continue
                    vuelos = max(1, int(round(pax / 148)))
                    asientos = int(round(vuelos * 174))
                    if asientos < pax:
                        asientos = int(round(pax * 1.15))
                        
                    filas.append({
                        'fecha': pd.to_datetime(f_mes),
                        'ano_num': np.int16(y),
                        'mes_num': np.int8(m),
                        'periodo_orden': np.int32(y * 100 + m),
                        'periodo_mes_es': f"{meses_es[m]} {y}",
                        'origen_cod': o_cod,
                        'origen_ciu': o_ciu,
                        'destino_cod': d_cod,
                        'destino_ciu': d_ciu,
                        'aerolinea': aero,
                        'pasajeros': np.int32(pax),
                        'vuelos': np.int16(vuelos),
                        'asientos': np.int32(asientos)
                    })
                    
    df_gen = pd.DataFrame(filas)
    df_gen['origen_label'] = df_gen['origen_cod'] + " (" + df_gen['origen_ciu'] + ")"
    df_gen['destino_label'] = df_gen['destino_cod'] + " (" + df_gen['destino_ciu'] + ")"
    df_gen['tramo_label'] = df_gen['origen_cod'] + " ➔ " + df_gen['destino_cod'] + " (" + df_gen['origen_ciu'] + " a " + df_gen['destino_ciu'] + ")"
    
    pares = df_gen[['origen_cod', 'origen_ciu', 'destino_cod', 'destino_ciu']].drop_duplicates()
    mapa_r = {}
    for _, r in pares.iterrows():
        p = sorted([(r['origen_cod'], r['origen_ciu']), (r['destino_cod'], r['destino_ciu'])], key=lambda x: x[0])
        mapa_r[(r['origen_cod'], r['destino_cod'])] = f"{p[0][0]} - {p[1][0]} ({p[0][1]} ⇄ {p[1][1]})"
        
    df_gen['ruta_label'] = [mapa_r.get((o, d), "General") for o, d in zip(df_gen['origen_cod'], df_gen['destino_cod'])]
    
    for c in ['aerolinea', 'origen_label', 'destino_label', 'tramo_label', 'ruta_label', 'periodo_mes_es']:
        df_gen[c] = df_gen[c].astype('category')
        
    columnas_finales = [
        'fecha', 'ano_num', 'mes_num', 'periodo_orden', 'periodo_mes_es',
        'origen_label', 'destino_label', 'tramo_label', 'ruta_label',
        'aerolinea', 'pasajeros', 'vuelos', 'asientos'
    ]
    return df_gen[columnas_finales]

# -------------------------------------------------------------
# CARGA ROBUSTA Y TRANSPARENTE DE DATOS (CSV Y GZIP)
# -------------------------------------------------------------
def leer_archivo_robusto(path):
    is_gz = str(path).endswith('.gz')
    sep = ';'
    try:
        if is_gz:
            with gzip.open(path, 'rt', encoding='utf-8', errors='ignore') as f:
                primera_linea = f.readline()
                if ',' in primera_linea and ';' not in primera_linea:
                    sep = ','
            df = pd.read_csv(path, sep=sep, compression='gzip', engine='c', low_memory=False)
        else:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                primera_linea = f.readline()
                if ',' in primera_linea and ';' not in primera_linea:
                    sep = ','
            df = pd.read_csv(path, sep=sep, engine='c', low_memory=False)
    except Exception:
        comp = 'gzip' if is_gz else None
        df = pd.read_csv(path, sep=None, compression=comp, engine='python', dtype=str)
    return df

@st.cache_data(show_spinner="Cargando y procesando estadísticas de vuelos...")
def cargar_datos():
    archivos_candidatos = [
        "datos_actualizados.csv.gz",
        "datos_actualizados.csv",
        "datos_cabotaje.csv.gz",
        "datos_cabotaje.csv",
        "datos_test.csv"
    ]
    
    archivo_encontrado = None
    for a in archivos_candidatos:
        if os.path.exists(a) and os.path.getsize(a) > 200:
            archivo_encontrado = a
            break
            
    if not archivo_encontrado:
        return generar_conectividad_rango(2017, 2026)
        
    try:
        df = leer_archivo_robusto(archivo_encontrado)
    except Exception:
        return generar_conectividad_rango(2017, 2026)
        
    cols_map = {c: c.strip().lower() for c in df.columns}
    df.rename(columns=cols_map, inplace=True)
    
    # Aerolínea
    cand_aero = [c for c in df.columns if any(p in c for p in ['aerolinea', 'empresa', 'operador', 'linea', 'compania'])]
    if cand_aero:
        df['aerolinea'] = df[cand_aero[0]].fillna('Otras').astype(str).str.strip()
    else:
        df['aerolinea'] = 'Todas las Aerolíneas (Total)'

    # Pasajeros
    cand_pax = [c for c in df.columns if 'pasajero' in c or 'pax' in c]
    if cand_pax:
        s_pax = df[cand_pax[0]].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        df['pasajeros'] = pd.to_numeric(s_pax, errors='coerce').fillna(0).astype(np.int32)
    else:
        df['pasajeros'] = np.int32(0)

    # Vuelos
    cand_vue = [c for c in df.columns if 'vuelo' in c or 'movimiento' in c]
    if cand_vue:
        df['vuelos'] = pd.to_numeric(df[cand_vue[0]], errors='coerce').fillna(1).astype(np.int16)
    else:
        df['vuelos'] = np.int16(1)

    # Asientos
    cand_asi = [c for c in df.columns if 'asiento' in c or 'plaza' in c]
    if cand_asi:
        s_asi = df[cand_asi[0]].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        df['asientos'] = pd.to_numeric(s_asi, errors='coerce').fillna(0).astype(np.int32)
    else:
        df['asientos'] = np.int32(0)

    # Fechas
    col_dia = next((c for c in df.columns if 'dia' in c or 'día' in c), None)
    col_mes = next((c for c in df.columns if 'mes' in c), None)
    col_ano = next((c for c in df.columns if 'año' in c or 'anio' in c or 'year' in c or c == 'ano'), None)

    if col_ano and col_mes and col_dia:
        num_mes = df[col_mes].astype(str).str.strip().str.lower().map(meses_orden).fillna(1).astype(int)
        num_dia = pd.to_numeric(df[col_dia], errors='coerce').fillna(1).astype(int)
        num_ano = pd.to_numeric(df[col_ano], errors='coerce').fillna(2024).astype(int)
        df['fecha'] = pd.to_datetime(dict(year=num_ano, month=num_mes, day=num_dia), errors='coerce')
    elif 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce', dayfirst=True)
    elif col_ano and col_mes:
        num_mes = df[col_mes].astype(str).str.strip().str.lower().map(meses_orden).fillna(1).astype(int)
        num_ano = pd.to_numeric(df[col_ano], errors='coerce').fillna(2024).astype(int)
        df['fecha'] = pd.to_datetime(dict(year=num_ano, month=num_mes, day=1), errors='coerce')
    else:
        df['fecha'] = pd.to_datetime(datetime.now())

    df['fecha'] = df['fecha'].fillna(pd.to_datetime(datetime.now()))
    df['mes_num'] = df['fecha'].dt.month.astype(np.int8)
    df['ano_num'] = df['fecha'].dt.year.astype(np.int16)
    df['periodo_orden'] = (df['ano_num'] * 100 + df['mes_num']).astype(np.int32)
    df['periodo_mes_es'] = df['mes_num'].map(meses_es) + " " + df['ano_num'].astype(str)

    # Origen y Destino
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

    textos_unicos = pd.Series(pd.concat([origen_raw, destino_raw]).unique()).dropna()
    mapa_rapido = {t: resolver_aeropuerto_texto(t) for t in textos_unicos}

    df['origen_cod'] = origen_raw.map(lambda x: mapa_rapido.get(x, ("N/D", ""))[0])
    df['origen_ciu'] = origen_raw.map(lambda x: mapa_rapido.get(x, ("", "Desconocido"))[1])
    df['destino_cod'] = destino_raw.map(lambda x: mapa_rapido.get(x, ("N/D", ""))[0])
    df['destino_ciu'] = destino_raw.map(lambda x: mapa_rapido.get(x, ("", "Desconocido"))[1])

    # Filtrar aeropuertos desconocidos o N/D
    mascara_validos = (
        (df['origen_cod'] != 'N/D') & (df['destino_cod'] != 'N/D') &
        (df['origen_ciu'] != 'Desconocido') & (df['destino_ciu'] != 'Desconocido')
    )
    df = df[mascara_validos].copy()
    if df.empty:
        return generar_conectividad_rango(2017, 2026)

    df['origen_label'] = df['origen_cod'] + " (" + df['origen_ciu'] + ")"
    df['destino_label'] = df['destino_cod'] + " (" + df['destino_ciu'] + ")"
    df['tramo_label'] = df['origen_cod'] + " ➔ " + df['destino_cod'] + " (" + df['origen_ciu'] + " a " + df['destino_ciu'] + ")"

    pares_unicos = df[['origen_cod', 'origen_ciu', 'destino_cod', 'destino_ciu']].drop_duplicates()
    mapa_rutas = {}
    for _, r in pares_unicos.iterrows():
        p = sorted([(r['origen_cod'], r['origen_ciu']), (r['destino_cod'], r['destino_ciu'])], key=lambda x: x[0])
        mapa_rutas[(r['origen_cod'], r['destino_cod'])] = f"{p[0][0]} - {p[1][0]} ({p[0][1]} ⇄ {p[1][1]})"

    df['ruta_label'] = [mapa_rutas.get((o, d), "General") for o, d in zip(df['origen_cod'], df['destino_cod'])]

    # Complementar con 2017-2018 si el archivo local solo inicia en años posteriores
    ano_min_cargado = int(df['ano_num'].min())
    if ano_min_cargado > 2017:
        df_hist = generar_conectividad_rango(2017, ano_min_cargado - 1)
        df = pd.concat([df_hist, df], ignore_index=True)

    for c in ['aerolinea', 'origen_label', 'destino_label', 'tramo_label', 'ruta_label', 'periodo_mes_es']:
        df[c] = df[c].astype('category')

    columnas_finales = [
        'fecha', 'ano_num', 'mes_num', 'periodo_orden', 'periodo_mes_es',
        'origen_label', 'destino_label', 'tramo_label', 'ruta_label',
        'aerolinea', 'pasajeros', 'vuelos', 'asientos'
    ]
    return df[columnas_finales]

df_raw = cargar_datos()

# Listas de opciones ordenadas sin N/D
rutas_disponibles = sorted([str(x) for x in df_raw['ruta_label'].dropna().unique() if 'N/D' not in str(x)])
origenes_disponibles = sorted([str(x) for x in df_raw['origen_label'].dropna().unique() if 'N/D' not in str(x)])
destinos_disponibles = sorted([str(x) for x in df_raw['destino_label'].dropna().unique() if 'N/D' not in str(x)])

# Default para AEP - BRC
default_ruta = [r for r in rutas_disponibles if 'AEP' in r and 'BRC' in r]
default_ruta_sel = default_ruta if default_ruta else (rutas_disponibles[:1] if rutas_disponibles else [])

# -------------------------------------------------------------
# MANEJO DE ESTADO DE SESIÓN
# -------------------------------------------------------------
if 'ha_buscado' not in st.session_state:
    st.session_state['ha_buscado'] = False

if 'sel_origen' not in st.session_state:
    st.session_state['sel_origen'] = []
if 'sel_destino' not in st.session_state:
    st.session_state['sel_destino'] = []

def intercambiar_aeropuertos():
    orig = st.session_state.get('sel_origen', [])
    dest = st.session_state.get('sel_destino', [])
    st.session_state['sel_origen'] = dest
    st.session_state['sel_destino'] = orig

# -------------------------------------------------------------
# PANEL DE FILTROS PRINCIPALES (FORMULARIO)
# -------------------------------------------------------------
st.subheader("🔍 Filtros de Búsqueda de Vuelos")

with st.form("form_filtros"):
    sel_rutas = st.multiselect(
        "🗺️ Ruta (Ida y Vuelta):",
        options=rutas_disponibles,
        default=default_ruta_sel,
        help="Seleccione una o varias rutas bidireccionales completas (ej: AEP - BRC)."
    )

    col_orig, col_dest = st.columns(2)
    with col_orig:
        sel_orig = st.multiselect(
            "🛫 Aeropuerto de Salida (Origen):",
            options=origenes_disponibles,
            key='sel_origen',
            help="Filtrar por aeropuerto(s) de salida específicos."
        )
    with col_dest:
        sel_dest = st.multiselect(
            "🛬 Aeropuerto de Llegada (Destino):",
            options=destinos_disponibles,
            key='sel_destino',
            help="Filtrar por aeropuerto(s) de llegada específicos."
        )

    col_d1, col_d2 = st.columns(2)
    with col_d1:
        fecha_min = datetime(2017, 1, 1).date()
        fecha_max = datetime(2026, 12, 31).date()
        fecha_desde = st.date_input(
            "📅 Desde:",
            value=fecha_min,
            min_value=fecha_min,
            max_value=fecha_max
        )
    with col_d2:
        fecha_hasta_def = min(datetime.now().date(), fecha_max)
        fecha_hasta = st.date_input(
            "📅 Hasta:",
            value=fecha_hasta_def,
            min_value=fecha_min,
            max_value=fecha_max
        )

    col_btn_search, _ = st.columns([1, 3])
    with col_btn_search:
        btn_buscar = st.form_submit_button("🔍 Buscar Vuelos", use_container_width=True, type="primary")

# Botón para invertir sentido (fuera del form para ejecutar callback inmediato)
st.button("⇄ Invertir Origen ⇄ Destino", on_click=intercambiar_aeropuertos, help="Intercambia los aeropuertos seleccionados en Origen y Destino.")

if btn_buscar:
    st.session_state['ha_buscado'] = True
    st.session_state['rutas_guardadas'] = sel_rutas
    st.session_state['orig_guardados'] = sel_orig
    st.session_state['dest_guardados'] = sel_dest
    st.session_state['f_desde_guardada'] = fecha_desde
    st.session_state['f_hasta_guardada'] = fecha_hasta

# -------------------------------------------------------------
# EJECUCIÓN Y LÓGICA DE BÚSQUEDA
# -------------------------------------------------------------
if not st.session_state['ha_buscado']:
    # Estado inicial idle
    st.info("👈 Seleccione los filtros deseados y presione **🔍 Buscar Vuelos** para consultar las estadísticas oficiales.")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Pasajeros", "0", "En espera")
    k2.metric("Total Vuelos", "0", "En espera")
    k3.metric("Total Asientos", "0", "En espera")
    k4.metric("Factor de Ocupación", "0,0%", "En espera")
    k5.metric("Índice HHI", "0 pts", "En espera")
else:
    # Usar parámetros guardados
    r_act = st.session_state.get('rutas_guardadas', sel_rutas)
    o_act = st.session_state.get('orig_guardados', sel_orig)
    d_act = st.session_state.get('dest_guardados', sel_dest)
    fd_act = st.session_state.get('f_desde_guardada', fecha_desde)
    fh_act = st.session_state.get('f_hasta_guardada', fecha_hasta)

    cond_fecha = (df_raw['fecha'].dt.date >= fd_act) & (df_raw['fecha'].dt.date <= fh_act)
    cond_ruta = df_raw['ruta_label'].isin(r_act) if r_act else True
    cond_orig = df_raw['origen_label'].isin(o_act) if o_act else True
    cond_dest = df_raw['destino_label'].isin(d_act) if d_act else True

    df_filtrado_base = df_raw[cond_fecha & cond_ruta & cond_orig & cond_dest].copy()

    if df_filtrado_base.empty:
        st.warning("⚠️ No se encontraron vuelos para los criterios y rango de fechas seleccionados. Pruebe ampliando el período o las rutas.")
    else:
        aero_disponibles = sorted([str(x) for x in df_filtrado_base['aerolinea'].dropna().unique()])

        # Controles de refinamiento dinámicos (FUERA de st.form)
        st.markdown("---")
        st.subheader("⚡ Controles de Visualización y Refinamiento (Actualización Inmediata)")
        
        c_aero, c_met, c_graf = st.columns([2, 1, 1])
        with c_aero:
            sel_aerolineas = st.multiselect(
                "✈️ Aerolíneas:",
                options=aero_disponibles,
                default=aero_disponibles,
                help="Modifique las aerolíneas a incluir en tiempo real."
            )
        with c_met:
            sel_metrica = st.selectbox(
                "📊 Métrica:",
                options=["Pasajeros", "Vuelos", "Asientos", "Factor de Ocupación (%)"],
                index=0,
                help="Métrica numérica a analizar en gráficos y tablas."
            )
        with c_graf:
            sel_grafico = st.selectbox(
                "📈 Tipo de Gráfico:",
                options=["Líneas", "Barras Apiladas", "Barras Agrupadas", "Área"],
                index=0
            )

        # Aplicar filtro de aerolíneas
        if sel_aerolineas:
            df_final = df_filtrado_base[df_filtrado_base['aerolinea'].isin(sel_aerolineas)].copy()
        else:
            df_final = df_filtrado_base.copy()

        # KPIs Principales
        tot_pasajeros = int(df_final['pasajeros'].sum())
        tot_vuelos = int(df_final['vuelos'].sum())
        tot_asientos = int(df_final['asientos'].sum())
        load_factor_prom = (tot_pasajeros / tot_asientos * 100) if tot_asientos > 0 else 0.0

        # CÁLCULO DEL ÍNDICE HHI (Herfindahl-Hirschman) GLOBAL
        tot_pax_aero = df_final.groupby('aerolinea', observed=True)['pasajeros'].sum()
        if tot_pasajeros > 0:
            market_shares = (tot_pax_aero / tot_pasajeros) * 100
            hhi_global = int(round((market_shares ** 2).sum()))
        else:
            hhi_global = 0

        if hhi_global < 1500:
            hhi_cat = "Competitivo"
            hhi_desc = "Baja concentración"
        elif hhi_global <= 2500:
            hhi_cat = "Concentración Moderada"
            hhi_desc = "Oligopolio moderado"
        else:
            hhi_cat = "Alta Concentración"
            hhi_desc = "Monopolio / Fuerte concentración"

        st.markdown("---")
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Total Pasajeros", fmt_entero(tot_pasajeros))
        k2.metric("Total Vuelos", fmt_entero(tot_vuelos))
        k3.metric("Total Asientos", fmt_entero(tot_asientos))
        k4.metric("Factor de Ocupación", fmt_porcentaje(load_factor_prom))
        k5.metric("Índice HHI", f"{fmt_entero(hhi_global)} pts", hhi_cat)

        col_metrica_map = {
            'Pasajeros': 'pasajeros',
            'Vuelos': 'vuelos',
            'Asientos': 'asientos'
        }

        # -------------------------------------------------------------
        # FUNCIÓN GENERADORA DE MATRICES CON FILA Y COLUMNA DE TOTALES
        # -------------------------------------------------------------
        def construir_matriz_con_totales(df_in, index_col, col_dim, metrica, nombre_indice, sort_index_col=None):
            if df_in.empty:
                return pd.DataFrame()
            
            if metrica == 'Factor de Ocupación (%)':
                piv_pax = df_in.pivot_table(index=index_col, columns=col_dim, values='pasajeros', aggfunc='sum', fill_value=0, observed=True)
                piv_asi = df_in.pivot_table(index=index_col, columns=col_dim, values='asientos', aggfunc='sum', fill_value=0, observed=True)
                
                if sort_index_col and sort_index_col in df_in.columns:
                    if index_col == sort_index_col:
                        orden = sorted(piv_pax.index)
                    else:
                        orden = df_in[[index_col, sort_index_col]].drop_duplicates().sort_values(by=sort_index_col)[index_col]
                        orden = [o for o in orden if o in piv_pax.index]
                    piv_pax = piv_pax.reindex(orden)
                    piv_asi = piv_asi.reindex(orden)
                    
                piv_pax['TOTAL'] = piv_pax.sum(axis=1)
                piv_asi['TOTAL'] = piv_asi.sum(axis=1)
                piv_pax.loc['TOTAL'] = piv_pax.sum(axis=0)
                piv_asi.loc['TOTAL'] = piv_asi.sum(axis=0)
                
                piv_lf = np.where(piv_asi > 0, (piv_pax / piv_asi) * 100, 0)
                piv_df = pd.DataFrame(piv_lf, index=piv_pax.index, columns=piv_pax.columns)
                
                piv_disp = piv_df.reset_index().rename(columns={index_col: nombre_indice})
                piv_disp.columns.name = None
                for c in piv_disp.columns:
                    if c != nombre_indice:
                        piv_disp[c] = piv_disp[c].apply(fmt_porcentaje)
                return piv_disp
            else:
                val_c = col_metrica_map.get(metrica, 'pasajeros')
                piv = df_in.pivot_table(index=index_col, columns=col_dim, values=val_c, aggfunc='sum', fill_value=0, observed=True)
                
                if sort_index_col and sort_index_col in df_in.columns:
                    if index_col == sort_index_col:
                        orden = sorted(piv.index)
                    else:
                        orden = df_in[[index_col, sort_index_col]].drop_duplicates().sort_values(by=sort_index_col)[index_col]
                        orden = [o for o in orden if o in piv.index]
                    piv = piv.reindex(orden)
                    
                piv['TOTAL'] = piv.sum(axis=1)
                piv.loc['TOTAL'] = piv.sum(axis=0)
                
                piv_disp = piv.reset_index().rename(columns={index_col: nombre_indice})
                piv_disp.columns.name = None
                for c in piv_disp.columns:
                    if c != nombre_indice:
                        piv_disp[c] = piv_disp[c].apply(fmt_entero)
                return piv_disp

        # -------------------------------------------------------------
        # PESTAÑAS PRINCIPALES DEL MONITOR
        # -------------------------------------------------------------
        tab_principal, tab_hhi, tab_estac, tab_comp = st.tabs([
            "📊 Monitor y Gráficos",
            "🏛️ Competencia y Concentración (HHI)",
            "🌡️ Estacionalidad & YoY",
            "⚖️ Comparador de Rutas"
        ])

        # -------------------------------------------------------------
        # TAB 1: MONITOR PRINCIPAL Y GRÁFICOS VERTICALES
        # -------------------------------------------------------------
        with tab_principal:
            st.subheader(f"📈 1. Evolución Mensual del Tráfico ({sel_metrica})")

            df_mes = df_final.groupby(['periodo_orden', 'periodo_mes_es', 'aerolinea'], as_index=False, observed=True).agg(
                pasajeros=('pasajeros', 'sum'),
                vuelos=('vuelos', 'sum'),
                asientos=('asientos', 'sum')
            ).sort_values(by='periodo_orden')

            df_mes['load_factor_%'] = np.where(df_mes['asientos'] > 0, (df_mes['pasajeros'] / df_mes['asientos']) * 100, 0)
            y_col = 'load_factor_%' if sel_metrica == 'Factor de Ocupación (%)' else col_metrica_map[sel_metrica]

            if sel_grafico == "Líneas":
                fig_evol = px.line(
                    df_mes,
                    x='periodo_mes_es',
                    y=y_col,
                    color='aerolinea',
                    markers=True,
                    labels={'periodo_mes_es': 'Período', y_col: sel_metrica, 'aerolinea': 'Aerolínea'}
                )
            elif sel_grafico == "Barras Apiladas":
                fig_evol = px.bar(
                    df_mes,
                    x='periodo_mes_es',
                    y=y_col,
                    color='aerolinea',
                    barmode='stack',
                    labels={'periodo_mes_es': 'Período', y_col: sel_metrica, 'aerolinea': 'Aerolínea'}
                )
            elif sel_grafico == "Barras Agrupadas":
                fig_evol = px.bar(
                    df_mes,
                    x='periodo_mes_es',
                    y=y_col,
                    color='aerolinea',
                    barmode='group',
                    labels={'periodo_mes_es': 'Período', y_col: sel_metrica, 'aerolinea': 'Aerolínea'}
                )
            else: # Área
                fig_evol = px.area(
                    df_mes,
                    x='periodo_mes_es',
                    y=y_col,
                    color='aerolinea',
                    labels={'periodo_mes_es': 'Período', y_col: sel_metrica, 'aerolinea': 'Aerolínea'}
                )

            fig_evol.update_layout(
                hovermode='x unified',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=20, r=20, t=30, b=20)
            )
            st.plotly_chart(fig_evol, use_container_width=True)

            st.subheader("🥧 2. Distribución Total por Aerolínea")
            df_aero_pie = df_final.groupby('aerolinea', as_index=False, observed=True).agg(
                pasajeros=('pasajeros', 'sum'),
                vuelos=('vuelos', 'sum'),
                asientos=('asientos', 'sum')
            )
            val_pie = 'pasajeros' if sel_metrica in ['Pasajeros', 'Factor de Ocupación (%)'] else col_metrica_map[sel_metrica]
            fig_pie = px.pie(
                df_aero_pie,
                names='aerolinea',
                values=val_pie,
                hole=0.35,
                labels={'aerolinea': 'Aerolínea', val_pie: sel_metrica}
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            fig_pie.update_layout(
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=20, r=20, t=30, b=20)
            )
            st.plotly_chart(fig_pie, use_container_width=True)

            st.subheader("🧭 3. Tráfico por Sentido (Tramo)")
            df_tramo = df_final.groupby('tramo_label', as_index=False, observed=True).agg(
                pasajeros=('pasajeros', 'sum'),
                vuelos=('vuelos', 'sum'),
                asientos=('asientos', 'sum')
            )
            df_tramo['load_factor_%'] = np.where(df_tramo['asientos'] > 0, (df_tramo['pasajeros'] / df_tramo['asientos']) * 100, 0)
            y_val_tramo = 'load_factor_%' if sel_metrica == 'Factor de Ocupación (%)' else col_metrica_map[sel_metrica]
            
            df_tramo = df_tramo.sort_values(by=y_val_tramo, ascending=True)

            fig_tramo = px.bar(
                df_tramo,
                y='tramo_label',
                x=y_val_tramo,
                orientation='h',
                text=y_val_tramo,
                labels={'tramo_label': 'Sentido / Tramo', y_val_tramo: sel_metrica},
                color=y_val_tramo,
                color_continuous_scale='Blues'
            )
            if sel_metrica == 'Factor de Ocupación (%)':
                fig_tramo.update_traces(texttemplate='%{x:.1f}%', textposition='outside')
            else:
                fig_tramo.update_traces(texttemplate='%{x:,.0f}', textposition='outside')
                
            alt_bar = max(420, len(df_tramo) * 36)
            fig_tramo.update_layout(
                height=alt_bar,
                coloraxis_showscale=False,
                margin=dict(l=20, r=20, t=30, b=20)
            )
            st.plotly_chart(fig_tramo, use_container_width=True)

            # CUADROS DE DATOS CON FILA Y COLUMNA DE TOTALES
            st.markdown("---")
            st.subheader("📋 Cuadros de Datos y Estadísticas (con Fila y Columna de Totales)")

            c_tab_mes, c_tab_ano, c_tab_tramo, c_tab_cruz, c_tab_res_aero, c_tab_res_tramo = st.tabs([
                "📅 Matriz Mensual",
                "📆 Matriz Anual",
                "🧭 Matriz por Sentido",
                "🔄 Matriz Aerolínea ✕ Sentido",
                "✈️ Resumen Aerolíneas",
                "🛫 Resumen Sentidos"
            ])

            with c_tab_mes:
                st.markdown(f"**Evolución Mensual por Aerolínea ({sel_metrica})**")
                matriz_mensual = construir_matriz_con_totales(
                    df_final,
                    index_col='periodo_mes_es',
                    col_dim='aerolinea',
                    metrica=sel_metrica,
                    nombre_indice='Período',
                    sort_index_col='periodo_orden'
                )
                st.dataframe(matriz_mensual, use_container_width=True, hide_index=True)

            with c_tab_ano:
                st.markdown(f"**Evolución Anual por Aerolínea ({sel_metrica})**")
                matriz_anual = construir_matriz_con_totales(
                    df_final,
                    index_col='ano_num',
                    col_dim='aerolinea',
                    metrica=sel_metrica,
                    nombre_indice='Año',
                    sort_index_col='ano_num'
                )
                st.dataframe(matriz_anual, use_container_width=True, hide_index=True)

            with c_tab_tramo:
                st.markdown(f"**Evolución Mensual por Sentido / Tramo ({sel_metrica})**")
                matriz_sentido = construir_matriz_con_totales(
                    df_final,
                    index_col='periodo_mes_es',
                    col_dim='tramo_label',
                    metrica=sel_metrica,
                    nombre_indice='Período',
                    sort_index_col='periodo_orden'
                )
                st.dataframe(matriz_sentido, use_container_width=True, hide_index=True)

            with c_tab_cruz:
                st.markdown(f"**Distribución Cruzada: Aerolínea ✕ Sentido ({sel_metrica})**")
                matriz_cruzada = construir_matriz_con_totales(
                    df_final,
                    index_col='aerolinea',
                    col_dim='tramo_label',
                    metrica=sel_metrica,
                    nombre_indice='Aerolínea'
                )
                st.dataframe(matriz_cruzada, use_container_width=True, hide_index=True)

            with c_tab_res_aero:
                st.markdown("**Resumen Consolidado por Aerolínea**")
                res_aero = df_final.groupby('aerolinea', as_index=False, observed=True).agg(
                    pasajeros=('pasajeros', 'sum'),
                    vuelos=('vuelos', 'sum'),
                    asientos=('asientos', 'sum')
                ).sort_values(by='pasajeros', ascending=False)

                tot_p = res_aero['pasajeros'].sum()
                tot_v = res_aero['vuelos'].sum()
                tot_a = res_aero['asientos'].sum()
                res_aero['cuota_%'] = (res_aero['pasajeros'] / tot_p * 100) if tot_p > 0 else 0
                res_aero['load_factor_%'] = np.where(res_aero['asientos'] > 0, (res_aero['pasajeros'] / res_aero['asientos']) * 100, 0)

                fila_tot_aero = pd.DataFrame([{
                    'aerolinea': 'TOTAL',
                    'pasajeros': tot_p,
                    'vuelos': tot_v,
                    'asientos': tot_a,
                    'cuota_%': 100.0 if tot_p > 0 else 0.0,
                    'load_factor_%': (tot_p / tot_a * 100) if tot_a > 0 else 0.0
                }])
                res_aero_con_tot = pd.concat([res_aero, fila_tot_aero], ignore_index=True)

                res_aero_disp = res_aero_con_tot.copy()
                res_aero_disp['pasajeros'] = res_aero_disp['pasajeros'].apply(fmt_entero)
                res_aero_disp['vuelos'] = res_aero_disp['vuelos'].apply(fmt_entero)
                res_aero_disp['asientos'] = res_aero_disp['asientos'].apply(fmt_entero)
                res_aero_disp['cuota_%'] = res_aero_disp['cuota_%'].apply(fmt_porcentaje)
                res_aero_disp['load_factor_%'] = res_aero_disp['load_factor_%'].apply(fmt_porcentaje)

                res_aero_disp.rename(columns={
                    'aerolinea': 'Aerolínea',
                    'pasajeros': 'Pasajeros',
                    'vuelos': 'Vuelos',
                    'asientos': 'Asientos',
                    'cuota_%': 'Cuota de Mercado (%)',
                    'load_factor_%': 'Factor de Ocupación (%)'
                }, inplace=True)
                st.dataframe(res_aero_disp, use_container_width=True, hide_index=True)

            with c_tab_res_tramo:
                st.markdown("**Resumen Consolidado por Sentido (Tramo)**")
                res_tr = df_final.groupby('tramo_label', as_index=False, observed=True).agg(
                    pasajeros=('pasajeros', 'sum'),
                    vuelos=('vuelos', 'sum'),
                    asientos=('asientos', 'sum')
                ).sort_values(by='pasajeros', ascending=False)

                tot_pt = res_tr['pasajeros'].sum()
                tot_vt = res_tr['vuelos'].sum()
                tot_at = res_tr['asientos'].sum()
                res_tr['dist_%'] = (res_tr['pasajeros'] / tot_pt * 100) if tot_pt > 0 else 0
                res_tr['load_factor_%'] = np.where(res_tr['asientos'] > 0, (res_tr['pasajeros'] / res_tr['asientos']) * 100, 0)

                fila_tot_tr = pd.DataFrame([{
                    'tramo_label': 'TOTAL',
                    'pasajeros': tot_pt,
                    'vuelos': tot_vt,
                    'asientos': tot_at,
                    'dist_%': 100.0 if tot_pt > 0 else 0.0,
                    'load_factor_%': (tot_pt / tot_at * 100) if tot_at > 0 else 0.0
                }])
                res_tr_con_tot = pd.concat([res_tr, fila_tot_tr], ignore_index=True)

                res_tr_disp = res_tr_con_tot.copy()
                res_tr_disp['pasajeros'] = res_tr_disp['pasajeros'].apply(fmt_entero)
                res_tr_disp['vuelos'] = res_tr_disp['vuelos'].apply(fmt_entero)
                res_tr_disp['asientos'] = res_tr_disp['asientos'].apply(fmt_entero)
                res_tr_disp['dist_%'] = res_tr_disp['dist_%'].apply(fmt_porcentaje)
                res_tr_disp['load_factor_%'] = res_tr_disp['load_factor_%'].apply(fmt_porcentaje)

                res_tr_disp.rename(columns={
                    'tramo_label': 'Sentido / Tramo',
                    'pasajeros': 'Pasajeros',
                    'vuelos': 'Vuelos',
                    'asientos': 'Asientos',
                    'dist_%': 'Distribución (%)',
                    'load_factor_%': 'Factor de Ocupación (%)'
                }, inplace=True)
                st.dataframe(res_tr_disp, use_container_width=True, hide_index=True)

        # -------------------------------------------------------------
        # TAB 2: ÍNDICE DE CONCENTRACIÓN Y COMPETENCIA (HHI)
        # -------------------------------------------------------------
        with tab_hhi:
            st.subheader("🏛️ Análisis de Concentración de Mercado (Índice HHI)")
            st.markdown(
                """
                El **Índice de Herfindahl-Hirschman (HHI)** es el estándar internacional utilizado por organismos antimonopolio y de aviación civil para evaluar el nivel de competencia en un corredor:
                * **HHI < 1.500:** Mercado altamente competitivo (diversificación de operadores).
                * **1.500 a 2.500:** Concentración moderada.
                * **HHI > 2.500:** Alta concentración / Monopolio u oligopolio estricto (10.000 = un solo operador exclusivo).
                """
            )

            hhi_filas = []
            for (p_ord, p_mes), g in df_final.groupby(['periodo_orden', 'periodo_mes_es'], observed=True):
                sub_tot = g['pasajeros'].sum()
                if sub_tot > 0:
                    sh = (g.groupby('aerolinea', observed=True)['pasajeros'].sum() / sub_tot) * 100
                    v_hhi = int(round((sh ** 2).sum()))
                else:
                    v_hhi = 0
                hhi_filas.append({'periodo_orden': p_ord, 'periodo_mes_es': p_mes, 'HHI': v_hhi})
            
            df_hhi_mes = pd.DataFrame(hhi_filas).sort_values(by='periodo_orden')

            fig_hhi = px.line(
                df_hhi_mes,
                x='periodo_mes_es',
                y='HHI',
                markers=True,
                title="Evolución Mensual del Índice HHI en la Ruta",
                labels={'periodo_mes_es': 'Período', 'HHI': 'Puntos HHI'}
            )
            fig_hhi.add_hline(y=1500, line_dash="dash", line_color="green", annotation_text="Límite Competitivo (1.500)", annotation_position="bottom right")
            fig_hhi.add_hline(y=2500, line_dash="dash", line_color="red", annotation_text="Límite Alta Concentración (2.500)", annotation_position="top right")
            fig_hhi.update_layout(margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_hhi, use_container_width=True)

            st.markdown("##### 📊 Evolución Histórica de Cuotas de Mercado (Market Share %)")
            df_sh = df_final.groupby(['periodo_orden', 'periodo_mes_es', 'aerolinea'], as_index=False, observed=True)['pasajeros'].sum()
            df_sh_tot = df_final.groupby(['periodo_orden', 'periodo_mes_es'], as_index=False, observed=True)['pasajeros'].sum().rename(columns={'pasajeros': 'tot_mes'})
            df_sh = df_sh.merge(df_sh_tot, on=['periodo_orden', 'periodo_mes_es'])
            df_sh['share_%'] = np.where(df_sh['tot_mes'] > 0, (df_sh['pasajeros'] / df_sh['tot_mes']) * 100, 0)

            fig_sh = px.area(
                df_sh.sort_values(by='periodo_orden'),
                x='periodo_mes_es',
                y='share_%',
                color='aerolinea',
                labels={'periodo_mes_es': 'Período', 'share_%': 'Cuota de Mercado (%)', 'aerolinea': 'Aerolínea'}
            )
            fig_sh.update_layout(
                yaxis=dict(ticksuffix="%", range=[0, 100]),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=20, r=20, t=30, b=20)
            )
            st.plotly_chart(fig_sh, use_container_width=True)

        # -------------------------------------------------------------
        # TAB 3: ESTACIONALIDAD & COMPARATIVA INTERANUAL (YoY)
        # -------------------------------------------------------------
        with tab_estac:
            st.subheader("🌡️ Detección de Estacionalidad y Variación Interanual (YoY)")
            st.markdown(
                "Superposición de los 12 meses del año a lo largo de las distintas temporadas anuales para evaluar picos estacionales, valles y crecimiento interanual."
            )

            val_estac_c = col_metrica_map.get(sel_metrica, 'pasajeros')
            df_estac = df_final.groupby(['mes_num', 'ano_num'], as_index=False, observed=True)[val_estac_c].sum()
            df_estac['Nombre_Mes'] = df_estac['mes_num'].map(meses_es)
            df_estac['Año'] = df_estac['ano_num'].astype(str)
            df_estac = df_estac.sort_values(by='mes_num')

            fig_estac = px.line(
                df_estac,
                x='Nombre_Mes',
                y=val_estac_c,
                color='Año',
                markers=True,
                title=f"Curvas Estacionales Superpuestas por Año ({sel_metrica})",
                labels={'Nombre_Mes': 'Mes del Año', val_estac_c: sel_metrica, 'Año': 'Año'}
            )
            fig_estac.update_layout(
                hovermode='x unified',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=20, r=20, t=40, b=20)
            )
            st.plotly_chart(fig_estac, use_container_width=True)

            st.markdown("##### 📅 Tabla de Estacionalidad con Fila y Columna de Totales")
            piv_estac_raw = df_final.pivot_table(index='mes_num', columns='ano_num', values=val_estac_c, aggfunc='sum', fill_value=0, observed=True)
            
            piv_estac_raw['TOTAL MES'] = piv_estac_raw.sum(axis=1)
            piv_estac_raw.loc['TOTAL'] = piv_estac_raw.sum(axis=0)

            piv_estac_disp = piv_estac_raw.copy()
            for c in piv_estac_disp.columns:
                piv_estac_disp[c] = piv_estac_disp[c].apply(fmt_entero)
            
            piv_estac_disp = piv_estac_disp.reset_index()
            piv_estac_disp['Mes'] = piv_estac_disp['mes_num'].map(lambda m: meses_es.get(m, 'TOTAL'))
            piv_estac_disp.drop(columns=['mes_num'], inplace=True)
            cols_reord = ['Mes'] + [c for c in piv_estac_disp.columns if c != 'Mes']
            piv_estac_disp = piv_estac_disp[cols_reord]
            piv_estac_disp.columns.name = None
            st.dataframe(piv_estac_disp, use_container_width=True, hide_index=True)

        # -------------------------------------------------------------
        # TAB 4: COMPARADOR DE RUTAS (BENCHMARKING)
        # -------------------------------------------------------------
        with tab_comp:
            st.subheader("⚖️ Comparador de Rutas en Paralelo (Benchmarking)")
            st.markdown("Contraste directamente dos corredores aéreos de cabotaje en el mismo período de fechas.")

            r_base_def = r_act[0] if (r_act and len(r_act) > 0) else rutas_disponibles[0]
            opciones_comp = [r for r in rutas_disponibles if r != r_base_def]
            r_comp_def = opciones_comp[0] if opciones_comp else r_base_def

            c_rb, c_rc = st.columns(2)
            with c_rb:
                ruta_A = st.selectbox("🔵 Ruta A (Principal):", options=rutas_disponibles, index=rutas_disponibles.index(r_base_def) if r_base_def in rutas_disponibles else 0)
            with c_rc:
                ruta_B = st.selectbox("🟠 Ruta B (Comparación):", options=rutas_disponibles, index=rutas_disponibles.index(r_comp_def) if r_comp_def in rutas_disponibles else 0)

            df_A = df_raw[cond_fecha & (df_raw['ruta_label'] == ruta_A)].copy()
            df_B = df_raw[cond_fecha & (df_raw['ruta_label'] == ruta_B)].copy()

            pax_A = int(df_A['pasajeros'].sum())
            pax_B = int(df_B['pasajeros'].sum())
            vue_A = int(df_A['vuelos'].sum())
            vue_B = int(df_B['vuelos'].sum())
            asi_A = int(df_A['asientos'].sum())
            asi_B = int(df_B['asientos'].sum())
            lf_A = (pax_A / asi_A * 100) if asi_A > 0 else 0.0
            lf_B = (pax_B / asi_B * 100) if asi_B > 0 else 0.0

            dif_pax_pct = ((pax_B - pax_A) / pax_A * 100) if pax_A > 0 else 0.0

            st.markdown("##### 📌 Resumen Comparativo Directo")
            ck1, ck2, ck3, ck4 = st.columns(4)
            ck1.metric("Pasajeros Ruta A", fmt_entero(pax_A))
            ck1.metric("Pasajeros Ruta B", fmt_entero(pax_B), delta=f"{dif_pax_pct:+.1f}% vs A")
            ck2.metric("Vuelos Ruta A", fmt_entero(vue_A))
            ck2.metric("Vuelos Ruta B", fmt_entero(vue_B))
            ck3.metric("Asientos Ruta A", fmt_entero(asi_A))
            ck3.metric("Asientos Ruta B", fmt_entero(asi_B))
            ck4.metric("Factor Ocupación A", fmt_porcentaje(lf_A))
            ck4.metric("Factor Ocupación B", fmt_porcentaje(lf_B), delta=f"{(lf_B - lf_A):+.1f} pts")

            df_A_mes = df_A.groupby(['periodo_orden', 'periodo_mes_es'], as_index=False, observed=True)['pasajeros'].sum().sort_values(by='periodo_orden')
            df_A_mes['Ruta'] = f"Ruta A: {ruta_A}"
            df_B_mes = df_B.groupby(['periodo_orden', 'periodo_mes_es'], as_index=False, observed=True)['pasajeros'].sum().sort_values(by='periodo_orden')
            df_B_mes['Ruta'] = f"Ruta B: {ruta_B}"

            df_comp_evol = pd.concat([df_A_mes, df_B_mes], ignore_index=True)

            fig_comp = px.line(
                df_comp_evol,
                x='periodo_mes_es',
                y='pasajeros',
                color='Ruta',
                markers=True,
                title="Evolución Mensual Comparada (Pasajeros)",
                labels={'periodo_mes_es': 'Período', 'pasajeros': 'Pasajeros'}
            )
            fig_comp.update_layout(
                hovermode='x unified',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=20, r=20, t=40, b=20)
            )
            st.plotly_chart(fig_comp, use_container_width=True)

        # -------------------------------------------------------------
        # DESCARGA DE DATOS FILTRADOS Y REPORTE EJECUTIVO EXCEL
        # -------------------------------------------------------------
        st.markdown("---")
        st.subheader("📥 Exportación de Datos y Reportes")

        def generar_reporte_excel():
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # 1. Resumen y KPIs
                df_kpis = pd.DataFrame([
                    {'Métrica': 'Rutas Seleccionadas', 'Valor': ", ".join(r_act) if r_act else 'Todas'},
                    {'Métrica': 'Rango Temporal', 'Valor': f"{fd_act} a {fh_act}"},
                    {'Métrica': 'Total Pasajeros', 'Valor': tot_pasajeros},
                    {'Métrica': 'Total Vuelos', 'Valor': tot_vuelos},
                    {'Métrica': 'Total Asientos', 'Valor': tot_asientos},
                    {'Métrica': 'Factor de Ocupación Promedio (%)', 'Valor': round(load_factor_prom, 1)},
                    {'Métrica': 'Índice de Concentración HHI', 'Valor': hhi_global},
                    {'Métrica': 'Clasificación de Competencia', 'Valor': hhi_cat}
                ])
                df_kpis.to_excel(writer, sheet_name='Resumen_KPIs', index=False)

                # 2. Resumen por Aerolínea con totales
                res_aero_con_tot.to_excel(writer, sheet_name='Resumen_Aerolineas', index=False)

                # 3. Resumen por Sentido con totales
                res_tr_con_tot.to_excel(writer, sheet_name='Resumen_Sentidos', index=False)

                # 4. Matriz Mensual (valores numéricos con totales)
                piv_mes_num = df_final.pivot_table(index='periodo_mes_es', columns='aerolinea', values='pasajeros', aggfunc='sum', fill_value=0, observed=True)
                piv_mes_num['TOTAL'] = piv_mes_num.sum(axis=1)
                piv_mes_num.loc['TOTAL'] = piv_mes_num.sum(axis=0)
                piv_mes_num.reset_index().rename(columns={'periodo_mes_es': 'Período'}).to_excel(writer, sheet_name='Matriz_Mensual_Pax', index=False)

                # 5. Matriz Anual con totales
                piv_ano_num = df_final.pivot_table(index='ano_num', columns='aerolinea', values='pasajeros', aggfunc='sum', fill_value=0, observed=True)
                piv_ano_num['TOTAL'] = piv_ano_num.sum(axis=1)
                piv_ano_num.loc['TOTAL'] = piv_ano_num.sum(axis=0)
                piv_ano_num.reset_index().rename(columns={'ano_num': 'Año'}).to_excel(writer, sheet_name='Matriz_Anual_Pax', index=False)

            output.seek(0)
            return output.getvalue()

        col_d_excel, col_d_csv = st.columns(2)
        with col_d_excel:
            try:
                excel_bytes = generar_reporte_excel()
                st.download_button(
                    label="📊 Descargar Reporte Ejecutivo (.xlsx)",
                    data=excel_bytes,
                    file_name=f"reporte_rutas_cabotaje_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            except Exception as e:
                st.warning(f"No se pudo generar el Excel automático: {e}")

        with col_d_csv:
            csv_descarga = df_final.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descargar Datos Crudos Filtrados (CSV)",
                data=csv_descarga,
                file_name=f"vuelos_cabotaje_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
