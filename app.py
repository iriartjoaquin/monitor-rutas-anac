import os
import io
import re
import zipfile
import warnings
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px

warnings.filterwarnings("ignore")

# Configuración de interfaz
st.set_page_config(
    page_title="Monitor de Conectividad y Rutas Aéreas ANAC",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Diccionarios y constantes de referencia
meses_es = {
    1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
    7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'
}

meses_map = {
    'ene': 1, 'enero': 1, 'jan': 1, 'january': 1,
    'feb': 2, 'febrero': 2, 'february': 2,
    'mar': 3, 'marzo': 3, 'march': 3,
    'abr': 4, 'abril': 4, 'apr': 4, 'april': 4,
    'may': 5, 'mayo': 5,
    'jun': 6, 'junio': 6, 'june': 6,
    'jul': 7, 'julio': 7, 'july': 7,
    'ago': 8, 'agosto': 8, 'aug': 8, 'august': 8,
    'sep': 9, 'septiembre': 9, 'set': 9, 'setiembre': 9, 'september': 9,
    'oct': 10, 'octubre': 10, 'october': 10,
    'nov': 11, 'noviembre': 11, 'november': 11,
    'dic': 12, 'diciembre': 12, 'dec': 12, 'december': 12
}

AEROPUERTOS_EXHAUSTIVO = {
    'AEP': {'codigo': 'AEP', 'ciudad': 'Aeroparque', 'keywords': ['AEROPARQUE', 'JORGE NEWBERY', 'BUENOS AIRES', 'CABA', 'AEP']},
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
    'RLO': {'codigo': 'RLO', 'ciudad': 'Valle del Conlara (Merlo)', 'keywords': ['VALLE DEL CONLARA', 'CONLARA', 'MERLO', 'RLO']},
    'PMQ': {'codigo': 'PMQ', 'ciudad': 'Perito Moreno', 'keywords': ['PERITO MORENO', 'JALIL HAMER', 'HAMER', 'PMQ']},
    'RCQ': {'codigo': 'RCQ', 'ciudad': 'Reconquista', 'keywords': ['RECONQUISTA', 'DANIEL JUKIC', 'JUKIC', 'RCQ']},
    'RZA': {'codigo': 'RZA', 'ciudad': 'Puerto Santa Cruz', 'keywords': ['PUERTO SANTA CRUZ', 'SANTA CRUZ', 'RZA']},
    'NCJ': {'codigo': 'NCJ', 'ciudad': 'Sunchales', 'keywords': ['SUNCHALES', 'NCJ']},
    'ROY': {'codigo': 'ROY', 'ciudad': 'Río Mayo', 'keywords': ['RIO MAYO', 'RÍO MAYO', 'ROY']},
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
    'GGS': {'codigo': 'GGS', 'ciudad': 'Gobernador Gregores', 'keywords': ['GOBERNADOR GREGORES', 'GREGORES', 'GGS']},
    'ULA': {'codigo': 'ULA', 'ciudad': 'San Julián', 'keywords': ['SAN JULIAN', 'SAN JULIÁN', 'ULA']},
    'SZT': {'codigo': 'SZT', 'ciudad': 'San Cristóbal', 'keywords': ['SAN CRISTOBAL', 'SZT']},
    'RDS': {'codigo': 'RDS', 'ciudad': 'Rincón de los Sauces', 'keywords': ['RINCON DE LOS SAUCES', 'RDS']},
    'APZ': {'codigo': 'APZ', 'ciudad': 'Zapala', 'keywords': ['ZAPALA', 'APZ']},
    'CUT': {'codigo': 'CUT', 'ciudad': 'Cutral Có', 'keywords': ['CUTRAL CO', 'CUTRAL CÓ', 'CUT']},
    'SST': {'codigo': 'SST', 'ciudad': 'Santa Teresita', 'keywords': ['SANTA TERESITA', 'SST']},
    'GHU': {'codigo': 'GHU', 'ciudad': 'Gualeguaychú', 'keywords': ['GUALEGUAYCHU', 'GUALEGUAYCHÚ', 'GHU']},
    'COC': {'codigo': 'COC', 'ciudad': 'Concordia', 'keywords': ['CONCORDIA', 'PIERRESTEGUI', 'COC']},
    'JNI': {'codigo': 'JNI', 'ciudad': 'Junín', 'keywords': ['JUNIN', 'JUNÍN', 'JNI']},
    'TTG': {'codigo': 'TTG', 'ciudad': 'Tartagal', 'keywords': ['TARTAGAL', 'TTG']},
    'ORS': {'codigo': 'ORS', 'ciudad': 'Orán', 'keywords': ['ORAN', 'ORÁN', 'ORS']},
    'CLX': {'codigo': 'CLX', 'ciudad': 'Clorinda', 'keywords': ['CLORINDA', 'CLX']},
    'PRQ': {'codigo': 'PRQ', 'ciudad': 'Presidencia Roque Sáenz Peña', 'keywords': ['SAENZ PENA', 'SÁENZ PEÑA', 'ROQUE SAENZ', 'PRQ']},
    'CUR': {'codigo': 'CUR', 'ciudad': 'Curuzú Cuatiá', 'keywords': ['CURUZU', 'CURUZÚ', 'CUR']},
    'MCS': {'codigo': 'MCS', 'ciudad': 'Monte Caseros', 'keywords': ['MONTE CASEROS', 'MCS']},
    'PZL': {'codigo': 'PZL', 'ciudad': 'Paso de los Libres', 'keywords': ['PASO DE LOS LIBRES', 'PZL']},
    'JSM': {'codigo': 'JSM', 'ciudad': 'José de San Martín', 'keywords': ['JOSE DE SAN MARTIN', 'JSM']},
    'LHS': {'codigo': 'LHS', 'ciudad': 'Las Heras', 'keywords': ['LAS HERAS', 'LHS']},
    'ING': {'codigo': 'ING', 'ciudad': 'Lago Argentino', 'keywords': ['LAGO ARGENTINO', 'ING']},
    'CVH': {'codigo': 'CVH', 'ciudad': 'Caviahue', 'keywords': ['CAVIAHUE', 'CVH']},
    'RAF': {'codigo': 'RAF', 'ciudad': 'Rafaela', 'keywords': ['RAFAELA', 'RAF']},
    'VDR': {'codigo': 'VDR', 'ciudad': 'Villa Dolores', 'keywords': ['VILLA DOLORES', 'VDR']},
    'VMR': {'codigo': 'VMR', 'ciudad': 'Villa María', 'keywords': ['VILLA MARIA', 'VILLA MARÍA', 'VMR']},
    'GNR': {'codigo': 'GNR', 'ciudad': 'General Roca', 'keywords': ['GENERAL ROCA', 'ROCA', 'GNR']},
    'OES': {'codigo': 'OES', 'ciudad': 'San Antonio Oeste', 'keywords': ['SAN ANTONIO OESTE', 'OES']},
    'CPF': {'codigo': 'CPF', 'ciudad': 'Cafayate', 'keywords': ['CAFAYATE', 'CPF']},
    'LPG': {'codigo': 'LPG', 'ciudad': 'La Plata', 'keywords': ['LA PLATA', 'LPG']},
    'CHM': {'codigo': 'CHM', 'ciudad': 'Chos Malal', 'keywords': ['CHOS MALAL', 'CHM']},
    'OYA': {'codigo': 'OYA', 'ciudad': 'Goya', 'keywords': ['GOYA', 'OYA']},
    'PUD': {'codigo': 'PUD', 'ciudad': 'Puerto Deseado', 'keywords': ['PUERTO DESEADO', 'DESEADO', 'PUD']},
    'CVI': {'codigo': 'CVI', 'ciudad': 'Caleta Olivia', 'keywords': ['CALETA OLIVIA', 'CVI']},
    'MOR': {'codigo': 'MOR', 'ciudad': 'Morón', 'keywords': ['MORON', 'MORÓN', 'MOR']},
    'EHL': {'codigo': 'EHL', 'ciudad': 'El Bolsón', 'keywords': ['EL BOLSON', 'EL BOLSÓN', 'BOLSON', 'BOLSÓN', 'EHL']},
    'TNO': {'codigo': 'TNO', 'ciudad': 'Tinogasta', 'keywords': ['TINOGASTA', 'TNO']},
    'BCN': {'codigo': 'BCN', 'ciudad': 'Belén', 'keywords': ['BELEN', 'BELÉN', 'BCN']},
    'AND': {'codigo': 'AND', 'ciudad': 'Andalgalá', 'keywords': ['ANDALGALA', 'ANDALGALÁ', 'AND']},
    'SMT': {'codigo': 'SMT', 'ciudad': 'Santa María', 'keywords': ['SANTA MARIA', 'SANTA MARÍA', 'SMT']},
    'MDX': {'codigo': 'MDX', 'ciudad': 'Mercedes', 'keywords': ['MERCEDES', 'MDX']},
    'PDI': {'codigo': 'PDI', 'ciudad': 'Paso de Indios', 'keywords': ['PASO DE INDIOS', 'PDI']},
    'ARR': {'codigo': 'ARR', 'ciudad': 'Alto Río Senguer', 'keywords': ['ALTO RIO SENGUER', 'ALTO RÍO SENGUER', 'SENGUER', 'ARR']},
    'OMR': {'codigo': 'OMR', 'ciudad': 'Sarmiento', 'keywords': ['SARMIENTO', 'OMR']}
}

def normalizar_texto_aeropuerto(txt):
    if not isinstance(txt, str):
        return ""
    txt = txt.upper().strip()
    txt = txt.replace('Ã±', 'N').replace('Ã‘', 'N').replace('ñ', 'N').replace('Ñ', 'N')
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

    # 1. Búsqueda exacta de código IATA conocido
    for iata, datos in AEROPUERTOS_EXHAUSTIVO.items():
        if re.search(r'\b' + re.escape(iata) + r'\b', norm):
            return datos['codigo'], datos['ciudad']

    # 2. Búsqueda por palabras clave oficiales
    for iata, datos in AEROPUERTOS_EXHAUSTIVO.items():
        for kw in datos['keywords']:
            kw_norm = normalizar_texto_aeropuerto(kw)
            if kw_norm and re.search(r'\b' + re.escape(kw_norm) + r'\b', norm):
                return datos['codigo'], datos['ciudad']

    # 3. Fallback inteligente: buscar el nombre propio real sin tomar "AEROPUERTO"
    stopwords = {
        'AEROPUERTO', 'AERODROMO', 'AERÓDROMO', 'BASE', 'AEREA', 'AÉREA', 'MILITAR',
        'INTERNACIONAL', 'INT', 'NACIONAL', 'DE', 'DEL', 'LA', 'EL', 'LOS', 'LAS',
        'SAN', 'SANTA', 'GDOR', 'GOBERNADOR', 'TENIENTE', 'TTE', 'BRIGADIER', 'CAPITAN',
        'ALMIRANTE', 'GENERAL', 'DR', 'DOCTOR', 'VICECOMODORO', 'COMODORO'
    }
    tokens_utiles = [t for t in norm.split() if t not in stopwords and len(t) >= 3]
    
    if tokens_utiles:
        ciudad_cand = tokens_utiles[0].title()
        sigla_fallback = tokens_utiles[0][:3].upper()
    else:
        palabras_resto = [p for p in norm.split() if p not in {'AEROPUERTO', 'AERODROMO', 'INT'}]
        ciudad_cand = palabras_resto[0].title() if palabras_resto else nombre_aeropuerto.strip().title()
        sigla_fallback = ciudad_cand[:3].upper() if len(ciudad_cand) >= 3 else "DES"

    # NUNCA devolver 'AER' ni 'INT' como sigla
    if sigla_fallback in ['AER', 'INT']:
        sigla_fallback = "OTR"

    return sigla_fallback, ciudad_cand

def construir_etiqueta_aeropuerto(nombre_aeropuerto):
    sigla, ciudad = obtener_sigla_y_ciudad(nombre_aeropuerto)
    return f"{sigla} ({ciudad})"

# Formateadores numéricos
fmt_entero = lambda x: f"{int(round(x)):,}".replace(",", ".")
fmt_decimal = lambda x: f"{x:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
fmt_porcentaje = lambda x: f"{x:.1f}%".replace(".", ",")

def limpiar_encabezado(col):
    txt = str(col).strip()
    txt = txt.replace('Ã±', 'n').replace('Ã‘', 'N').replace('ã±', 'n').replace('ñ', 'n').replace('Ñ', 'N')
    txt = txt.replace('Ã¡', 'a').replace('Ã©', 'e').replace('Ã­', 'i').replace('Ã³', 'o').replace('Ãº', 'u')
    txt = txt.replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
    txt = txt.upper()
    txt = re.sub(r'[^A-Z0-9]', ' ', txt)
    return ' '.join(txt.split())

def parsear_mes(val):
    if val is None or pd.isna(val):
        return 1
    s = str(val).strip().lower().replace('.0', '')
    if s.isdigit():
        return max(1, min(int(s), 12))
    s = s.replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
    s = re.sub(r'[^a-z]', '', s)
    return meses_map.get(s, 1)

def parsear_dia(val):
    if val is None or pd.isna(val):
        return 1
    s = str(val).strip()
    try:
        n = int(float(s))
        return max(1, min(n, 31))
    except Exception:
        return 1

def parsear_ano(val):
    if val is None or pd.isna(val):
        return None
    s = str(val).strip()
    try:
        n = int(float(s))
        if 1950 <= n <= 2100:
            return n
    except Exception:
        pass

    m = re.search(r'(19\d\d|20\d\d)', s)
    if m:
        return int(m.group(1))
    return None

@st.cache_data(show_spinner=False)
def cargar_y_limpiar_datos(archivo_path):
    if not os.path.exists(archivo_path):
        return None, f"No se encontró el archivo: {archivo_path}"

    df_raw = None
    
    # 1. Soporte para .zip
    if archivo_path.endswith('.zip'):
        try:
            with zipfile.ZipFile(archivo_path, 'r') as z:
                csv_files = [f for f in z.namelist() if f.endswith('.csv') and not f.startswith('__MACOSX')]
                if not csv_files:
                    return None, "El archivo .zip no contiene ningún archivo .csv válido."
                target_csv = csv_files[0]
                with z.open(target_csv) as f:
                    sample = f.read(4096).decode('utf-8', errors='ignore')
                    f.seek(0)
                    sep = ';' if ';' in sample else (',' if ',' in sample else '\t')
                    df_raw = pd.read_csv(f, sep=sep, low_memory=False, encoding='utf-8', encoding_errors='replace')
        except Exception as e:
            return None, f"Error al descomprimir y leer {archivo_path}: {e}"
            
    # 2. Soporte para .csv / .csv.gz
    else:
        for sep in [';', ',', '\t']:
            try:
                df_raw = pd.read_csv(archivo_path, sep=sep, nrows=10, low_memory=False, encoding='utf-8')
                if len(df_raw.columns) > 1:
                    df_raw = pd.read_csv(archivo_path, sep=sep, low_memory=False, encoding='utf-8', encoding_errors='replace')
                    break
            except Exception:
                continue

    if df_raw is None or len(df_raw.columns) <= 1:
        return None, "No se pudo detectar el formato tabular o delimitador adecuado."

    col_map = {}
    for col in df_raw.columns:
        norm = limpiar_encabezado(col)
        if any(k in norm for k in ['FECHA', 'DATE', 'DIA']):
            col_map['fecha_raw'] = col
        elif any(k in norm for k in ['ANO', 'ANIO', 'YEAR', 'A O']):
            col_map['ano'] = col
        elif any(k in norm for k in ['MES', 'MONTH']):
            col_map['mes'] = col
        elif any(k in norm for k in ['ORIGEN', 'ORIGIN', 'DESDE', 'AEROPUERTO ORIGEN']):
            col_map['origen'] = col
        elif any(k in norm for k in ['DESTINO', 'DESTINATION', 'HASTA', 'AEROPUERTO DESTINO']):
            col_map['destino'] = col
        elif any(k in norm for k in ['EMPRESA', 'AEROLINEA', 'OPERADOR', 'LINEA', 'COMPANIA']):
            col_map['aerolinea'] = col
        elif any(k in norm for k in ['PAX', 'PASAJERO', 'PASAJEROS', 'CANTIDAD PASAJEROS']):
            col_map['pasajeros'] = col
        elif any(k in norm for k in ['VUELO', 'VUELOS', 'MOVIMIENTO', 'OPERACION', 'ETAPA DE VUELO']):
            col_map['vuelos'] = col
        elif any(k in norm for k in ['ASIENTO', 'ASIENTOS', 'BUTACAS', 'CAPACIDAD']):
            col_map['asientos'] = col

    # Requerir al menos origen, destino y fecha
    if 'origen' not in col_map or 'destino' not in col_map:
        return None, "El archivo debe contener columnas identificables de Origen y Destino."

    df = pd.DataFrame()
    df['origen_raw'] = df_raw[col_map['origen']].astype(str).str.strip()
    df['destino_raw'] = df_raw[col_map['destino']].astype(str).str.strip()
    df['aerolinea'] = df_raw[col_map['aerolinea']].astype(str).str.strip().str.title() if 'aerolinea' in col_map else 'Línea Aérea No Especificada'

    # Normalizar valores numéricos
    for dest, src in [('pasajeros', 'pasajeros'), ('asientos', 'asientos'), ('vuelos', 'vuelos')]:
        if src in col_map:
            s = df_raw[col_map[src]].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
            df[dest] = pd.to_numeric(s, errors='coerce').fillna(0).astype(np.int32)
        else:
            df[dest] = 1 if dest == 'vuelos' else 0

    # Construir fecha exacta
    if 'fecha_raw' in col_map:
        df['fecha'] = pd.to_datetime(df_raw[col_map['fecha_raw']], errors='coerce', dayfirst=True)
    else:
        df['fecha'] = pd.NaT

    # Fallback si no hay fecha directa pero hay columnas de año y mes
    if df['fecha'].isna().all() and ('ano' in col_map or 'mes' in col_map):
        anos = [parsear_ano(x) or 2024 for x in df_raw[col_map.get('ano', df_raw.columns[0])]]
        meses = [parsear_mes(x) for x in df_raw[col_map.get('mes', df_raw.columns[0])]]
        dias = [parsear_dia(x) for x in df_raw[col_map.get('dia', df_raw.columns[0])]] if 'dia' in col_map else [1] * len(df)

        def armar_fecha(y, m, d):
            try:
                return datetime(int(y), int(m), int(d))
            except ValueError:
                try:
                    return datetime(int(y), int(m), 28)
                except Exception:
                    return pd.NaT

        df['fecha'] = [armar_fecha(y, m, d) for y, m, d in zip(anos, meses, dias)]

    df = df[df['fecha'].notna()].copy()
    if df.empty:
        return None, "No se pudieron construir fechas válidas a partir de los datos."

    df['ano_num'] = df['fecha'].dt.year.astype(np.int16)
    df['mes_num'] = df['fecha'].dt.month.astype(np.int8)
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

    # Optimización vectorizada de pares y tramos
    o_arr = df['origen_label'].to_numpy()
    d_arr = df['destino_label'].to_numpy()
    p1 = np.where(o_arr < d_arr, o_arr, d_arr)
    p2 = np.where(o_arr < d_arr, d_arr, o_arr)
    df['ruta_label'] = pd.Series(p1 + " ⇄ " + p2, index=df.index).astype('category')
    df['tramo_label'] = pd.Series(o_arr + " ➔ " + d_arr, index=df.index).astype('category')

    # Convertir columnas repetitivas a category para reducir la RAM en un 90%
    for c in ['aerolinea', 'origen_label', 'destino_label', 'periodo_orden', 'periodo_mes_es']:
        df[c] = df[c].astype('category')

    return df, None

# -------------------------------------------------------------
# INTERFAZ PRINCIPAL Y CARGA DE DATOS
# -------------------------------------------------------------
st.title("✈️ Monitor de Rutas Aéreas y Conectividad Argentina")
st.markdown("Herramienta de monitoreo basada en los microdatos oficiales de la **ANAC / SINTA**.")

# Búsqueda de archivo de datos
archivos_candidatos = [
    'conectividad_aerea.zip',
    'conectividad_aerea.csv.gz',
    'conectividad_aerea.csv',
    'datos_actualizados.csv',
    'datos_test_large.csv',
    'datos_sinta_ejemplo.csv',
    'test_raw.zip',
    'test_raw.csv'
]

archivo_encontrado = None
for arc in archivos_candidatos:
    if os.path.exists(arc) and os.path.getsize(arc) > 50:
        archivo_encontrado = arc
        break

uploaded_file = st.sidebar.file_uploader(
    "Cargar archivo (.zip, .csv.gz o .csv)",
    type=['zip', 'gz', 'csv'],
    help="Sube un archivo de microdatos de ANAC/SINTA. Se recomienda .zip para archivos grandes mayores a 25 MB."
)

if uploaded_file is not None:
    temp_path = f"temp_upload_{uploaded_file.name}"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    archivo_encontrado = temp_path
    fuente_activa = f"Archivo subido: `{uploaded_file.name}`"
elif archivo_encontrado:
    fuente_activa = f"Archivo local: `{archivo_encontrado}` ({os.path.getsize(archivo_encontrado) / (1024*1024):.1f} MB)"
else:
    st.error("⚠️ No se encontró ningún archivo de microdatos (`conectividad_aerea.zip` ni `.csv`).")
    st.info("Suba el archivo de datos desde el panel lateral para iniciar.")
    st.stop()

# Carga de datos con caché
with st.spinner("Cargando y procesando base oficial..."):
    df_raw, err = cargar_y_limpiar_datos(archivo_encontrado)

if err or df_raw is None or df_raw.empty:
    st.error(f"Error al procesar la base oficial: {err}")
    st.stop()

total_registros = len(df_raw)
f_min_total = df_raw['fecha'].min().date()
f_max_total = df_raw['fecha'].max().date()

st.success(
    f"🟢 **Fuente de Datos Activa:** {fuente_activa}  \n"
    f"📊 **Registros oficiales en memoria:** {fmt_entero(total_registros)} filas.  \n"
    f"📅 **Período con estadísticas disponibles:** desde el **{f_min_total.strftime('%d/%m/%Y')}** hasta el **{f_max_total.strftime('%d/%m/%Y')}**."
)

# -------------------------------------------------------------
# FILTROS DE BÚSQUEDA Y BOTÓN BUSCAR VUELOS
# -------------------------------------------------------------
st.subheader("🔍 Filtros de Búsqueda de Vuelos")

rutas_disponibles = sorted(df_raw['ruta_label'].dropna().unique().tolist())
origenes_disponibles = sorted(df_raw['origen_label'].dropna().unique().tolist())
destinos_disponibles = sorted(df_raw['destino_label'].dropna().unique().tolist())
aerolineas_disponibles = sorted(df_raw['aerolinea'].dropna().unique().tolist())

# Callback seguro para invertir Origen y Destino sin error de widget
def intercambiar_origen_destino():
    st.session_state['sel_origenes_key'], st.session_state['sel_destinos_key'] = (
        st.session_state.get('sel_destinos_key', []),
        st.session_state.get('sel_origenes_key', [])
    )
    if 'criterios_activos' in st.session_state:
        st.session_state['criterios_activos']['origenes'] = st.session_state['sel_origenes_key']
        st.session_state['criterios_activos']['destinos'] = st.session_state['sel_destinos_key']

# Control de estado de búsqueda inicial en CERO
if 'busqueda_activa' not in st.session_state:
    st.session_state['busqueda_activa'] = False
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
        'aerolineas': [],
        'desde': def_desde,
        'hasta': def_hasta,
        'todo_el_pais': False
    }

# 1. Selector de Ruta y Aerolínea
col_r1, col_r2 = st.columns([7, 5])
with col_r1:
    sel_rutas = st.multiselect(
        "🗺️ Ruta (Ida y Vuelta):",
        options=rutas_disponibles,
        default=st.session_state['criterios_activos'].get('rutas', []),
        help="Agrupa ambos sentidos de vuelo del corredor (ej. Aeroparque ⇄ Bariloche incluye tanto idas como vueltas)."
    )
with col_r2:
    sel_aerolineas = st.multiselect(
        "✈️ Aerolínea / Operador:",
        options=aerolineas_disponibles,
        default=st.session_state['criterios_activos'].get('aerolineas', []),
        help="Filtra por una o más aerolíneas específicas. Si lo dejas vacío, incluye todas."
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

# 3. Rango de Fechas y opción de mercado completo
col_d1, col_d2, col_d3 = st.columns([4, 4, 3])
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
with col_d3:
    st.write("")
    st.write("")
    chk_pais = st.checkbox("Analizar total país (todas las rutas)", value=st.session_state['criterios_activos'].get('todo_el_pais', False))

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
        'aerolineas': [],
        'desde': def_desde,
        'hasta': def_hasta,
        'todo_el_pais': False
    }
    st.session_state['busqueda_activa'] = False
    st.rerun()

# Actualizar criterios al pulsar Buscar Vuelos
if btn_buscar:
    tiene_criterios = bool(sel_rutas or st.session_state['sel_origenes_key'] or st.session_state['sel_destinos_key'] or sel_aerolineas or chk_pais)
    if tiene_criterios:
        st.session_state['criterios_activos'] = {
            'rutas': sel_rutas,
            'origenes': st.session_state['sel_origenes_key'],
            'destinos': st.session_state['sel_destinos_key'],
            'aerolineas': sel_aerolineas,
            'desde': f_desde,
            'hasta': f_hasta,
            'todo_el_pais': chk_pais
        }
        st.session_state['busqueda_activa'] = True
    else:
        st.session_state['busqueda_activa'] = False
        st.warning("⚠️ Seleccione una Ruta, Aeropuerto de Origen/Destino, Aerolínea (o marque 'Analizar total país') y pulse 'Buscar Vuelos'.")

# -------------------------------------------------------------
# ESTADO INICIAL EN CERO (SIN PESAR LA PÁGINA)
# -------------------------------------------------------------
st.markdown("---")
st.subheader("📌 Resumen Ejecutivo del Segmento Seleccionado")

if not st.session_state.get('busqueda_activa', False):
    # Todo en cero al ingresar por primera vez
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Pasajeros", "0")
    k2.metric("Vuelos", "0")
    k3.metric("Asientos", "0")
    k4.metric("Ocupación", "0,0%")
    k5.metric("Pax / Vuelo", "0,0")
    k6.metric("Concentración (HHI)", "-")

    st.info("💡 **El monitor está listo y en espera.** Seleccione una **Ruta**, **Origen y Destino** o **Aerolínea** en los filtros superiores y presione **🔍 Buscar Vuelos** para comenzar el análisis.")

    tab_g, tab_c, tab_e, tab_comp, tab_d = st.tabs([
        "📊 Gráficos Básicos",
        "📋 Cuadros de Datos",
        "📅 Estacionalidad",
        "⚖️ Comparación Interanual (YoY)",
        "📥 Descarga de Datos"
    ])
    with tab_g:
        st.info("Seleccione una ruta o tramo y presione 'Buscar Vuelos' para visualizar los gráficos de evolución, factor de ocupación y cuota de mercado.")
    with tab_c:
        st.info("Seleccione una ruta o tramo y presione 'Buscar Vuelos' para consultar las tablas tabuladas por aerolínea y mes.")
    with tab_e:
        st.info("Seleccione una ruta o tramo y presione 'Buscar Vuelos' para ver el comportamiento estacional y los índices de temporada.")
    with tab_comp:
        st.info("Seleccione una ruta o tramo y presione 'Buscar Vuelos' para comparar meses entre diferentes años y ver la absorción de mercado.")
    with tab_d:
        st.info("Seleccione una ruta o tramo y presione 'Buscar Vuelos' para descargar los microdatos y reportes del segmento.")
    st.stop()

# -------------------------------------------------------------
# EJECUCIÓN FILTRADA (INSTANTÁNEA)
# -------------------------------------------------------------
filtros = st.session_state['criterios_activos']
mascara = (df_raw['fecha'].dt.date >= filtros['desde']) & (df_raw['fecha'].dt.date <= filtros['hasta'])

if not filtros.get('todo_el_pais', False):
    if filtros.get('rutas'):
        mascara &= df_raw['ruta_label'].isin(filtros['rutas'])
    if filtros.get('origenes'):
        mascara &= df_raw['origen_label'].isin(filtros['origenes'])
    if filtros.get('destinos'):
        mascara &= df_raw['destino_label'].isin(filtros['destinos'])

if filtros.get('aerolineas'):
    mascara &= df_raw['aerolinea'].isin(filtros['aerolineas'])

df_filtrado = df_raw[mascara].copy()

if df_filtrado.empty:
    st.warning("⚠️ No se encontraron vuelos para los criterios seleccionados. Ajuste los filtros y pulse **Buscar Vuelos**.")
    st.stop()

# KPIs Reales del Segmento Filtrado
pax_total = df_filtrado['pasajeros'].sum()
vuelos_total = df_filtrado['vuelos'].sum()
asientos_total = df_filtrado['asientos'].sum()
factor_ocupacion = (pax_total / asientos_total * 100) if asientos_total > 0 else 0
pax_por_vuelo = (pax_total / vuelos_total) if vuelos_total > 0 else 0

# Cálculo del Índice HHI (Herfindahl-Hirschman Index)
cuotas_pax = df_filtrado.groupby('aerolinea', observed=True)['pasajeros'].sum()
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
tab_graficos, tab_cuadros, tab_estacionalidad, tab_comparador, tab_descargas = st.tabs([
    "📊 Gráficos Básicos",
    "📋 Cuadros de Datos",
    "📅 Estacionalidad",
    "⚖️ Comparación Interanual (YoY)",
    "📥 Descarga de Datos"
])

# =============================================================
# SECCIÓN 1: GRÁFICOS CON INFORMACIÓN BÁSICA (VERTICALES)
# =============================================================
with tab_graficos:
    st.markdown("### Métricas Visuales del Segmento Seleccionado")
    st.markdown("Todos los gráficos se muestran a ancho completo para una lectura clara de aerolíneas y períodos.")
    
    # 1. Pasajeros mensuales por aerolínea
    st.markdown("#### 1. Evolución Mensual de Pasajeros por Operador")
    df_mes_aero = df_filtrado.groupby(['periodo_orden', 'periodo_mes_es', 'aerolinea'], observed=True)['pasajeros'].sum().reset_index()
    df_mes_aero = df_mes_aero.sort_values(by=['periodo_orden', 'pasajeros'], ascending=[True, False])
    
    fig_bar = px.bar(
        df_mes_aero,
        x='periodo_mes_es',
        y='pasajeros',
        color='aerolinea',
        title="Pasajeros Mensuales Transportados por Aerolínea (Barras Apiladas)",
        labels={'periodo_mes_es': 'Período', 'pasajeros': 'Pasajeros'},
        barmode='stack'
    )
    fig_bar.update_layout(
        xaxis_tickangle=-45,
        legend_title_text='Aerolínea',
        height=480,
        margin=dict(l=20, r=20, t=50, b=40)
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")

    # 2. Factor de Ocupación mensual por aerolínea (Curva individual por cada aerolínea)
    st.markdown("#### 2. Factor de Ocupación (%) por Aerolínea Mes a Mes")
    df_mes_ocup = df_filtrado.groupby(['periodo_orden', 'periodo_mes_es', 'aerolinea'], observed=True).agg(
        pasajeros=('pasajeros', 'sum'),
        asientos=('asientos', 'sum')
    ).reset_index()
    
    # Filtrar solo aerolíneas que ofertaron asientos en el mes
    df_mes_ocup = df_mes_ocup[df_mes_ocup['asientos'] > 0].copy()
    df_mes_ocup['ocupacion_%'] = (df_mes_ocup['pasajeros'] / df_mes_ocup['asientos']) * 100
    df_mes_ocup = df_mes_ocup.sort_values(by=['periodo_orden', 'aerolinea'])

    if not df_mes_ocup.empty:
        fig_line = px.line(
            df_mes_ocup,
            x='periodo_mes_es',
            y='ocupacion_%',
            color='aerolinea',
            title="Evolución del Factor de Ocupación (%) por Operador (Curva individual por aerolínea)",
            labels={'periodo_mes_es': 'Período', 'ocupacion_%': 'Factor de Ocupación (%)', 'aerolinea': 'Aerolínea'},
            markers=True
        )
        fig_line.update_layout(
            yaxis_range=[0, 105],
            xaxis_tickangle=-45,
            legend_title_text='Aerolínea',
            height=480,
            margin=dict(l=20, r=20, t=50, b=40)
        )
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info("No se registran asientos ofertados para calcular el factor de ocupación en este segmento.")

    st.markdown("---")

    # 3. Market Share de Pasajeros
    st.markdown("#### 3. Participación de Mercado Acumulada (Market Share)")
    df_aero_pie = df_filtrado.groupby('aerolinea', observed=True)['pasajeros'].sum().reset_index()
    df_aero_pie = df_aero_pie[df_aero_pie['pasajeros'] > 0]
    if not df_aero_pie.empty:
        fig_pie = px.pie(
            df_aero_pie,
            names='aerolinea',
            values='pasajeros',
            title="Distribución de Pasajeros por Aerolínea en el Período",
            hole=0.42
        )
        fig_pie.update_layout(
            height=450,
            margin=dict(l=20, r=20, t=50, b=40)
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")

    # 4. Gráfico por Sentido de Vuelo (Ida vs Vuelta)
    st.markdown("#### 4. Pasajeros por Sentido de Vuelo (Ida vs. Vuelta)")
    df_tramo_graf = df_filtrado.groupby(['tramo_label', 'aerolinea'], observed=True)['pasajeros'].sum().reset_index()
    df_tramo_graf = df_tramo_graf[df_tramo_graf['pasajeros'] > 0]
    
    col_disp1, col_disp2 = st.columns([5, 7])
    with col_disp1:
        tipo_disposicion = st.radio(
            "Diseño de barras (Sentido de vuelo):",
            options=["Barras Apiladas (Pegadas por tramo)", "Barras Agrupadas (Lado a lado)"],
            horizontal=True,
            key="disp_barras_sentido"
        )
    modo_bar = 'stack' if "Apiladas" in tipo_disposicion else 'group'

    fig_tramo = px.bar(
        df_tramo_graf,
        x='tramo_label',
        y='pasajeros',
        color='aerolinea',
        title="Pasajeros Transportados por Sentido del Corredor",
        labels={'tramo_label': 'Tramo Operado', 'pasajeros': 'Pasajeros'},
        barmode=modo_bar
    )
    fig_tramo.update_layout(
        xaxis_tickangle=-20,
        bargap=0.15,
        bargroupgap=0.0,
        legend_title_text='Aerolínea',
        height=480,
        margin=dict(l=20, r=20, t=50, b=40)
    )
    st.plotly_chart(fig_tramo, use_container_width=True)

# =============================================================
# SECCIÓN 2: CUADROS CON INFORMACIÓN BÁSICA
# =============================================================
with tab_cuadros:
    st.markdown("### Cuadros Estadísticos y Tabulaciones Oficiales")

    # Cuadro 1: Desempeño por Aerolínea
    st.subheader("1. Desempeño Operativo y Comercial por Aerolínea")
    df_aero = df_filtrado.groupby('aerolinea', observed=True).agg(
        Pasajeros=('pasajeros', 'sum'),
        Vuelos=('vuelos', 'sum'),
        Asientos=('asientos', 'sum')
    ).reset_index()

    df_aero = df_aero[df_aero['Vuelos'] > 0].sort_values(by='Pasajeros', ascending=False)
    total_pax_seg = df_aero['Pasajeros'].sum()
    df_aero['Market Share'] = np.where(total_pax_seg > 0, (df_aero['Pasajeros'] / total_pax_seg) * 100, 0)
    df_aero['Factor Ocupación'] = np.where(df_aero['Asientos'] > 0, (df_aero['Pasajeros'] / df_aero['Asientos']) * 100, 0)
    df_aero['Pax / Vuelo'] = np.where(df_aero['Vuelos'] > 0, df_aero['Pasajeros'] / df_aero['Vuelos'], 0)

    # Formatear tabla
    df_aero_disp = df_aero.copy()
    df_aero_disp['Pasajeros'] = df_aero_disp['Pasajeros'].apply(fmt_entero)
    df_aero_disp['Vuelos'] = df_aero_disp['Vuelos'].apply(fmt_entero)
    df_aero_disp['Asientos'] = df_aero_disp['Asientos'].apply(fmt_entero)
    df_aero_disp['Market Share'] = df_aero_disp['Market Share'].apply(fmt_porcentaje)
    df_aero_disp['Factor Ocupación'] = df_aero_disp['Factor Ocupación'].apply(fmt_porcentaje)
    df_aero_disp['Pax / Vuelo'] = df_aero_disp['Pax / Vuelo'].apply(fmt_decimal)

    st.dataframe(df_aero_disp.rename(columns={'aerolinea': 'Aerolínea'}), use_container_width=True, hide_index=True)

    # Cuadro 2: Desempeño por Sentido de Vuelo
    st.subheader("2. Desempeño por Sentido de Vuelo (Tramo)")
    df_tramo = df_filtrado.groupby(['tramo_label', 'aerolinea'], observed=True).agg(
        Pasajeros=('pasajeros', 'sum'),
        Vuelos=('vuelos', 'sum'),
        Asientos=('asientos', 'sum')
    ).reset_index()
    df_tramo = df_tramo[df_tramo['Vuelos'] > 0].sort_values(by=['tramo_label', 'Pasajeros'], ascending=[True, False])
    df_tramo['Ocupación'] = np.where(df_tramo['Asientos'] > 0, (df_tramo['Pasajeros'] / df_tramo['Asientos']) * 100, 0)
    df_tramo['Pax/Vuelo'] = np.where(df_tramo['Vuelos'] > 0, df_tramo['Pasajeros'] / df_tramo['Vuelos'], 0)

    df_t_disp = df_tramo.copy()
    df_t_disp['Pasajeros'] = df_t_disp['Pasajeros'].apply(fmt_entero)
    df_t_disp['Vuelos'] = df_t_disp['Vuelos'].apply(fmt_entero)
    df_t_disp['Asientos'] = df_t_disp['Asientos'].apply(fmt_entero)
    df_t_disp['Ocupación'] = df_t_disp['Ocupación'].apply(fmt_porcentaje)
    df_t_disp['Pax/Vuelo'] = df_t_disp['Pax/Vuelo'].apply(fmt_decimal)

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

    pivot_pax_fmt = pivot_pax_con_total.map(fmt_entero) if hasattr(pivot_pax_con_total, "map") else pivot_pax_con_total.applymap(fmt_entero)
    st.dataframe(pivot_pax_fmt, use_container_width=True)
