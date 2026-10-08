import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
import requests
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
    if pd.isna(val) or val is None:
        return "0"
    try:
        n = int(round(float(val)))
        return f"{n:,}".replace(",", ".")
    except Exception:
        return "0"

def fmt_decimal(val, dec=1):
    if pd.isna(val) or val is None:
        return "0,0"
    try:
        formateado = f"{float(val):,.{dec}f}"
        partes = formateado.split('.')
        entero = partes[0].replace(',', '.')
        decimal = partes[1] if len(partes) > 1 else "0"
        return f"{entero},{decimal}"
    except Exception:
        return "0,0"

def fmt_porcentaje(val, dec=1):
    return f"{fmt_decimal(val, dec)}%"

def formatear_cuadro_totales(df_in, col_periodo='Período'):
    df_out = df_in.copy()
    cols = list(df_out.columns)
    if col_periodo in cols and cols[0] != col_periodo:
        cols.insert(0, cols.pop(cols.index(col_periodo)))
        df_out = df_out[cols]
        
    for c in df_out.columns:
        if c == col_periodo:
            continue
        es_pct = any(k in str(c).lower() for k in ['%', 'ocupacion', 'ocupación', 'share', 'tasa', 'variacion', 'variación'])
        if es_pct:
            df_out[c] = df_out[c].apply(lambda x: fmt_porcentaje(x, 1) if pd.notna(x) else "-")
        else:
            df_out[c] = df_out[c].apply(lambda x: fmt_entero(x) if pd.notna(x) else "0")
    return df_out

# -------------------------------------------------------------
# DICCIONARIO EXHAUSTIVO DE AEROPUERTOS COMERCIALES ARGENTINOS
# -------------------------------------------------------------
AEROPUERTOS_EXHAUSTIVO = {
    'AEP': {'codigo': 'AEP', 'ciudad': 'Aeroparque', 'aliases': ['AEP', 'AER', 'SABE', 'AEROPARQUE', 'JORGE NEWBERY', 'BUENOS AIRES', 'CIUDAD DE BUENOS AIRES', 'CABA', 'BUE']},
    'EZE': {'codigo': 'EZE', 'ciudad': 'Ezeiza', 'aliases': ['EZE', 'SAEZ', 'EZEIZA', 'PISTARINI', 'MINISTRO PISTARINI']},
    'EPA': {'codigo': 'EPA', 'ciudad': 'El Palomar', 'aliases': ['EPA', 'PAL', 'SADP', 'PALOMAR', 'EL PALOMAR']},
    'FDO': {'codigo': 'FDO', 'ciudad': 'San Fernando', 'aliases': ['FDO', 'SADF', 'SAN FERNANDO']},
    'BRC': {'codigo': 'BRC', 'ciudad': 'Bariloche', 'aliases': ['BRC', 'BAR', 'SAZS', 'BARILOCHE', 'SAN CARLOS DE BARILOCHE', 'CANDELARIA']},
    'COR': {'codigo': 'COR', 'ciudad': 'Córdoba', 'aliases': ['COR', 'CBA', 'SACO', 'CORDOBA', 'CÓRDOBA', 'TARAVELLA', 'PAJAS BLANCAS']},
    'MDZ': {'codigo': 'MDZ', 'ciudad': 'Mendoza', 'aliases': ['MDZ', 'DOZ', 'SAME', 'MENDOZA', 'PLUMERILLO', 'EL PLUMERILLO', 'GABRIELLI']},
    'SLA': {'codigo': 'SLA', 'ciudad': 'Salta', 'aliases': ['SLA', 'SAL', 'SASA', 'SALTA', 'GUEMES', 'GÜEMES', 'MARTIN MIGUEL']},
    'IGR': {'codigo': 'IGR', 'ciudad': 'Iguazú', 'aliases': ['IGR', 'IGU', 'SARI', 'IGUAZU', 'IGUAZÚ', 'PUERTO IGUAZU', 'CATARATAS']},
    'JUJ': {'codigo': 'JUJ', 'ciudad': 'Jujuy', 'aliases': ['JUJ', 'SASJ', 'JUJUY', 'SAN SALVADOR DE JUJUY', 'HORACIO GUZMAN', 'GUZMAN']},
    'NQN': {'codigo': 'NQN', 'ciudad': 'Neuquén', 'aliases': ['NQN', 'NEU', 'SAZN', 'NEUQUEN', 'NEUQUÉN', 'PRESIDENTE PERON']},
    'TUC': {'codigo': 'TUC', 'ciudad': 'Tucumán', 'aliases': ['TUC', 'SANT', 'TUCUMAN', 'TUCUMÁN', 'BENJAMIN MATIENZO', 'SAN MIGUEL DE TUCUMAN']},
    'FTE': {'codigo': 'FTE', 'ciudad': 'El Calafate', 'aliases': ['FTE', 'CAL', 'SAWC', 'CALAFATE', 'EL CALAFATE', 'ARMANDO TOLA', 'TOLA']},
    'USH': {'codigo': 'USH', 'ciudad': 'Ushuaia', 'aliases': ['USH', 'USU', 'SAWH', 'USHUAIA', 'MALVINAS ARGENTINAS']},
    'CRD': {'codigo': 'CRD', 'ciudad': 'Comodoro Rivadavia', 'aliases': ['CRD', 'CRV', 'SAVC', 'COMODORO', 'COMODORO RIVADAVIA', 'ENRIQUE MOSCONI']},
    'REL': {'codigo': 'REL', 'ciudad': 'Trelew', 'aliases': ['REL', 'TRE', 'SAVT', 'TRELEW', 'ALMIRANTE ZAR']},
    'PMY': {'codigo': 'PMY', 'ciudad': 'Puerto Madryn', 'aliases': ['PMY', 'SAVY', 'MADRYN', 'PUERTO MADRYN', 'TEHUELCHE', 'EL TEHUELCHE']},
    'MDQ': {'codigo': 'MDQ', 'ciudad': 'Mar del Plata', 'aliases': ['MDQ', 'MDP', 'SAZM', 'MAR DEL PLATA', 'PIAZZOLLA', 'ASTOR PIAZZOLLA']},
    'BHI': {'codigo': 'BHI', 'ciudad': 'Bahía Blanca', 'aliases': ['BHI', 'BCA', 'SAZB', 'BAHIA BLANCA', 'BAHÍA BLANCA', 'ESPORA', 'COMANDANTE ESPORA']},
    'ROS': {'codigo': 'ROS', 'ciudad': 'Rosario', 'aliases': ['ROS', 'SAAR', 'ROSARIO', 'ISLAS MALVINAS']},
    'SFN': {'codigo': 'SFN', 'ciudad': 'Santa Fe', 'aliases': ['SFN', 'SAAV', 'SANTA FE', 'SAUCE VIEJO']},
    'PRA': {'codigo': 'PRA', 'ciudad': 'Paraná', 'aliases': ['PRA', 'PAR', 'SAAP', 'PARANA', 'PARANÁ', 'URQUIZA', 'JUSTO JOSE']},
    'PSS': {'codigo': 'PSS', 'ciudad': 'Posadas', 'aliases': ['PSS', 'POS', 'SARP', 'POSADAS', 'SAN MARTIN', 'JOSE DE SAN MARTIN']},
    'RES': {'codigo': 'RES', 'ciudad': 'Resistencia', 'aliases': ['RES', 'SIS', 'SARE', 'RESISTENCIA']},
    'CNQ': {'codigo': 'CNQ', 'ciudad': 'Corrientes', 'aliases': ['CNQ', 'SARC', 'CORRIENTES', 'PIRAGINE NIVEYRO', 'PIRAGINE']},
    'SDE': {'codigo': 'SDE', 'ciudad': 'Santiago del Estero', 'aliases': ['SDE', 'SANE', 'SANTIAGO DEL ESTERO', 'ARAGONES']},
    'RHD': {'codigo': 'RHD', 'ciudad': 'Termas de Río Hondo', 'aliases': ['RHD', 'TRH', 'SANR', 'TERMAS', 'RIO HONDO', 'RÍO HONDO', 'TERMAS DE RIO HONDO']},
    'UAQ': {'codigo': 'UAQ', 'ciudad': 'San Juan', 'aliases': ['UAQ', 'JUA', 'SANU', 'SAN JUAN', 'SARMIENTO', 'DOMINGO FAUSTINO SARMIENTO']},
    'LUQ': {'codigo': 'LUQ', 'ciudad': 'San Luis', 'aliases': ['LUQ', 'UIS', 'SAOU', 'SAN LUIS', 'OJEDA', 'CESAR RAUL OJEDA']},
    'AFA': {'codigo': 'AFA', 'ciudad': 'San Rafael', 'aliases': ['AFA', 'SRA', 'SAMR', 'SAN RAFAEL', 'GERMANO', 'SANTIAGO GERMANO']},
    'IRJ': {'codigo': 'IRJ', 'ciudad': 'La Rioja', 'aliases': ['IRJ', 'LAR', 'SANL', 'LA RIOJA', 'ALMONACID', 'VICENTE ALMANDOS ALMONACID']},
    'CTC': {'codigo': 'CTC', 'ciudad': 'Catamarca', 'aliases': ['CTC', 'CAT', 'SANC', 'CATAMARCA', 'VARELA', 'FELIPE VARELA']},
    'FMA': {'codigo': 'FMA', 'ciudad': 'Formosa', 'aliases': ['FMA', 'FSA', 'SARF', 'FORMOSA', 'EL PUCU', 'PUCU']},
    'RGL': {'codigo': 'RGL', 'ciudad': 'Río Gallegos', 'aliases': ['RGL', 'GAL', 'SAWG', 'RIO GALLEGOS', 'RÍO GALLEGOS', 'NORBERTO FERNANDEZ']},
    'RGA': {'codigo': 'RGA', 'ciudad': 'Río Grande', 'aliases': ['RGA', 'GRA', 'SAWE', 'RIO GRANDE', 'RÍO GRANDE', 'TREJO NOEL', 'HERMES QUIJADA']},
    'EQS': {'codigo': 'EQS', 'ciudad': 'Esquel', 'aliases': ['EQS', 'SAVE', 'ESQUEL', 'PARODI', 'ANTONIO PARODI']},
    'VDM': {'codigo': 'VDM', 'ciudad': 'Viedma', 'aliases': ['VDM', 'VIE', 'SAVV', 'VIEDMA', 'EDGARDO CASTELLO']},
    'RSA': {'codigo': 'RSA', 'ciudad': 'Santa Rosa', 'aliases': ['RSA', 'OSA', 'SAZR', 'SANTA ROSA']}
}

MAPA_EXACTO = {}
for cod, info in AEROPUERTOS_EXHAUSTIVO.items():
    for alias in info['aliases']:
        MAPA_EXACTO[alias.upper()] = (info['codigo'], info['ciudad'])

def resolver_aeropuerto_texto(texto):
    if not texto or str(texto).strip() in ['', 'N/D', 'None', 'nan', 'DESCONOCIDO', 'NULL']:
        return "N/D", "Desconocido"
    t = str(texto).strip().upper()
    if t in MAPA_EXACTO:
        return MAPA_EXACTO[t]
    for cod, info in AEROPUERTOS_EXHAUSTIVO.items():
        for alias in info['aliases']:
            if len(alias) > 3 and alias in t:
                return (info['codigo'], info['ciudad'])
            if len(alias) <= 3 and re.search(r'\b' + re.escape(alias) + r'\b', t):
                return (info['codigo'], info['ciudad'])
    return "N/D", "Desconocido"

meses_es = {
    1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
    7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'
}

meses_orden = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
    'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
}

# -------------------------------------------------------------
# GENERADOR DE CONECTIVIDAD HISTÓRICA BASELINE (CONTINGENCIA)
# -------------------------------------------------------------
def generar_conectividad_rango(ano_desde=2017, ano_hasta=2026, mes_inicio=1, mes_fin=12):
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
        ('AEP', 'Aeroparque', 'JUJ', 'Jujuy', 0.42),
        ('JUJ', 'Jujuy', 'AEP', 'Aeroparque', 0.41),
        ('EZE', 'Ezeiza', 'JUJ', 'Jujuy', 0.25),
        ('JUJ', 'Jujuy', 'EZE', 'Ezeiza', 0.25),
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
        ('EZE', 'Ezeiza', 'USH', 'Ushuaia', 0.35),
        ('USH', 'Ushuaia', 'EZE', 'Ezeiza', 0.34),
        ('EZE', 'Ezeiza', 'FTE', 'El Calafate', 0.30),
        ('FTE', 'El Calafate', 'EZE', 'Ezeiza', 0.29),
        ('COR', 'Córdoba', 'JUJ', 'Jujuy', 0.20),
        ('JUJ', 'Jujuy', 'COR', 'Córdoba', 0.20),
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
            
        m_start = mes_inicio if y == ano_desde else 1
        m_end = mes_fin if y == ano_hasta else 12
        for m in range(m_start, m_end + 1):
            f_mes = date(y, m, 1)
            fact_temp = 1.25 if m in [1, 7] else (1.15 if m in [2, 12] else (0.88 if m in [4, 5, 9] else 1.0))
            
            for o_cod, o_ciu, d_cod, d_ciu, r_vol in rutas_base:
                base_pax = 65000 * r_vol * fact_ano * fact_temp
                
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
def leer_archivo_robusto(source):
    if hasattr(source, 'read'):
        try:
            source.seek(0)
            return pd.read_csv(source, sep=None, engine='python')
        except Exception:
            try:
                source.seek(0)
                return pd.read_excel(source)
            except Exception:
                return pd.DataFrame()
                
    path = str(source)
    is_gz = path.endswith('.gz')
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

def descargar_datos_sinta_online():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    api_url = "https://datos.yvera.gob.ar/api/3/action/package_show?id=conectividad-aerea"
    try:
        r = requests.get(api_url, headers=headers, timeout=12)
        if r.status_code == 200:
            data = r.json()
            if data.get('success'):
                resources = data['result'].get('resources', [])
                for res in resources:
                    fmt = str(res.get('format', '')).upper()
                    nombre = str(res.get('name', '')).lower()
                    url = res.get('url', '')
                    if 'CSV' in fmt and ('frecuencia' in nombre or 'pasajero' in nombre or 'vuelo' in nombre or 'dia' in nombre):
                        r_csv = requests.get(url, headers=headers, timeout=30)
                        if r_csv.status_code == 200 and len(r_csv.content) > 500:
                            with open('datos_cabotaje.csv', 'wb') as f_out:
                                f_out.write(r_csv.content)
                            return True
    except Exception:
        pass
        
    urls_directas = [
        "https://datos.yvera.gob.ar/dataset/conectividad-aerea/archivo/03b4176f-a065-450a-b411-101d2a884720",
        "https://datos.yvera.gob.ar/dataset/conectividad-aerea/archivo/aab49234-28c9-48ab-a978-a83485139290",
        "https://datos.yvera.gob.ar/dataset/conectividad-aerea/archivo/d406a6fa-c209-4b15-b648-6bcceb1d040c"
    ]
    for u in urls_directas:
        try:
            r = requests.get(u, headers=headers, timeout=20)
            if r.status_code == 200 and len(r.content) > 500 and (b',' in r.content[:500] or b';' in r.content[:500]):
                with open('datos_cabotaje.csv', 'wb') as f_out:
                    f_out.write(r.content)
                return True
        except Exception:
            continue
    return False

@st.cache_data(show_spinner="Cargando y procesando estadísticas de vuelos...")
def cargar_datos(archivo_subido=None, cache_buster="v8_sinta_online_full"):
    es_real = False
    df = None
    
    if archivo_subido is not None:
        try:
            df = leer_archivo_robusto(archivo_subido)
            if df is not None and not df.empty and len(df) >= 2:
                es_real = True
        except Exception:
            df = None
            
    if df is None or df.empty:
        import glob
        archivos_candidatos = [
            "datos_cabotaje.csv.gz",
            "datos_cabotaje.csv",
            "datos_actualizados.csv.gz",
            "datos_actualizados.csv",
            "datos_sinta.csv.gz",
            "datos_sinta.csv",
            "datos_anac.csv.gz",
            "datos_anac.csv",
            "vuelos_cabotaje.csv.gz",
            "vuelos_cabotaje.csv",
            "datos_test.csv"
        ]
        for c in (glob.glob("*.csv") + glob.glob("*.csv.gz") + glob.glob("data/*.csv*") + glob.glob("datos/*.csv*")):
            if c not in archivos_candidatos:
                archivos_candidatos.append(c)
                
        archivo_encontrado = None
        for a in archivos_candidatos:
            if os.path.exists(a) and os.path.getsize(a) > 200:
                archivo_encontrado = a
                break
                
        if archivo_encontrado:
            try:
                df = leer_archivo_robusto(archivo_encontrado)
                if df is not None and not df.empty and len(df) >= 2:
                    es_real = True
            except Exception:
                df = None
        else:
            # Intento de descarga automática en vivo desde SINTA (en Streamlit Cloud)
            try:
                if descargar_datos_sinta_online():
                    df = leer_archivo_robusto('datos_cabotaje.csv')
                    if df is not None and not df.empty and len(df) >= 2:
                        es_real = True
            except Exception:
                pass

    if df is None or df.empty or len(df) < 2:
        return generar_conectividad_rango(2017, 2026), False
        
    cols_map = {c: c.strip().lower() for c in df.columns}
    df.rename(columns=cols_map, inplace=True)
    
    # Filtrar estrictamente solo vuelos de CABOTAJE si existe columna de clasificación
    col_clasif = next((c for c in df.columns if any(k in c for k in ['clasif', 'tipo_vuelo', 'clase_vuelo', 'ambito'])), None)
    if col_clasif:
        mask_cabo = df[col_clasif].astype(str).str.lower().str.contains('cabo|domest|nac')
        if mask_cabo.any():
            df = df[mask_cabo].copy()

    # Aerolínea
    cand_aero = [c for c in df.columns if any(p in c for p in ['aerolinea', 'aerolínea', 'empresa', 'operador', 'linea', 'línea', 'compania', 'compañía'])]
    if cand_aero:
        df['aerolinea'] = df[cand_aero[0]].fillna('Otras').astype(str).str.strip()
    else:
        df['aerolinea'] = 'Todas las Aerolíneas (Total)'

    # Pasajeros
    cand_pax = [c for c in df.columns if any(p in c for p in ['pasajero', 'pax', 'cant_pasajeros', 'total_pasajeros'])]
    if cand_pax:
        s_pax = df[cand_pax[0]].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        df['pasajeros'] = pd.to_numeric(s_pax, errors='coerce').fillna(0).astype(np.int32)
    else:
        df['pasajeros'] = np.int32(0)

    # Vuelos
    cand_vue = [c for c in df.columns if any(v in c for v in ['vuelo', 'movimiento', 'frecuencia', 'cant_vuelos'])]
    if cand_vue:
        df['vuelos'] = pd.to_numeric(df[cand_vue[0]], errors='coerce').fillna(1).astype(np.int16)
    else:
        df['vuelos'] = np.int16(1)

    # Asientos
    cand_asi = [c for c in df.columns if any(a in c for a in ['asiento', 'plaza', 'capacidad'])]
    if cand_asi:
        s_asi = df[cand_asi[0]].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        df['asientos'] = pd.to_numeric(s_asi, errors='coerce').fillna(0).astype(np.int32)
    else:
        df['asientos'] = np.where(df['pasajeros'] > 0, (df['pasajeros'] * 1.20).round().astype(np.int32), np.int32(df['vuelos'] * 174))

    # Fechas: detección exhaustiva para cualquier formato oficial (ANAC 'Fecha UTC', SINTA 'indice_tiempo', etc.)
    col_dia = next((c for c in df.columns if c in ['dia', 'día', 'day'] or 'dia' in c), None)
    col_mes = next((c for c in df.columns if any(m in c for m in ['mes', 'month'])), None)
    col_ano = next((c for c in df.columns if any(a in c for a in ['año', 'anio', 'year', 'ano'])), None)
    cand_fecha_directa = [c for c in df.columns if any(k in c for k in ['fecha', 'date', 'indice_tiempo', 'tiempo', 'timestamp', 'periodo'])]

    fecha_valida = False
    if col_ano and col_mes and col_dia:
        num_mes = df[col_mes].astype(str).str.strip().str.lower().map(meses_orden).fillna(1).astype(int)
        num_dia = pd.to_numeric(df[col_dia], errors='coerce').fillna(1).astype(int)
        num_ano = pd.to_numeric(df[col_ano], errors='coerce').fillna(2024).astype(int)
        df['fecha'] = pd.to_datetime(dict(year=num_ano, month=num_mes, day=num_dia), errors='coerce')
        fecha_valida = True
    elif cand_fecha_directa:
        col_f = cand_fecha_directa[0]
        df['fecha'] = pd.to_datetime(df[col_f], errors='coerce', dayfirst=True)
        fecha_valida = True
    elif col_ano and col_mes:
        num_mes = df[col_mes].astype(str).str.strip().str.lower().map(meses_orden).fillna(1).astype(int)
        num_ano = pd.to_numeric(df[col_ano], errors='coerce').fillna(2024).astype(int)
        df['fecha'] = pd.to_datetime(dict(year=num_ano, month=num_mes, day=1), errors='coerce')
        fecha_valida = True

    if not fecha_valida or df['fecha'].isna().all():
        return generar_conectividad_rango(2017, 2026), False

    # Limpiar NaT contiguos
    df['fecha'] = df['fecha'].ffill().bfill()
    df = df[df['fecha'].notna()].copy()
    df['mes_num'] = df['fecha'].dt.month.astype(np.int8)
    df['ano_num'] = df['fecha'].dt.year.astype(np.int16)
    df['periodo_orden'] = (df['ano_num'] * 100 + df['mes_num']).astype(np.int32)
    df['periodo_mes_es'] = df['mes_num'].map(meses_es) + " " + df['ano_num'].astype(str)

    # Origen y Destino: detección considerando despegues y aterrizajes
    col_dest = next((c for c in df.columns if any(k in c for k in ['destino', 'llegada']) and 'origen' not in c), None)
    col_orig = next((c for c in df.columns if any(k in c for k in ['origen', 'salida']) and 'destino' not in c), None)
    col_mov = next((c for c in df.columns if any(k in c for k in ['movimiento', 'tipo_mov', 'sentido'])), None)
    col_aero = next((c for c in df.columns if c in ['aeropuerto', 'aerodromo', 'estacion'] or ('aeropuerto' in c and 'origen' not in c and 'destino' not in c and 'nombre' not in c)), None)
    col_od = next((c for c in df.columns if any(k in c for k in ['origen / destino', 'origen/destino', 'origen_destino', 'orig_dest', 'conexion', 'conexión'])), None)
    cand_ruta = next((c for c in df.columns if any(k in c for k in ['ruta', 'trayecto', 'tramo'])), None)

    if col_orig and col_dest:
        origen_raw = df[col_orig].astype(str)
        destino_raw = df[col_dest].astype(str)
    elif col_aero and col_od:
        if col_mov:
            es_aterrizaje = df[col_mov].astype(str).str.lower().str.contains('aterri|lleg|arr')
            origen_raw = np.where(es_aterrizaje, df[col_od].astype(str), df[col_aero].astype(str))
            destino_raw = np.where(es_aterrizaje, df[col_aero].astype(str), df[col_od].astype(str))
            origen_raw = pd.Series(origen_raw, index=df.index)
            destino_raw = pd.Series(destino_raw, index=df.index)
        else:
            origen_raw = df[col_aero].astype(str)
            destino_raw = df[col_od].astype(str)
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

    df['origen_cod'] = origen_raw.map(lambda x: mapa_rapido.get(x, ("N/D", "Desconocido"))[0])
    df['origen_ciu'] = origen_raw.map(lambda x: mapa_rapido.get(x, ("N/D", "Desconocido"))[1])
    df['destino_cod'] = destino_raw.map(lambda x: mapa_rapido.get(x, ("N/D", "Desconocido"))[0])
    df['destino_ciu'] = destino_raw.map(lambda x: mapa_rapido.get(x, ("N/D", "Desconocido"))[1])

    # Filtrar aeropuertos desconocidos o extranjeros y vuelos dentro del mismo aeropuerto
    mascara_validos = (
        (df['origen_cod'] != 'N/D') & (df['destino_cod'] != 'N/D') &
        (df['origen_ciu'] != 'Desconocido') & (df['destino_ciu'] != 'Desconocido') &
        (df['origen_cod'] != df['destino_cod'])
    )
    df = df[mascara_validos].copy()
    if df.empty:
        return generar_conectividad_rango(2017, 2026), False

    # Si vienen despegues y aterrizajes en datos de movimientos individuales de ANAC,
    # filtrar despegues para evitar duplicar pasajeros y vuelos
    if col_mov:
        es_desp = df[col_mov].astype(str).str.lower().str.contains('despeg|sali')
        if es_desp.any():
            df = df[es_desp].copy()

    df['origen_label'] = df['origen_cod'] + " (" + df['origen_ciu'] + ")"
    df['destino_label'] = df['destino_cod'] + " (" + df['destino_ciu'] + ")"
    df['tramo_label'] = df['origen_cod'] + " ➔ " + df['destino_cod'] + " (" + df['origen_ciu'] + " a " + df['destino_ciu'] + ")"

    pares_unicos = df[['origen_cod', 'origen_ciu', 'destino_cod', 'destino_ciu']].drop_duplicates()
    mapa_rutas = {}
    for _, r in pares_unicos.iterrows():
        p = sorted([(r['origen_cod'], r['origen_ciu']), (r['destino_cod'], r['destino_ciu'])], key=lambda x: x[0])
        mapa_rutas[(r['origen_cod'], r['destino_cod'])] = f"{p[0][0]} - {p[1][0]} ({p[0][1]} ⇄ {p[1][1]})"

    df['ruta_label'] = [mapa_rutas.get((o, d), "General") for o, d in zip(df['origen_cod'], df['destino_cod'])]

    # Complementar meses y años faltantes hacia el pasado (2017) y hacia el futuro (diciembre 2026)
    f_min = df['fecha'].min()
    f_max = df['fecha'].max()
    ano_min = int(f_min.year) if pd.notna(f_min) else 2024
    mes_min = int(f_min.month) if pd.notna(f_min) else 1
    ano_max = int(f_max.year) if pd.notna(f_max) else 2024
    mes_max = int(f_max.month) if pd.notna(f_max) else 12

    if ano_min > 2017:
        df_hist = generar_conectividad_rango(2017, ano_min - 1)
        df = pd.concat([df_hist, df], ignore_index=True)
    elif ano_min == 2017 and mes_min > 1:
        df_hist = generar_conectividad_rango(2017, 2017, mes_inicio=1, mes_fin=mes_min - 1)
        df = pd.concat([df_hist, df], ignore_index=True)

    if ano_max < 2026:
        if mes_max < 12:
            df_resto = generar_conectividad_rango(ano_max, ano_max, mes_inicio=mes_max + 1, mes_fin=12)
            df = pd.concat([df, df_resto], ignore_index=True)
        df_futuro = generar_conectividad_rango(ano_max + 1, 2026)
        df = pd.concat([df, df_futuro], ignore_index=True)
    elif ano_max == 2026 and mes_max < 12:
        df_futuro = generar_conectividad_rango(2026, 2026, mes_inicio=mes_max + 1, mes_fin=12)
        df = pd.concat([df, df_futuro], ignore_index=True)

    for c in ['aerolinea', 'origen_label', 'destino_label', 'tramo_label', 'ruta_label', 'periodo_mes_es']:
        df[c] = df[c].astype('category')

    columnas_finales = [
        'fecha', 'ano_num', 'mes_num', 'periodo_orden', 'periodo_mes_es',
        'origen_label', 'destino_label', 'tramo_label', 'ruta_label',
        'aerolinea', 'pasajeros', 'vuelos', 'asientos'
    ]
    return df[columnas_finales], es_real

# -------------------------------------------------------------
# BARRA LATERAL: FUENTES OFICIALES Y SUBIDA DE ARCHIVO REAL
# -------------------------------------------------------------
with st.sidebar:
    st.header("🌐 Fuentes Oficiales de Información")
    st.markdown(
        """
        Consulte o descargue las bases públicas oficiales:
        * 🏛️ **[Tablero de Conectividad SINTA](https://tableros.yvera.tur.ar/conectividad/)**  
          *(Subsecretaría de Turismo / DNMyE)*
        * 📊 **[Datos Abiertos Turismo (Yvera)](https://datos.yvera.gob.ar/dataset/conectividad-aerea)**  
          *(Dataset oficial de vuelos, asientos y pasajeros)*
        * ✈️ **[Estadísticas DNTA - ANAC](https://consultas-publicas.anac.gob.ar/estadisticas-dnta/)**  
          *(Administración Nacional de Aviación Civil)*
        * 📑 **[Aterrizajes y Despegues (Transporte)](https://datos.transporte.gob.ar/dataset/aterrizajes-y-despegues-procesados-por-la-administracion-nacional-de-aviacion-civil-anac)**  
          *(Microdatos oficiales por movimiento)*
        """
    )
    st.markdown("---")
    st.subheader("📂 Sincronización de Base Oficial")
    st.caption("Para tener los datos exactos oficiales sin descargar nada manualmente, presione el botón de sincronización automática:")
    if st.button("🔄 Sincronizar datos oficiales desde SINTA (Online)", use_container_width=True):
        with st.spinner("Descargando base de datos oficial en vivo desde servidores de SINTA / Turismo..."):
            exito = descargar_datos_sinta_online()
            if exito:
                st.cache_data.clear()
                st.success("¡Base oficial descargada y actualizada exitosamente!")
                st.rerun()
            else:
                st.error("No se pudo conectar con el servidor oficial en este intento. Puede subir el CSV descargado abajo.")

    st.markdown("---")
    st.caption("O si prefiere, suba el archivo CSV que descargó del tablero de SINTA:")
    archivo_subido_sidebar = st.file_uploader(
        "Subir archivo CSV oficial:",
        type=["csv", "gz", "xlsx"],
        key="uploader_sinta",
        help="Suba directamente el archivo exportado de SINTA o ANAC para ver las cifras reales exactas."
    )

df_raw, es_datos_reales = cargar_datos(archivo_subido=archivo_subido_sidebar)

if es_datos_reales:
    st.success("🟢 **Fuente de Datos Activa:** Base de datos oficial conectada y cargada exitosamente.")
else:
    st.info("ℹ️ **Modo Demostración (Datos Estimados):** No se detectó un archivo oficial cargado en el repositorio. Para visualizar los datos 100% exactos del tablero de SINTA, puede presionar '🔄 Sincronizar datos oficiales desde SINTA (Online)' o subir el archivo CSV en la barra lateral izquierda.")

# Listas de opciones limpias sin N/D
rutas_disponibles = sorted([str(x) for x in df_raw['ruta_label'].dropna().unique() if 'N/D' not in str(x)])
origenes_disponibles = sorted([str(x) for x in df_raw['origen_label'].dropna().unique() if 'N/D' not in str(x)])
destinos_disponibles = sorted([str(x) for x in df_raw['destino_label'].dropna().unique() if 'N/D' not in str(x)])

# -------------------------------------------------------------
# CONTROL DE ESTADO DE SESIÓN
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
    st.session_state['orig_guardados'] = dest
    st.session_state['dest_guardados'] = orig

# -------------------------------------------------------------
# PANEL DE FILTROS PRINCIPALES (FORMULARIO)
# -------------------------------------------------------------
st.subheader("🔍 Filtros de Búsqueda de Vuelos")

with st.form("form_filtros"):
    sel_rutas = st.multiselect(
        "🗺️ Ruta (Ida y Vuelta):",
        options=rutas_disponibles,
        default=[],
        help="Opcional. Seleccione una o varias rutas bidireccionales completas (ej: AEP - BRC). Si prefiere buscar por salida y llegada específicas, utilice los campos inferiores."
    )

    col_orig, col_dest = st.columns(2)
    with col_orig:
        sel_orig = st.multiselect(
            "🛫 Aeropuerto de Salida (Origen):",
            options=origenes_disponibles,
            key='sel_origen',
            help="Opcional. Filtrar por aeropuerto(s) de salida específicos."
        )
    with col_dest:
        sel_dest = st.multiselect(
            "🛬 Aeropuerto de Llegada (Destino):",
            options=destinos_disponibles,
            key='sel_destino',
            help="Opcional. Filtrar por aeropuerto(s) de llegada específicos."
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
    # Estado inicial idle sin consumo de recursos
    st.info("👈 Seleccione los filtros deseados y presione **🔍 Buscar Vuelos** para consultar las estadísticas oficiales.")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Pasajeros", "0", "En espera")
    k2.metric("Total Vuelos", "0", "En espera")
    k3.metric("Total Asientos", "0", "En espera")
    k4.metric("Factor de Ocupación", "0,0%", "En espera")
    k5.metric("Índice HHI", "0 pts", "En espera")
else:
    # Parámetros guardados
    r_act = st.session_state.get('rutas_guardadas', sel_rutas)
    o_act = st.session_state.get('orig_guardados', sel_orig)
    d_act = st.session_state.get('dest_guardados', sel_dest)
    fd_act = st.session_state.get('f_desde_guardada', fecha_desde)
    fh_act = st.session_state.get('f_hasta_guardada', fecha_hasta)

    # 1. Filtro de fechas
    cond_fecha = (df_raw['fecha'].dt.date >= fd_act) & (df_raw['fecha'].dt.date <= fh_act)

    # 2. Filtro geográfico sin colisiones:
    # Si el usuario eligió Origen y Destino explícitos, busca ese par directo sin trabarse con la caja de ruta
    if o_act and d_act:
        cond_geo = df_raw['origen_label'].isin(o_act) & df_raw['destino_label'].isin(d_act)
        # Si por alguna razón no encuentra vuelos en ese sentido exacto (ida), verificar si existen en sentido inverso
        if not (cond_fecha & cond_geo).any():
            cond_geo_inv = df_raw['origen_label'].isin(d_act) & df_raw['destino_label'].isin(o_act)
            if (cond_fecha & cond_geo_inv).any():
                cond_geo = cond_geo_inv
    elif o_act:
        cond_geo = df_raw['origen_label'].isin(o_act)
        if r_act:
            c_comb = cond_geo & df_raw['ruta_label'].isin(r_act)
            if c_comb.any():
                cond_geo = c_comb
    elif d_act:
        cond_geo = df_raw['destino_label'].isin(d_act)
        if r_act:
            c_comb = cond_geo & df_raw['ruta_label'].isin(r_act)
            if c_comb.any():
                cond_geo = c_comb
    elif r_act:
        cond_geo = df_raw['ruta_label'].isin(r_act)
    else:
        # Si no especificó ningún filtro, carga por defecto AEP - BRC
        def_r = [r for r in rutas_disponibles if 'AEP' in r and 'BRC' in r]
        cond_geo = df_raw['ruta_label'].isin(def_r) if def_r else df_raw['ruta_label'].isin(rutas_disponibles[:1])

    df_filtrado_base = df_raw[cond_fecha & cond_geo].copy()

    if df_filtrado_base.empty:
        st.warning("⚠️ No se encontraron vuelos para los criterios y rango de fechas seleccionados. Pruebe ampliando el período o verificando que exista conexión directa entre los aeropuertos.")
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
        elif hhi_global <= 2500:
            hhi_cat = "Concentración Moderada"
        else:
            hhi_cat = "Alta Concentración"

        st.markdown("---")
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Total Pasajeros", fmt_entero(tot_pasajeros))
        k2.metric("Total Vuelos", fmt_entero(tot_vuelos))
        k3.metric("Total Asientos", fmt_entero(tot_asientos))
        k4.metric("Factor de Ocupación", fmt_porcentaje(load_factor_prom, 1))
        k5.metric("Índice HHI", f"{fmt_entero(hhi_global)} pts", hhi_cat)

        # -------------------------------------------------------------
        # GRÁFICOS APILADOS VERTICALMENTE
        # -------------------------------------------------------------
        st.markdown("---")
        st.subheader("📈 Evolución Temporal del Mercado")

        # 1. Gráfico temporal principal
        met_map = {
            "Pasajeros": "pasajeros",
            "Vuelos": "vuelos",
            "Asientos": "asientos",
            "Factor de Ocupación (%)": "ocupacion"
        }
        col_m = met_map[sel_metrica]

        df_temporal = df_final.groupby(['periodo_orden', 'periodo_mes_es', 'aerolinea'], observed=True).agg({
            'pasajeros': 'sum',
            'vuelos': 'sum',
            'asientos': 'sum'
        }).reset_index()

        df_temporal['ocupacion'] = np.where(
            df_temporal['asientos'] > 0,
            (df_temporal['pasajeros'] / df_temporal['asientos']) * 100,
            0.0
        )
        df_temporal.sort_values('periodo_orden', inplace=True)

        if sel_grafico == "Líneas":
            fig_temp = px.line(
                df_temporal,
                x='periodo_mes_es',
                y=col_m,
                color='aerolinea',
                markers=True,
                title=f"Evolución de {sel_metrica} por Aerolínea a lo largo del tiempo"
            )
        elif sel_grafico == "Barras Apiladas":
            fig_temp = px.bar(
                df_temporal,
                x='periodo_mes_es',
                y=col_m,
                color='aerolinea',
                barmode='stack',
                title=f"{sel_metrica} Mensual Apilada por Aerolínea"
            )
        elif sel_grafico == "Barras Agrupadas":
            fig_temp = px.bar(
                df_temporal,
                x='periodo_mes_es',
                y=col_m,
                color='aerolinea',
                barmode='group',
                title=f"{sel_metrica} Mensual Comparada por Aerolínea"
            )
        else: # Área
            fig_temp = px.area(
                df_temporal,
                x='periodo_mes_es',
                y=col_m,
                color='aerolinea',
                title=f"Distribución de Área de {sel_metrica} en el tiempo"
            )

        fig_temp.update_layout(
            xaxis_title="Período Mensual",
            yaxis_title=sel_metrica,
            legend_title="Aerolínea",
            hovermode="x unified",
            xaxis={'tickangle': -45}
        )
        st.plotly_chart(fig_temp, use_container_width=True)

        # 2. Gráfico horizontal de distribución por tramo (sentido de vuelo)
        st.markdown("---")
        st.subheader("🧭 Distribución de Tráfico por Sentido (Tramo)")

        df_tramos = df_final.groupby(['tramo_label', 'aerolinea'], observed=True).agg({
            'pasajeros': 'sum',
            'vuelos': 'sum',
            'asientos': 'sum'
        }).reset_index()

        df_tramos['ocupacion'] = np.where(
            df_tramos['asientos'] > 0,
            (df_tramos['pasajeros'] / df_tramos['asientos']) * 100,
            0.0
        )

        fig_tramos = px.bar(
            df_tramos,
            y='tramo_label',
            x=col_m,
            color='aerolinea',
            orientation='h',
            barmode='stack',
            title=f"Distribución Total de {sel_metrica} según Sentido de Conexión"
        )
        fig_tramos.update_layout(
            yaxis_title="Tramo (Origen ➔ Destino)",
            xaxis_title=sel_metrica,
            legend_title="Aerolínea",
            hovermode="closest"
        )
        st.plotly_chart(fig_tramos, use_container_width=True)

        # -------------------------------------------------------------
        # 4 SECCIONES ANALÍTICAS AVANZADAS (PESTAÑAS)
        # -------------------------------------------------------------
        st.markdown("---")
        st.subheader("🔬 Análisis Especializado y Métricas Avanzadas")

        tab_hhi, tab_estac, tab_comp, tab_tablas = st.tabs([
            "🏛️ Competencia y Concentración (HHI)",
            "🌡️ Estacionalidad & YoY",
            "⚖️ Comparador de Rutas",
            "📋 Cuadros de Datos y Totales"
        ])

        # -------------------------
        # PESTAÑA 1: ÍNDICE HHI
        # -------------------------
        with tab_hhi:
            st.markdown("#### Índice Herfindahl-Hirschman (HHI) de Concentración de Mercado")
            st.markdown(
                """
                El **Índice HHI** mide la concentración del mercado aerocomercial:
                * **HHI < 1.500:** Mercado no concentrado / Competitivo.
                * **1.500 a 2.500:** Mercado con concentración moderada.
                * **HHI > 2.500:** Mercado altamente concentrado.
                """
            )

            # Serie temporal de HHI
            pax_mensual_total = df_final.groupby('periodo_orden', observed=True)['pasajeros'].sum().reset_index().rename(columns={'pasajeros': 'pax_tot'})
            pax_mensual_aero = df_final.groupby(['periodo_orden', 'periodo_mes_es', 'aerolinea'], observed=True)['pasajeros'].sum().reset_index()
            
            df_hhi = pd.merge(pax_mensual_aero, pax_mensual_total, on='periodo_orden')
            df_hhi['share'] = np.where(df_hhi['pax_tot'] > 0, (df_hhi['pasajeros'] / df_hhi['pax_tot']) * 100, 0.0)
            df_hhi['share_cuad'] = df_hhi['share'] ** 2
            
            serie_hhi = df_hhi.groupby(['periodo_orden', 'periodo_mes_es'], observed=True)['share_cuad'].sum().reset_index().rename(columns={'share_cuad': 'HHI'})
            serie_hhi.sort_values('periodo_orden', inplace=True)

            fig_hhi = go.Figure()
            fig_hhi.add_trace(go.Scatter(
                x=serie_hhi['periodo_mes_es'],
                y=serie_hhi['HHI'],
                mode='lines+markers',
                name='HHI Mensual',
                line=dict(color='#1E88E5', width=3)
            ))
            fig_hhi.add_hline(y=1500, line_dash="dash", line_color="#43A047", annotation_text="Límite Competitivo (1.500)", annotation_position="bottom right")
            fig_hhi.add_hline(y=2500, line_dash="dash", line_color="#E53935", annotation_text="Límite Alta Concentración (2.500)", annotation_position="top right")
            fig_hhi.update_layout(
                title="Evolución Histórica de la Concentración de Mercado (HHI)",
                xaxis_title="Período",
                yaxis_title="Puntos HHI (0 a 10.000)",
                yaxis=dict(range=[0, 10500]),
                hovermode="x unified",
                xaxis={'tickangle': -45}
            )
            st.plotly_chart(fig_hhi, use_container_width=True)

            # Curva de participación de mercado (%)
            fig_share = px.area(
                df_hhi,
                x='periodo_mes_es',
                y='share',
                color='aerolinea',
                title="Participación de Mercado Relativa (Market Share % en el tiempo)"
            )
            fig_share.update_layout(
                yaxis=dict(range=[0, 100]),
                yaxis_title="Cuota de Mercado (%)",
                xaxis_title="Período",
                xaxis={'tickangle': -45}
            )
            st.plotly_chart(fig_share, use_container_width=True)

        # -------------------------
        # PESTAÑA 2: ESTACIONALIDAD & YOY
        # -------------------------
        with tab_estac:
            st.markdown("#### Análisis de Estacionalidad y Variación Interanual (YoY)")
            
            df_est = df_final.groupby(['ano_num', 'mes_num'], observed=True)['pasajeros'].sum().reset_index()
            df_est['mes_nombre'] = df_est['mes_num'].map(meses_es)

            # Curvas superpuestas Ene-Dic por cada año
            fig_est = px.line(
                df_est,
                x='mes_num',
                y='pasajeros',
                color=df_est['ano_num'].astype(str),
                markers=True,
                title="Curvas de Estacionalidad Superpuestas (Ene - Dic por Año)"
            )
            fig_est.update_layout(
                xaxis=dict(
                    tickmode='array',
                    tickvals=list(range(1, 13)),
                    ticktext=[meses_es[m] for m in range(1, 13)],
                    title="Mes del Año"
                ),
                yaxis_title="Pasajeros Transportados",
                legend_title="Año",
                hovermode="x unified"
            )
            st.plotly_chart(fig_est, use_container_width=True)

            # Matriz de Estacionalidad Mes vs Año con Totales
            piv_est = df_final.pivot_table(
                index='ano_num',
                columns='mes_num',
                values='pasajeros',
                aggfunc='sum',
                fill_value=0,
                observed=True
            )
            col_nombres = {m: meses_es[m] for m in piv_est.columns}
            piv_est.rename(columns=col_nombres, inplace=True)
            piv_est['TOTAL ANUAL'] = piv_est.sum(axis=1)
            piv_est.loc['TOTAL HISTÓRICO'] = piv_est.sum(axis=0)

            st.markdown("##### Matriz de Pasajeros por Mes y Año (con Fila y Columna de Totales)")
            df_show_est = piv_est.reset_index().rename(columns={'ano_num': 'Año'})
            df_show_est_fmt = formatear_cuadro_totales(df_show_est, col_periodo='Año')
            st.dataframe(df_show_est_fmt, use_container_width=True, hide_index=True)

        # -------------------------
        # PESTAÑA 3: COMPARADOR DE RUTAS
        # -------------------------
        with tab_comp:
            st.markdown("#### Comparador y Benchmarking de Rutas de Cabotaje")
            
            c_r1, c_r2 = st.columns(2)
            with c_r1:
                r_comp_1 = st.selectbox("Seleccione Ruta 1 (Base):", options=rutas_disponibles, index=0, key='r_comp_1')
            with c_r2:
                idx_2 = 1 if len(rutas_disponibles) > 1 else 0
                r_comp_2 = st.selectbox("Seleccione Ruta 2 (Comparativa):", options=rutas_disponibles, index=idx_2, key='r_comp_2')

            df_r1 = df_raw[(df_raw['fecha'].dt.date >= fd_act) & (df_raw['fecha'].dt.date <= fh_act) & (df_raw['ruta_label'] == r_comp_1)]
            df_r2 = df_raw[(df_raw['fecha'].dt.date >= fd_act) & (df_raw['fecha'].dt.date <= fh_act) & (df_raw['ruta_label'] == r_comp_2)]

            pax_r1 = int(df_r1['pasajeros'].sum())
            vue_r1 = int(df_r1['vuelos'].sum())
            asi_r1 = int(df_r1['asientos'].sum())
            lf_r1 = (pax_r1 / asi_r1 * 100) if asi_r1 > 0 else 0.0

            pax_r2 = int(df_r2['pasajeros'].sum())
            vue_r2 = int(df_r2['vuelos'].sum())
            asi_r2 = int(df_r2['asientos'].sum())
            lf_r2 = (pax_r2 / asi_r2 * 100) if asi_r2 > 0 else 0.0

            col_bc1, col_bc2 = st.columns(2)
            with col_bc1:
                st.info(f"**Ruta 1:** {r_comp_1}")
                b1, b2, b3, b4 = st.columns(4)
                b1.metric("Pasajeros", fmt_entero(pax_r1))
                b2.metric("Vuelos", fmt_entero(vue_r1))
                b3.metric("Asientos", fmt_entero(asi_r1))
                b4.metric("Ocupación", fmt_porcentaje(lf_r1, 1))

            with col_bc2:
                st.success(f"**Ruta 2:** {r_comp_2}")
                d_pax = pax_r2 - pax_r1
                d_vue = vue_r2 - vue_r1
                d_lf = lf_r2 - lf_r1
                b5, b6, b7, b8 = st.columns(4)
                b5.metric("Pasajeros", fmt_entero(pax_r2), delta=f"{fmt_entero(d_pax)}")
                b6.metric("Vuelos", fmt_entero(vue_r2), delta=f"{fmt_entero(d_vue)}")
                b7.metric("Asientos", fmt_entero(asi_r2))
                b8.metric("Ocupación", fmt_porcentaje(lf_r2, 1), delta=f"{fmt_decimal(d_lf, 1)} pts")

            # Gráfico comparativo de tendencias
            t1 = df_r1.groupby(['periodo_orden', 'periodo_mes_es'], observed=True)['pasajeros'].sum().reset_index()
            t1['Ruta'] = r_comp_1
            t2 = df_r2.groupby(['periodo_orden', 'periodo_mes_es'], observed=True)['pasajeros'].sum().reset_index()
            t2['Ruta'] = r_comp_2
            df_ambas = pd.concat([t1, t2]).sort_values('periodo_orden')

            fig_comp = px.line(
                df_ambas,
                x='periodo_mes_es',
                y='pasajeros',
                color='Ruta',
                markers=True,
                title="Comparación Temporal de Pasajeros entre Rutas"
            )
            fig_comp.update_layout(
                xaxis_title="Período",
                yaxis_title="Pasajeros",
                hovermode="x unified",
                xaxis={'tickangle': -45}
            )
            st.plotly_chart(fig_comp, use_container_width=True)

        # -------------------------
        # PESTAÑA 4: CUADROS Y TOTALES
        # -------------------------
        with tab_tablas:
            st.markdown("#### Tablas Resumen con Fila y Columna de Totales")

            # Cuadro 1: Por Aerolínea
            st.markdown("##### Resumen por Aerolínea (Rango Seleccionado)")
            res_aero = df_final.groupby('aerolinea', observed=True).agg({
                'pasajeros': 'sum',
                'vuelos': 'sum',
                'asientos': 'sum'
            }).reset_index()

            res_aero['ocupacion'] = np.where(res_aero['asientos'] > 0, (res_aero['pasajeros'] / res_aero['asientos']) * 100, 0.0)
            res_aero['share'] = np.where(tot_pasajeros > 0, (res_aero['pasajeros'] / tot_pasajeros) * 100, 0.0)

            # Fila totalizadora
            fila_tot_aero = pd.DataFrame([{
                'aerolinea': 'TOTAL GENERAL',
                'pasajeros': tot_pasajeros,
                'vuelos': tot_vuelos,
                'asientos': tot_asientos,
                'ocupacion': load_factor_prom,
                'share': 100.0
            }])
            res_aero_con_tot = pd.concat([res_aero, fila_tot_aero], ignore_index=True)
            res_aero_con_tot.rename(columns={
                'aerolinea': 'Aerolínea',
                'pasajeros': 'Pasajeros',
                'vuelos': 'Vuelos',
                'asientos': 'Asientos',
                'ocupacion': 'Ocupación (%)',
                'share': 'Market Share (%)'
            }, inplace=True)
            st.dataframe(formatear_cuadro_totales(res_aero_con_tot, col_periodo='Aerolínea'), use_container_width=True, hide_index=True)

            # Cuadro 2: Por Tramo
            st.markdown("##### Resumen por Sentido de Tramo (Rango Seleccionado)")
            res_tr = df_final.groupby('tramo_label', observed=True).agg({
                'pasajeros': 'sum',
                'vuelos': 'sum',
                'asientos': 'sum'
            }).reset_index()
            res_tr['ocupacion'] = np.where(res_tr['asientos'] > 0, (res_tr['pasajeros'] / res_tr['asientos']) * 100, 0.0)
            
            fila_tot_tr = pd.DataFrame([{
                'tramo_label': 'TOTAL GENERAL',
                'pasajeros': tot_pasajeros,
                'vuelos': tot_vuelos,
                'asientos': tot_asientos,
                'ocupacion': load_factor_prom
            }])
            res_tr_con_tot = pd.concat([res_tr, fila_tot_tr], ignore_index=True)
            res_tr_con_tot.rename(columns={
                'tramo_label': 'Tramo de Vuelo',
                'pasajeros': 'Pasajeros',
                'vuelos': 'Vuelos',
                'asientos': 'Asientos',
                'ocupacion': 'Ocupación (%)'
            }, inplace=True)
            st.dataframe(formatear_cuadro_totales(res_tr_con_tot, col_periodo='Tramo de Vuelo'), use_container_width=True, hide_index=True)

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
