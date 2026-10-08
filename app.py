import os
import io
import re
import calendar
import zipfile
import warnings
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px

import plotly.graph_objects as go
import plotly.io as pio

warnings.filterwarnings("ignore")

# Paleta y plantilla visual unificada para todos los gráficos
PALETA = ["#1d4ed8", "#0ea5e9", "#f59e0b", "#10b981", "#8b5cf6",
          "#ef4444", "#14b8a6", "#ec4899", "#64748b", "#84cc16"]
pio.templates["monitor"] = go.layout.Template(
    layout=dict(
        colorway=PALETA,
        font=dict(family="Inter, Segoe UI, system-ui, sans-serif", size=13, color="#334155"),
        title=dict(font=dict(size=15, color="#0f172a"), x=0.0, xanchor="left"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, linecolor="#cbd5e1", ticks="outside", tickcolor="#cbd5e1"),
        yaxis=dict(gridcolor="#e2e8f0", zeroline=False, linecolor="rgba(0,0,0,0)"),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor="#0f172a", font_color="#ffffff", bordercolor="#0f172a"),
    )
)
pio.templates.default = "monitor"

# Configuración de interfaz
st.set_page_config(
    page_title="Monitor de Conectividad y Rutas Aéreas ANAC",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
.block-container { padding-top: 2rem; padding-bottom: 4rem; max-width: 1280px; }
header[data-testid="stHeader"] { background: transparent; }
h1, h2, h3, h4 { letter-spacing: -0.01em; color: #0f172a; }
h3 { margin-top: .5rem; }
hr { margin: 1.8rem 0; border-color: #e2e8f0; }

/* Cabecera */
.hero {
    background: linear-gradient(120deg, #0b1f4d 0%, #1d4ed8 60%, #0ea5e9 100%);
    border-radius: 18px; padding: 2rem 2.2rem; margin-bottom: 1.4rem; color: #fff;
    box-shadow: 0 10px 30px rgba(29, 78, 216, .25);
}
.hero h1 { color: #fff; font-size: 2rem; margin: 0 0 .3rem 0; padding: 0; }
.hero p { color: rgba(255,255,255,.85); margin: 0; font-size: 1rem; }
.chips { margin-top: 1rem; display: flex; flex-wrap: wrap; gap: .5rem; }
.chip {
    background: rgba(255,255,255,.16); border: 1px solid rgba(255,255,255,.28);
    border-radius: 999px; padding: .25rem .8rem; font-size: .82rem; color: #fff;
}

/* Tarjetas de métricas */
div[data-testid="stMetric"] {
    background: #fff; border: 1px solid #e2e8f0; border-radius: 14px;
    padding: .9rem 1rem; box-shadow: 0 1px 3px rgba(15, 23, 42, .06);
}
div[data-testid="stMetricLabel"] p { color: #64748b; font-size: .8rem; text-transform: uppercase; letter-spacing: .04em; }
div[data-testid="stMetricValue"] { color: #0f172a; font-weight: 700; }

/* Pestañas */
button[data-baseweb="tab"] { font-weight: 600; padding: .7rem 1rem; }
div[data-baseweb="tab-list"] { gap: .25rem; border-bottom: 1px solid #e2e8f0; }

/* Botones, inputs, tablas y gráficos */
.stButton > button { border-radius: 10px; font-weight: 600; }
div[data-baseweb="select"] > div, div[data-baseweb="input"] > div { border-radius: 10px; }
div[data-testid="stDataFrame"], div[data-testid="stPlotlyChart"] {
    background: #fff; border: 1px solid #e2e8f0; border-radius: 14px; padding: .4rem;
}
div[data-testid="stAlert"] { border-radius: 12px; }
section[data-testid="stSidebar"] { background: #fff; border-right: 1px solid #e2e8f0; }
.insight {
    background: #eff6ff; border: 1px solid #bfdbfe; color: #1e3a8a; border-radius: 12px;
    padding: .7rem 1rem; margin: .4rem 0 1rem 0; font-size: .95rem;
}
@media (max-width: 640px) {
    .block-container { padding-left: 1rem; padding-right: 1rem; padding-top: 1rem; }
    .hero { padding: 1.2rem 1.1rem; border-radius: 14px; }
    .hero h1 { font-size: 1.35rem; }
    .hero p { font-size: .88rem; }
    div[data-testid="stMetricValue"] { font-size: 1.5rem; }
    div[data-testid="stHorizontalBlock"]:has(div[data-testid="stMetric"]) { flex-wrap: wrap; gap: .6rem; }
    div[data-testid="stHorizontalBlock"]:has(div[data-testid="stMetric"]) > div[data-testid="stColumn"] {
        min-width: calc(50% - .6rem); flex: 1 1 calc(50% - .6rem);
    }
    button[data-baseweb="tab"] { padding: .5rem .6rem; font-size: .85rem; }
}
#MainMenu, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

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
    'CPC': {'codigo': 'CPC', 'ciudad': 'San Martín de los Andes', 'keywords': ['SAN MARTIN DE LOS ANDES', 'CHAPELCO', 'CARLOS CAMPOS', 'AVIADOR C CAMPOS', 'CPC']},
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

def normalizar_texto_aeropuerto(texto):
    if not isinstance(texto, str):
        return ""
    txt = texto.upper().strip()
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

    for iata, datos in AEROPUERTOS_EXHAUSTIVO.items():
        if re.search(r'\b' + re.escape(iata) + r'\b', norm):
            return datos['codigo'], datos['ciudad']

    # Se elige la ciudad con mejor puntaje: nombre de la ciudad (1ª palabra clave) pesa más que el resto
    mejor, mejor_puntaje = None, 0
    for iata, datos in AEROPUERTOS_EXHAUSTIVO.items():
        puntaje = 0
        for n_kw, kw in enumerate(datos['keywords']):
            kw_norm = normalizar_texto_aeropuerto(kw)
            if kw_norm and re.search(r'\b' + re.escape(kw_norm) + r'\b', norm):
                puntaje += 100 if n_kw == 0 else 1
        if puntaje > mejor_puntaje:
            mejor, mejor_puntaje = datos, puntaje
    if mejor is not None:
        return mejor['codigo'], mejor['ciudad']

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

    if sigla_fallback in ['AER', 'INT']:
        sigla_fallback = "OTR"

    return sigla_fallback, ciudad_cand

def construir_etiqueta_aeropuerto(nombre_aeropuerto):
    sigla, ciudad = obtener_sigla_y_ciudad(nombre_aeropuerto)
    return f"{sigla} ({ciudad})"

# Formateadores numéricos
fmt_entero = lambda x: f"{int(round(x)):,}".replace(",", ".")
fmt_decimal = lambda x: f"{x:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
fmt_porcentaje = lambda x: "s/d" if pd.isna(x) else f"{x:.1f}%".replace(".", ",")

# Aeropuertos del Área Metropolitana de Buenos Aires (para medir conectividad federal)
AMBA_SIGLAS = {'AEP', 'EZE', 'EPA', 'MOR', 'FDO'}

def dias_operados(df):
    """Cantidad de días cubiertos por los datos (base diaria) o días calendario de cada mes (base mensual)."""
    total = 0
    for po, n in df.groupby('periodo_orden', observed=True)['fecha'].nunique().items():
        if n > 1:
            total += int(n)
        else:
            y, m = map(int, str(po).split('-'))
            total += calendar.monthrange(y, m)[1]
    return max(total, 1)

def restar_ano(f):
    try:
        return f.replace(year=f.year - 1)
    except ValueError:
        return f.replace(year=f.year - 1, day=28)

def filtrar_segmento(df, filtros, desde, hasta):
    """Aplica los filtros activos de ruta/aeropuertos/aerolínea y un rango de fechas."""
    m = (df['fecha'].dt.date >= desde) & (df['fecha'].dt.date <= hasta)
    if not filtros.get('todo_el_pais', False):
        if filtros.get('rutas'):
            m &= df['ruta_label'].isin(filtros['rutas'])
        if filtros.get('origenes'):
            m &= df['origen_label'].isin(filtros['origenes'])
        if filtros.get('destinos'):
            m &= df['destino_label'].isin(filtros['destinos'])
    if filtros.get('aerolineas'):
        m &= df['aerolinea'].isin(filtros['aerolineas'])
    return df[m]

def config_numerica(df, porcentajes=(), deltas=(), deltas_pts=()):
    """column_config para mostrar números ordenables (sin convertirlos a texto)."""
    cfg = {}
    for c in df.columns:
        if not pd.api.types.is_numeric_dtype(df[c]):
            continue
        if str(c).startswith('Δ%'):
            fmt = "%+.1f%%"
        elif c in porcentajes:
            fmt = "%.1f%%"
        elif c in deltas:
            fmt = "%+d"
        elif c in deltas_pts:
            fmt = "%+.1f pts"
        else:
            fmt = "localized"
        cfg[c] = st.column_config.NumberColumn(c, format=fmt)
    return cfg

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
    return meses_map.get(s[:3], 1)

def parsear_dia(val):
    if val is None or pd.isna(val):
        return 1
    s = str(val).strip()
    try:
        n = int(float(s))
        return max(1, min(n, 31))
    except Exception:
        return 1

def sanitizar_fecha(val, default_val, min_val, max_val):
    if isinstance(val, (tuple, list)):
        val = val[0] if len(val) > 0 else default_val
    if isinstance(val, pd.Timestamp):
        val = val.date()
    elif isinstance(val, datetime):
        val = val.date()
    elif isinstance(val, str):
        try:
            val = datetime.strptime(val[:10], '%Y-%m-%d').date()
        except Exception:
            val = default_val
    elif not isinstance(val, date):
        val = default_val

    if val < min_val:
        return min_val
    if val > max_val:
        return max_val
    return val

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
    m = re.search(r'(19\d{2}|20\d{2})', s)
    if m:
        return int(m.group(1))
    return None

def limpiar_mojibake_texto(val):
    if not isinstance(val, str):
        return val
    txt = val
    reemplazos = {
        'Ã¡': 'á', 'Ã©': 'é', 'Ã­': 'í', 'Ã³': 'ó', 'Ãº': 'ú',
        'Ã': 'Á', 'Ã‰': 'É', 'Ã': 'Í', 'Ã“': 'Ó', 'Ãš': 'Ú',
        'Ã±': 'ñ', 'Ã‘': 'Ñ'
    }
    for k, v in reemplazos.items():
        txt = txt.replace(k, v)
    return txt.strip()

# -------------------------------------------------------------
# DETECCIÓN Y PROCESAMIENTO ESTRICTO DE DATOS REALES (OPTIMIZADO EN RAM)
# -------------------------------------------------------------
@st.cache_data(show_spinner=False)
def procesar_dataframe_oficial(df_in):
    if df_in is None or df_in.empty:
        return None, "El archivo proporcionado está vacío."

    df = df_in.copy()
    
    col_map = {}
    for c in df.columns:
        norm = limpiar_encabezado(c)
        if any(k in norm for k in ['ANO', 'ANIO', 'YEAR']) or norm == 'A':
            col_map[c] = 'ano_raw'
        elif 'MES' in norm or 'MONTH' in norm:
            col_map[c] = 'mes_raw'
        elif 'DIA' in norm or 'DAY' in norm or norm == 'D':
            col_map[c] = 'dia_raw'
        elif any(k in norm for k in ['FECHA', 'DATE', 'INDICE TIEMPO', 'TIEMPO', 'PERIODO']):
            col_map[c] = 'fecha_raw'
        elif 'ORIGEN' in norm or 'ORIG' in norm or 'DESDE' in norm:
            col_map[c] = 'origen_raw'
        elif 'DESTINO' in norm or 'DEST' in norm or 'HACIA' in norm:
            col_map[c] = 'destino_raw'
        elif any(k in norm for k in ['EMPRESA', 'AEROLINEA', 'OPERADOR', 'LINEA', 'COMPANIA']):
            col_map[c] = 'aerolinea_raw'
        elif 'PASAJERO' in norm or 'PAX' in norm:
            col_map[c] = 'pasajeros_raw'
        elif 'VUELO' in norm or 'FLIGHT' in norm or 'ETAPA' in norm or 'OPERACION' in norm or 'MOVIMIENTO' in norm:
            col_map[c] = 'vuelos_raw'
        elif 'ASIENTO' in norm or 'SEAT' in norm or 'CAPACIDAD' in norm or 'PLAZA' in norm:
            col_map[c] = 'asientos_raw'

    df.rename(columns=col_map, inplace=True)

    if 'origen_raw' not in df.columns or 'destino_raw' not in df.columns:
        return None, "El archivo debe contener columnas que indiquen el origen y destino de cada vuelo."

    # Aerolínea
    if 'aerolinea_raw' in df.columns:
        df['aerolinea'] = df['aerolinea_raw'].astype(str).apply(limpiar_mojibake_texto).replace({'nan': 'Otras Aerolíneas', '': 'Otras Aerolíneas'})
    else:
        df['aerolinea'] = 'Línea Regular'

    # Métricas numéricas con tipos compactos
    for col_met, col_dest, col_type in [
        ('pasajeros_raw', 'pasajeros', np.int32),
        ('vuelos_raw', 'vuelos', np.int16),
        ('asientos_raw', 'asientos', np.int32)
    ]:
        if col_met in df.columns:
            s_clean = df[col_met].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).str.strip()
            df[col_dest] = pd.to_numeric(s_clean, errors='coerce').fillna(0).astype(col_type)
        else:
            df[col_dest] = col_type(0)

    # Construcción robusta de Fechas (evitando epoch 1970 por enteros o números)
    fechas = pd.Series(pd.NaT, index=df.index)

    if 'fecha_raw' in df.columns:
        s = df['fecha_raw']
        if pd.api.types.is_numeric_dtype(s):
            s_str = s.fillna(0).astype(np.int64).astype(str).str.strip()
            # YYYYMMDD (8 dígitos, ej: 20170101)
            m8 = s_str.str.match(r'^(19\d\d|20\d\d)(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])$')
            if m8.any():
                f8 = pd.to_datetime(s_str.where(m8), format='%Y%m%d', errors='coerce')
                fechas = fechas.combine_first(f8)
            # YYYYMM (6 dígitos, ej: 201701)
            m6 = s_str.str.match(r'^(19\d\d|20\d\d)(0[1-9]|1[0-2])$')
            if m6.any():
                f6 = pd.to_datetime(s_str.where(m6) + '01', format='%Y%m%d', errors='coerce')
                fechas = fechas.combine_first(f6)
        else:
            s_str = s.astype(str).str.strip().str.replace('.0', '', regex=False)
            f_iso = pd.to_datetime(s_str, format='%Y-%m-%d', errors='coerce')
            fechas = fechas.combine_first(f_iso)

            f_dmy = pd.to_datetime(s_str, format='%d/%m/%Y', errors='coerce')
            fechas = fechas.combine_first(f_dmy)

            m8 = s_str.str.match(r'^(19\d\d|20\d\d)(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])$')
            if m8.any():
                f8 = pd.to_datetime(s_str.where(m8), format='%Y%m%d', errors='coerce')
                fechas = fechas.combine_first(f8)

            m6 = s_str.str.match(r'^(19\d\d|20\d\d)(0[1-9]|1[0-2])$')
            if m6.any():
                f6 = pd.to_datetime(s_str.where(m6) + '01', format='%Y%m%d', errors='coerce')
                fechas = fechas.combine_first(f6)

            f_gen = pd.to_datetime(s_str, errors='coerce', dayfirst=True)
            f_gen = f_gen.where(f_gen.dt.year >= 2000)
            fechas = fechas.combine_first(f_gen)

    # Filtrar estrictamente fechas erróneas (como 1970 por timestamp de época)
    fechas = fechas.where(fechas.dt.year >= 2000)

    # Si todavía faltan fechas y existen columnas de año y mes:
    if (fechas.isna().any() or len(fechas.dropna()) == 0) and 'ano_raw' in df.columns and 'mes_raw' in df.columns:
        anos = df['ano_raw'].apply(parsear_ano)
        meses = df['mes_raw'].apply(parsear_mes)
        dias = df['dia_raw'].apply(parsear_dia) if 'dia_raw' in df.columns else pd.Series(1, index=df.index)

        def armar_fecha(y, m, d):
            if pd.isna(y) or y is None:
                return pd.NaT
            try:
                return datetime(int(y), int(m), int(d))
            except ValueError:
                try:
                    return datetime(int(y), int(m), 28)
                except Exception:
                    return pd.NaT

        fechas_fb = pd.Series([armar_fecha(y, m, d) for y, m, d in zip(anos, meses, dias)], index=df.index)
        fechas = fechas.combine_first(fechas_fb)

    df['fecha'] = fechas
    df = df[df['fecha'].notna() & (df['fecha'].dt.year >= 2000)].copy()
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

    cols_finales = [
        'fecha', 'ano_num', 'mes_num', 'periodo_orden', 'periodo_mes_es',
        'aerolinea', 'origen_label', 'destino_label', 'ruta_label', 'tramo_label',
        'pasajeros', 'vuelos', 'asientos'
    ]
    return df[cols_finales], None

def cargar_archivo_en_memoria(archivo_bytes_o_path):
    try:
        es_zip = False
        if isinstance(archivo_bytes_o_path, str) and archivo_bytes_o_path.lower().endswith('.zip'):
            es_zip = True
        elif not isinstance(archivo_bytes_o_path, str):
            archivo_bytes_o_path.seek(0)
            magic = archivo_bytes_o_path.read(4)
            archivo_bytes_o_path.seek(0)
            if magic == b'PK\x03\x04':
                es_zip = True

        if es_zip:
            with zipfile.ZipFile(archivo_bytes_o_path) as z:
                csv_names = [n for n in z.namelist() if n.lower().endswith(('.csv', '.txt')) and not n.startswith('__MACOSX')]
                if not csv_names:
                    csv_names = [n for n in z.namelist() if not n.startswith('__MACOSX') and not n.endswith('/')]
                if csv_names:
                    with z.open(csv_names[0]) as zf:
                        contenido_bytes = io.BytesIO(zf.read())
                        return cargar_archivo_en_memoria(contenido_bytes)
    except Exception:
        pass

    try:
        es_gz = False
        if isinstance(archivo_bytes_o_path, str) and archivo_bytes_o_path.lower().endswith('.gz'):
            es_gz = True
        elif not isinstance(archivo_bytes_o_path, str):
            archivo_bytes_o_path.seek(0)
            magic = archivo_bytes_o_path.read(2)
            archivo_bytes_o_path.seek(0)
            if magic == b'\x1f\x8b':
                es_gz = True
        if es_gz:
            import gzip
            with gzip.open(archivo_bytes_o_path, 'rb') as gz_f:
                contenido_bytes = io.BytesIO(gz_f.read())
                return cargar_archivo_en_memoria(contenido_bytes)
    except Exception:
        pass

    encodings = ['utf-8-sig', 'utf-8', 'latin1', 'iso-8859-1', 'cp1252']
    separadores = [',', ';', '\t']

    for enc in encodings:
        for sep in separadores:
            try:
                if isinstance(archivo_bytes_o_path, str):
                    df = pd.read_csv(archivo_bytes_o_path, sep=sep, encoding=enc, nrows=50)
                else:
                    archivo_bytes_o_path.seek(0)
                    df = pd.read_csv(archivo_bytes_o_path, sep=sep, encoding=enc, nrows=50)

                if len(df.columns) >= 3:
                    if isinstance(archivo_bytes_o_path, str):
                        df_completo = pd.read_csv(archivo_bytes_o_path, sep=sep, encoding=enc, low_memory=False)
                    else:
                        archivo_bytes_o_path.seek(0)
                        df_completo = pd.read_csv(archivo_bytes_o_path, sep=sep, encoding=enc, low_memory=False)
                    return df_completo, None
            except Exception:
                continue

    return None, "No se pudo interpretar el archivo (CSV/ZIP/GZ) con las codificaciones habituales."

# -------------------------------------------------------------
# BARRA LATERAL: FUENTES DE DATOS
# -------------------------------------------------------------
st.sidebar.title("✈️ Conectividad Aérea")
st.sidebar.markdown("**Monitor Oficial de Vuelos de Cabotaje**")
st.sidebar.markdown("---")

df_raw = None
fuente_activa = None

subido = st.sidebar.file_uploader(
    "📂 Cargar microdatos (CSV o ZIP oficial)",
    type=['csv', 'zip', 'gz', 'txt', 'parquet'],
    help="Suba la base oficial descargada de ANAC o comprimida en ZIP."
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
        "conectividad_aerea.zip",
        "conectividad_aerea.csv.gz",
        "conectividad_aerea.csv",
        "conectividad-aerea.zip",
        "conectividad-aerea.csv",
        "data/conectividad_aerea.zip",
        "data/conectividad_aerea.csv",
        "datos/conectividad_aerea.zip",
        "datos/conectividad_aerea.csv",
        "base_anac.zip",
        "base_anac.csv",
        "cabotaje.zip",
        "cabotaje.csv"
    ]
    try:
        for f in os.listdir('.'):
            if f.lower().endswith(('.zip', '.gz', '.csv')) and f not in posibles_rutas:
                posibles_rutas.append(f)
    except Exception:
        pass

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
st.markdown(
    '<div class="hero">'
    '<h1>✈️ Monitor de Rutas Aéreas y Tráfico de Cabotaje</h1>'
    '<p>Análisis basado únicamente en estadísticas oficiales: ANAC y Secretaría de Turismo y Transporte.</p>'
    '</div>',
    unsafe_allow_html=True
)

if df_raw is None or df_raw.empty:
    st.error(
        "⛔ **NO HAY DATOS REALES CARGADOS O VÁLIDOS**  \n\n"
        "Esta aplicación tiene **estrictamente prohibido generar, simular o inventar datos**.  \n"
        "Para visualizar información, realice una de las siguientes acciones:  \n"
        "1. Asegúrese de que el archivo oficial `conectividad_aerea.zip` o `conectividad_aerea.csv` esté en la raíz del repositorio de GitHub.  \n"
        "2. O bien, suba el archivo oficial (.csv o .zip) en el menú lateral izquierdo."
    )
    st.info("ℹ️ Una vez cargado el archivo oficial con columnas de fecha, aerolínea, origen, destino, pasajeros y vuelos, se habilitará el monitor.")
    st.stop()

# Si hay datos reales cargados:
f_min_total = df_raw['fecha'].min().date()
f_max_total = df_raw['fecha'].max().date()
total_registros = len(df_raw)

st.markdown(
    '<div class="chips" style="margin:-.4rem 0 1.2rem 0;">'
    f'<span class="chip" style="background:#e0f2fe;color:#0c4a6e;border-color:#bae6fd;">🟢 {fuente_activa}</span>'
    f'<span class="chip" style="background:#e0f2fe;color:#0c4a6e;border-color:#bae6fd;">📊 {fmt_entero(total_registros)} registros</span>'
    f'<span class="chip" style="background:#e0f2fe;color:#0c4a6e;border-color:#bae6fd;">📅 {f_min_total.strftime("%d/%m/%Y")} → {f_max_total.strftime("%d/%m/%Y")}</span>'
    '</div>',
    unsafe_allow_html=True
)

# -------------------------------------------------------------
# FILTROS DE BÚSQUEDA Y BOTÓN BUSCAR VUELOS
# -------------------------------------------------------------

rutas_disponibles = sorted(df_raw['ruta_label'].dropna().unique().tolist())
origenes_disponibles = sorted(df_raw['origen_label'].dropna().unique().tolist())
destinos_disponibles = sorted(df_raw['destino_label'].dropna().unique().tolist())
aerolineas_disponibles = sorted(df_raw['aerolinea'].dropna().unique().tolist())

def intercambiar_origen_destino():
    st.session_state['sel_origenes_key'], st.session_state['sel_destinos_key'] = (
        st.session_state.get('sel_destinos_key', []),
        st.session_state.get('sel_origenes_key', [])
    )
    if 'criterios_activos' in st.session_state:
        st.session_state['criterios_activos']['origenes'] = st.session_state['sel_origenes_key']
        st.session_state['criterios_activos']['destinos'] = st.session_state['sel_destinos_key']

if 'busqueda_activa' not in st.session_state:
    st.session_state['busqueda_activa'] = False
if 'sel_origenes_key' not in st.session_state:
    st.session_state['sel_origenes_key'] = []
if 'sel_destinos_key' not in st.session_state:
    st.session_state['sel_destinos_key'] = []

def_desde = max(f_min_total, date(f_max_total.year, 1, 1)) if f_min_total <= date(f_max_total.year, 1, 1) <= f_max_total else f_min_total
def_hasta = f_max_total

if 'criterios_activos' not in st.session_state or not isinstance(st.session_state['criterios_activos'], dict):
    st.session_state['criterios_activos'] = {
        'rutas': [],
        'origenes': [],
        'destinos': [],
        'aerolineas': [],
        'desde': def_desde,
        'hasta': def_hasta,
        'todo_el_pais': False
    }
else:
    st.session_state['criterios_activos']['desde'] = sanitizar_fecha(
        st.session_state['criterios_activos'].get('desde'), def_desde, f_min_total, f_max_total
    )
    st.session_state['criterios_activos']['hasta'] = sanitizar_fecha(
        st.session_state['criterios_activos'].get('hasta'), def_hasta, f_min_total, f_max_total
    )

# --- Panel de filtros ---
with st.container(border=True):
    col_t1, col_t2 = st.columns([6, 4], vertical_alignment="center")
    with col_t1:
        st.markdown("#### 🔍 Filtros de búsqueda")
    with col_t2:
        chk_pais = st.toggle(
            "Analizar total país (todas las rutas)",
            value=st.session_state['criterios_activos'].get('todo_el_pais', False),
            help="Ignora los filtros de ruta y aeropuertos y analiza todo el cabotaje. La aerolínea y las fechas siguen aplicando."
        )

    # 1. Ruta y aerolínea
    col_r1, col_r2 = st.columns([7, 5])
    with col_r1:
        sel_rutas = st.multiselect(
            "Ruta (ida y vuelta)",
            options=rutas_disponibles,
            default=st.session_state['criterios_activos'].get('rutas', []),
            placeholder="Elegí uno o más corredores",
            disabled=chk_pais,
            help="Agrupa ambos sentidos de vuelo del corredor (ej. Aeroparque ⇄ Bariloche incluye idas y vueltas)."
        )
    with col_r2:
        sel_aerolineas = st.multiselect(
            "Aerolínea / operador",
            options=aerolineas_disponibles,
            default=st.session_state['criterios_activos'].get('aerolineas', []),
            placeholder="Todas",
            help="Si lo dejás vacío, incluye todas las aerolíneas."
        )

    # 2. Origen ⇄ Destino
    col_orig, col_inv, col_dest = st.columns([10, 2, 10], vertical_alignment="bottom")
    with col_orig:
        sel_origenes = st.multiselect(
            "🛫 Origen",
            options=origenes_disponibles,
            key='sel_origenes_key',
            placeholder="Aeropuerto de salida",
            disabled=chk_pais,
            help="Filtra los despegues desde este aeropuerto."
        )
    with col_inv:
        st.button("⇄", on_click=intercambiar_origen_destino, use_container_width=True,
                  disabled=chk_pais, help="Invertir origen y destino")
    with col_dest:
        sel_destinos = st.multiselect(
            "🛬 Destino",
            options=destinos_disponibles,
            key='sel_destinos_key',
            placeholder="Aeropuerto de llegada",
            disabled=chk_pais,
            help="Filtra los aterrizajes en este aeropuerto."
        )

    # 3. Período
    val_desde_input = sanitizar_fecha(st.session_state['criterios_activos'].get('desde'), def_desde, f_min_total, f_max_total)
    val_hasta_input = sanitizar_fecha(st.session_state['criterios_activos'].get('hasta'), def_hasta, f_min_total, f_max_total)
    col_d1, col_d2, col_b1, col_b2 = st.columns([3, 3, 3, 3], vertical_alignment="bottom")
    with col_d1:
        f_desde = st.date_input(
            "📅 Desde", value=val_desde_input, min_value=f_min_total, max_value=f_max_total,
            format="DD/MM/YYYY",
            help=f"Base disponible: {f_min_total.strftime('%d/%m/%Y')} a {f_max_total.strftime('%d/%m/%Y')}."
        )
    with col_d2:
        f_hasta = st.date_input(
            "📅 Hasta", value=val_hasta_input, min_value=f_min_total, max_value=f_max_total,
            format="DD/MM/YYYY",
            help=f"Base disponible: {f_min_total.strftime('%d/%m/%Y')} a {f_max_total.strftime('%d/%m/%Y')}."
        )
    f_desde = sanitizar_fecha(f_desde, def_desde, f_min_total, f_max_total)
    f_hasta = sanitizar_fecha(f_hasta, def_hasta, f_min_total, f_max_total)

    # 4. Acciones
    with col_b1:
        btn_buscar = st.button("🔍 Buscar vuelos", type="primary", use_container_width=True)
    with col_b2:
        btn_reset = st.button("↺ Restablecer", use_container_width=True)

    if f_desde > f_hasta:
        st.warning("La fecha inicial es posterior a la final: ajustá el período.")


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

if btn_buscar:
    tiene_criterios = bool(sel_rutas or st.session_state['sel_origenes_key'] or st.session_state['sel_destinos_key'] or sel_aerolineas or chk_pais)
    if tiene_criterios:
        st.session_state['criterios_activos'] = {
            'rutas': sel_rutas,
            'origenes': st.session_state['sel_origenes_key'],
            'destinos': st.session_state['sel_destinos_key'],
            'aerolineas': sel_aerolineas,
            'desde': sanitizar_fecha(f_desde, def_desde, f_min_total, f_max_total),
            'hasta': sanitizar_fecha(f_hasta, def_hasta, f_min_total, f_max_total),
            'todo_el_pais': chk_pais
        }
        st.session_state['busqueda_activa'] = True
    else:
        st.session_state['busqueda_activa'] = False
        st.warning("⚠️ Seleccione una Ruta, Aeropuerto de Origen/Destino, Aerolínea (o marque 'Analizar total país') y pulse 'Buscar vuelos'.")

# -------------------------------------------------------------
# ESTADO INICIAL EN CERO (SIN PESAR LA PÁGINA)
# -------------------------------------------------------------
st.markdown("---")
st.subheader("📌 Resumen Ejecutivo del Segmento Seleccionado")

if not st.session_state.get('busqueda_activa', False):
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Pasajeros", "0")
    k2.metric("Vuelos", "0")
    k3.metric("Asientos", "0")
    k4.metric("Ocupación", "0,0%")
    k5.metric("Pax / Vuelo", "0,0")
    k6.metric("Concentración (HHI)", "-")

    st.info("💡 **El monitor está listo y en espera.** Seleccione una **Ruta**, **Origen y Destino** o **Aerolínea** en los filtros superiores y presione **🔍 Buscar vuelos** para comenzar el análisis.")

    tab_g, tab_c, tab_r, tab_e, tab_d = st.tabs([
        "📊 Panorama",
        "⚖️ Competencia",
        "🗺️ Rutas y sentidos",
        "📅 Estacionalidad",
        "📋 Datos y descargas"
    ])
    with tab_g:
        st.info("Seleccione una ruta o tramo y presione 'Buscar vuelos' para visualizar la evolución de oferta, demanda y ocupación.")
    with tab_c:
        st.info("Seleccione una ruta o tramo y presione 'Buscar vuelos' para ver cuotas de mercado y comparación interanual por aerolínea.")
    with tab_r:
        st.info("Seleccione una ruta o tramo y presione 'Buscar vuelos' para ver el ranking de rutas y el balance entre sentidos.")
    with tab_e:
        st.info("Seleccione una ruta o tramo y presione 'Buscar vuelos' para ver el comportamiento estacional y los índices de temporada.")
    with tab_d:
        st.info("Seleccione una ruta o tramo y presione 'Buscar vuelos' para descargar los microdatos y reportes del segmento.")
    st.stop()

# -------------------------------------------------------------
# EJECUCIÓN FILTRADA (INSTANTÁNEA)
# -------------------------------------------------------------
filtros = st.session_state['criterios_activos']
f_d_efectiva = sanitizar_fecha(filtros.get('desde'), def_desde, f_min_total, f_max_total)
f_h_efectiva = sanitizar_fecha(filtros.get('hasta'), def_hasta, f_min_total, f_max_total)
mascara = (df_raw['fecha'].dt.date >= f_d_efectiva) & (df_raw['fecha'].dt.date <= f_h_efectiva)

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
    st.warning("⚠️ No se encontraron vuelos para los criterios seleccionados. Ajuste los filtros y pulse **Buscar vuelos**.")
    st.stop()

# KPIs Reales del Segmento Filtrado
pax_total = df_filtrado['pasajeros'].sum()
vuelos_total = df_filtrado['vuelos'].sum()
asientos_total = df_filtrado['asientos'].sum()
factor_ocupacion = (pax_total / asientos_total * 100) if asientos_total > 0 else np.nan
pax_por_vuelo = (pax_total / vuelos_total) if vuelos_total > 0 else 0

# Índice HHI
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
kpi6.metric("Concentración (HHI)", f"{hhi_val:,}".replace(",", "."), delta=hhi_desc, delta_color="off", delta_arrow="off",
            help="Índice Herfindahl-Hirschman sobre pasajeros: menos de 1.500 = competitivo, 1.500 a 2.500 = moderado, más de 2.500 = concentrado.")

# -------------------------------------------------------------
# ESTRUCTURA ORGANIZADA POR PESTAÑAS FUNCIONALES
# -------------------------------------------------------------
tab_panorama, tab_competencia, tab_rutas, tab_estacionalidad, tab_datos = st.tabs([
    "📊 Panorama",
    "⚖️ Competencia",
    "🗺️ Rutas y sentidos",
    "📅 Estacionalidad",
    "📋 Datos y descargas"
])

# -------------------------------------------------------------
# RANKING DE RUTAS (con variación vs. mismo período del año anterior)
# -------------------------------------------------------------
df_rank = df_filtrado.groupby('ruta_label', observed=True).agg(
    Pasajeros=('pasajeros', 'sum'), Vuelos=('vuelos', 'sum'), Asientos=('asientos', 'sum')
).reset_index().rename(columns={'ruta_label': 'Ruta'})
df_rank['Ruta'] = df_rank['Ruta'].astype(str)
df_rank = df_rank[df_rank['Vuelos'] > 0].sort_values('Pasajeros', ascending=False).reset_index(drop=True)
df_rank['Share'] = df_rank['Pasajeros'] / max(df_rank['Pasajeros'].sum(), 1) * 100
df_rank['Ocupación'] = np.where(df_rank['Asientos'] > 0, df_rank['Pasajeros'] / df_rank['Asientos'] * 100, np.nan)
dias_periodo = dias_operados(df_filtrado)
df_rank['Asientos/vuelo'] = np.where(df_rank['Vuelos'] > 0, df_rank['Asientos'] / df_rank['Vuelos'], np.nan)
df_rank['Vuelos/día'] = df_rank['Vuelos'] / dias_periodo

rutas_suspendidas = []
hay_base_prev = restar_ano(f_d_efectiva) >= f_min_total
if hay_base_prev:
    df_prev = filtrar_segmento(df_raw, filtros, restar_ano(f_d_efectiva), restar_ano(f_h_efectiva))
    pax_prev = df_prev.groupby('ruta_label', observed=True)['pasajeros'].sum()
    pax_prev = {str(k): v for k, v in pax_prev.items() if v > 0}
    df_rank['Pax año ant.'] = df_rank['Ruta'].map(pax_prev).fillna(0).astype(int)
    df_rank['Δ% vs año ant.'] = np.where(
        df_rank['Pax año ant.'] > 0,
        (df_rank['Pasajeros'] - df_rank['Pax año ant.']) / df_rank['Pax año ant.'].replace(0, np.nan) * 100,
        np.nan
    )
    df_rank['Estado'] = np.where(df_rank['Pax año ant.'] == 0, 'Nueva', '')
    rutas_suspendidas = sorted(set(pax_prev) - set(df_rank['Ruta']))

# =============================================================
# SECCIÓN 1: GRÁFICOS CON INFORMACIÓN BÁSICA (VERTICALES)
# =============================================================
with tab_panorama:
    # 1. Oferta vs. demanda vs. ocupación
    st.markdown("#### Oferta, Demanda y Ocupación del Segmento")
    df_od = df_filtrado.groupby(['periodo_orden', 'periodo_mes_es'], observed=True)[['pasajeros', 'asientos']].sum().reset_index()
    df_od['periodo_orden'] = df_od['periodo_orden'].astype(str)
    df_od['periodo_mes_es'] = df_od['periodo_mes_es'].astype(str)
    df_od = df_od.sort_values('periodo_orden')
    df_od['ocup'] = np.where(df_od['asientos'] > 0, df_od['pasajeros'] / df_od['asientos'] * 100, np.nan)

    fig_od = go.Figure()
    fig_od.add_bar(x=df_od['periodo_mes_es'], y=df_od['asientos'], name='Asientos ofrecidos', marker_color='#cbd5e1')
    fig_od.add_bar(x=df_od['periodo_mes_es'], y=df_od['pasajeros'], name='Pasajeros', marker_color=PALETA[0])
    fig_od.add_scatter(x=df_od['periodo_mes_es'], y=df_od['ocup'], name='Ocupación (%)', yaxis='y2',
                       mode='lines+markers', line=dict(color=PALETA[2], width=3), connectgaps=False,
                       hovertemplate='%{y:.1f}%<extra>Ocupación</extra>')
    fig_od.update_layout(
        barmode='overlay', height=440, margin=dict(l=20, r=20, t=50, b=40),
        xaxis=dict(categoryorder='array', categoryarray=df_od['periodo_mes_es'].tolist(), tickangle=-45),
        yaxis=dict(title='Asientos / Pasajeros'),
        yaxis2=dict(title='Ocupación', overlaying='y', side='right', range=[0, 105], tickvals=[0, 25, 50, 75, 100], ticksuffix='%', showgrid=False),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0)
    )
    st.plotly_chart(fig_od, use_container_width=True)
    st.caption("Si las barras grises superan mucho a las azules, hay capacidad ociosa; si se igualan y la ocupación se acerca al 100%, la ruta está saturada.")

    st.markdown("---")

    # Frecuencias y tamaño de aeronave
    st.markdown("#### Frecuencias y Tamaño de Aeronave")
    g_fq = df_filtrado.groupby(['periodo_orden', 'periodo_mes_es'], observed=True).agg(
        vuelos=('vuelos', 'sum'), asientos=('asientos', 'sum'), n_dias=('fecha', 'nunique')
    ).reset_index()
    g_fq['periodo_orden'] = g_fq['periodo_orden'].astype(str)
    g_fq['periodo_mes_es'] = g_fq['periodo_mes_es'].astype(str)
    g_fq = g_fq.sort_values('periodo_orden')

    def _dias(r):
        if r['n_dias'] > 1:
            return r['n_dias']
        y, m = map(int, r['periodo_orden'].split('-'))
        return calendar.monthrange(y, m)[1]

    g_fq['dias'] = g_fq.apply(_dias, axis=1)
    g_fq['vuelos_dia'] = g_fq['vuelos'] / g_fq['dias']
    g_fq['asientos_vuelo'] = np.where(g_fq['vuelos'] > 0, g_fq['asientos'] / g_fq['vuelos'], np.nan)

    fig_fq = go.Figure()
    fig_fq.add_bar(x=g_fq['periodo_mes_es'], y=g_fq['vuelos_dia'], name='Vuelos por día', marker_color=PALETA[1],
                   hovertemplate='%{y:,.1f} vuelos/día<extra></extra>')
    fig_fq.add_scatter(x=g_fq['periodo_mes_es'], y=g_fq['asientos_vuelo'], name='Asientos por vuelo', yaxis='y2',
                       mode='lines+markers', line=dict(color=PALETA[4], width=3),
                       hovertemplate='%{y:,.0f} asientos/vuelo<extra></extra>')
    fig_fq.update_layout(
        height=420, margin=dict(l=20, r=20, t=50, b=40),
        xaxis=dict(categoryorder='array', categoryarray=g_fq['periodo_mes_es'].tolist(), tickangle=-45),
        yaxis=dict(title='Vuelos por día'),
        yaxis2=dict(title='Asientos por vuelo', overlaying='y', side='right', showgrid=False, rangemode='tozero'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0)
    )
    st.plotly_chart(fig_fq, use_container_width=True)
    st.caption("Barras: frecuencia operada (vuelos por día). Línea: tamaño promedio de la aeronave. "
               "Si suben las barras, la ruta crece con más frecuencias; si sube la línea, con aviones más grandes.")

    st.markdown("---")

    # 2. Pasajeros mensuales por aerolínea
    st.markdown("#### Evolución Mensual de Pasajeros por Operador")
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

    if len(df_rank) > 1:
        st.markdown("#### Principales Rutas por Pasajeros")
        top_rutas = df_rank.head(15).iloc[::-1]
        fig_top = px.bar(
            top_rutas, x='Pasajeros', y='Ruta', orientation='h',
            title=f"Top {len(top_rutas)} rutas del segmento (ambos sentidos)",
            text=top_rutas['Pasajeros'].apply(fmt_entero)
        )
        fig_top.update_traces(textposition='outside', marker_color=PALETA[0], cliponaxis=False)
        fig_top.update_layout(height=max(320, 32 * len(top_rutas) + 100), margin=dict(l=20, r=60, t=50, b=40),
                              yaxis_title=None)
        st.plotly_chart(fig_top, use_container_width=True)

with tab_competencia:
    # Participación de mercado en el tiempo (100% apilado)
    st.markdown("#### Participación de Mercado Mes a Mes")
    df_share = df_filtrado.groupby(['periodo_orden', 'periodo_mes_es', 'aerolinea'], observed=True)['pasajeros'].sum().reset_index()
    df_share['periodo_orden'] = df_share['periodo_orden'].astype(str)
    df_share['periodo_mes_es'] = df_share['periodo_mes_es'].astype(str)
    df_share['aerolinea'] = df_share['aerolinea'].astype(str)
    df_share = df_share[df_share['pasajeros'] > 0].sort_values('periodo_orden')
    if not df_share.empty:
        orden_meses = df_share.drop_duplicates('periodo_orden')['periodo_mes_es'].tolist()
        fig_share = px.bar(
            df_share, x='periodo_mes_es', y='pasajeros', color='aerolinea',
            category_orders={'periodo_mes_es': orden_meses},
            labels={'periodo_mes_es': 'Período', 'pasajeros': 'Participación', 'aerolinea': 'Aerolínea'},
            title="Porcentaje de los pasajeros transportados por cada aerolínea"
        )
        fig_share.update_layout(barmode='stack', barnorm='percent', yaxis_ticksuffix='%', xaxis_tickangle=-45, height=440,
                                margin=dict(l=20, r=20, t=50, b=40), legend_title_text='Aerolínea')
        st.plotly_chart(fig_share, use_container_width=True)
        st.caption("Muestra quién gana o pierde cuota a lo largo del tiempo; el HHI de arriba resume la concentración del período.")
    st.markdown("---")

    # 2. Factor de Ocupación mensual por aerolínea (Curva individual por cada aerolínea)
    st.markdown("#### Factor de Ocupación (%) por Aerolínea Mes a Mes")
    df_mes_ocup = df_filtrado.groupby(['periodo_orden', 'periodo_mes_es', 'aerolinea'], observed=True).agg(
        pasajeros=('pasajeros', 'sum'),
        asientos=('asientos', 'sum')
    ).reset_index()
    
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

    # Cuadro 2: Desempeño por Aerolínea
    st.subheader("Desempeño Operativo y Comercial por Aerolínea")
    df_aero = df_filtrado.groupby('aerolinea', observed=True).agg(
        Pasajeros=('pasajeros', 'sum'),
        Vuelos=('vuelos', 'sum'),
        Asientos=('asientos', 'sum')
    ).reset_index()

    df_aero = df_aero[df_aero['Vuelos'] > 0].sort_values(by='Pasajeros', ascending=False)
    total_pax_seg = df_aero['Pasajeros'].sum()
    df_aero['Market Share'] = np.where(total_pax_seg > 0, (df_aero['Pasajeros'] / total_pax_seg) * 100, 0)
    df_aero['Factor Ocupación'] = np.where(df_aero['Asientos'] > 0, (df_aero['Pasajeros'] / df_aero['Asientos']) * 100, np.nan)
    df_aero['Pax / Vuelo'] = np.where(df_aero['Vuelos'] > 0, df_aero['Pasajeros'] / df_aero['Vuelos'], 0)
    df_aero['Asientos / Vuelo'] = np.where(df_aero['Vuelos'] > 0, df_aero['Asientos'] / df_aero['Vuelos'], np.nan)
    df_aero['Vuelos / día'] = df_aero['Vuelos'] / dias_periodo

    df_aero_disp = df_aero.rename(columns={'aerolinea': 'Aerolínea'}).copy()
    cols_dec = ['Market Share', 'Factor Ocupación', 'Pax / Vuelo', 'Asientos / Vuelo', 'Vuelos / día']
    df_aero_disp[cols_dec] = df_aero_disp[cols_dec].round(1)
    st.dataframe(
        df_aero_disp, use_container_width=True, hide_index=True,
        column_config=config_numerica(df_aero_disp, porcentajes=('Market Share', 'Factor Ocupación'))
    )

with tab_rutas:
    st.subheader("Conectividad Federal")
    if len(df_rank) < 3:
        st.info("Para medir conectividad federal seleccioná un segmento con varias rutas (por ejemplo, 'Analizar total país' o una aerolínea).")
    else:
        o_amba = df_filtrado['origen_label'].astype(str).str[:3].isin(AMBA_SIGLAS)
        d_amba = df_filtrado['destino_label'].astype(str).str[:3].isin(AMBA_SIGLAS)
        toca_amba = (o_amba | d_amba).to_numpy()
        pax_arr = df_filtrado['pasajeros'].to_numpy()
        pax_transv = int(pax_arr[~toca_amba].sum())
        pct_transv = pax_transv / pax_total * 100 if pax_total > 0 else 0

        n_aeropuertos = len(set(df_filtrado['origen_label'].astype(str)) | set(df_filtrado['destino_label'].astype(str)))
        m1, m2, m3 = st.columns(3)
        m1.metric("Rutas operadas", fmt_entero(len(df_rank)),
                  help="Corredores (ambos sentidos) con al menos un vuelo en el período.")
        m2.metric("Aeropuertos conectados", fmt_entero(n_aeropuertos))
        m3.metric("Pasajeros sin pasar por el AMBA", fmt_porcentaje(pct_transv),
                  help="Porcentaje de pasajeros en rutas que no tocan Aeroparque, Ezeiza, El Palomar, Morón ni San Fernando (rutas transversales).")

        # Evolución de la participación de rutas transversales
        df_fed = df_filtrado[['periodo_orden', 'periodo_mes_es', 'pasajeros']].copy()
        df_fed['periodo_orden'] = df_fed['periodo_orden'].astype(str)
        df_fed['periodo_mes_es'] = df_fed['periodo_mes_es'].astype(str)
        df_fed['transv'] = np.where(~toca_amba, df_fed['pasajeros'], 0)
        df_fed = df_fed.groupby(['periodo_orden', 'periodo_mes_es'])[['pasajeros', 'transv']].sum().reset_index().sort_values('periodo_orden')
        df_fed['pct'] = np.where(df_fed['pasajeros'] > 0, df_fed['transv'] / df_fed['pasajeros'] * 100, np.nan)
        if len(df_fed) > 1:
            fig_fed = px.line(
                df_fed, x='periodo_mes_es', y='pct', markers=True,
                category_orders={'periodo_mes_es': df_fed['periodo_mes_es'].tolist()},
                labels={'periodo_mes_es': 'Período', 'pct': '% de pasajeros'},
                title="Pasajeros en rutas transversales (sin AMBA), % del total"
            )
            fig_fed.update_layout(yaxis_ticksuffix='%', xaxis_tickangle=-45, height=380,
                                  margin=dict(l=20, r=20, t=50, b=40))
            st.plotly_chart(fig_fed, use_container_width=True)

        # Aeropuertos con más movimiento de pasajeros
        mov_o = df_filtrado.groupby('origen_label', observed=True)['pasajeros'].sum()
        mov_d = df_filtrado.groupby('destino_label', observed=True)['pasajeros'].sum()
        mov = (mov_o.rename(index=str).add(mov_d.rename(index=str), fill_value=0)).sort_values(ascending=False).head(15)
        df_mov = mov.reset_index()
        df_mov.columns = ['Aeropuerto', 'Pasajeros']
        df_mov['Zona'] = np.where(df_mov['Aeropuerto'].str[:3].isin(AMBA_SIGLAS), 'AMBA', 'Interior')
        fig_mov = px.bar(
            df_mov.iloc[::-1], x='Pasajeros', y='Aeropuerto', orientation='h', color='Zona',
            color_discrete_map={'AMBA': '#94a3b8', 'Interior': PALETA[0]},
            title="Aeropuertos con más movimiento (pasajeros que salen + llegan)"
        )
        fig_mov.update_layout(height=max(320, 32 * len(df_mov) + 100), margin=dict(l=20, r=20, t=50, b=40),
                              yaxis_title=None, legend_title_text='')
        st.plotly_chart(fig_mov, use_container_width=True)

    st.markdown("---")

    st.subheader("Dependencia de un Solo Operador")
    if filtros.get('aerolineas'):
        st.info("Con un filtro de aerolínea activo, todas las rutas figuran como de un solo operador. Quitá el filtro de aerolínea para ver esta sección.")
    elif len(df_rank) < 3:
        st.info("Seleccioná un segmento con varias rutas (por ejemplo, 'Analizar total país') para ver la dependencia de un solo operador.")
    else:
        base_ops = df_filtrado[df_filtrado['pasajeros'] > 0]
        ops_ruta = base_ops.groupby('ruta_label', observed=True)['aerolinea'].nunique()
        base_mono = base_ops[base_ops['ruta_label'].isin(ops_ruta[ops_ruta == 1].index)]
        pax_mono = int(base_mono['pasajeros'].sum())

        c1, c2 = st.columns(2)
        c1.metric("Rutas con un único operador", f"{int((ops_ruta == 1).sum())} de {len(ops_ruta)}")
        c2.metric("Pasajeros en esas rutas", fmt_porcentaje(pax_mono / pax_total * 100 if pax_total > 0 else 0),
                  help="Porcentaje de los pasajeros del segmento que viaja en rutas donde una sola aerolínea opera.")

        if base_mono.empty:
            st.info("Todas las rutas del segmento tienen más de un operador.")
        else:
            g_mono = base_mono.groupby(['ruta_label', 'aerolinea'], observed=True).agg(
                Pasajeros=('pasajeros', 'sum'), Vuelos=('vuelos', 'sum'), Asientos=('asientos', 'sum')
            ).reset_index()
            g_mono['ruta_label'] = g_mono['ruta_label'].astype(str)
            g_mono['aerolinea'] = g_mono['aerolinea'].astype(str)
            g_mono = g_mono[g_mono['Vuelos'] > 0]

            pax_aero_total = df_filtrado.groupby('aerolinea', observed=True)['pasajeros'].sum()
            pax_aero_total.index = pax_aero_total.index.astype(str)
            res = g_mono.groupby('aerolinea').agg(**{'Rutas exclusivas': ('ruta_label', 'nunique'),
                                                   'Pasajeros en rutas exclusivas': ('Pasajeros', 'sum')}).reset_index()
            res['% de sus pasajeros'] = (res['Pasajeros en rutas exclusivas'] / res['aerolinea'].map(pax_aero_total) * 100).round(1)
            res = res.sort_values('Pasajeros en rutas exclusivas', ascending=False).rename(columns={'aerolinea': 'Aerolínea'})
            st.markdown("**Por aerolínea**")
            st.dataframe(res, use_container_width=True, hide_index=True,
                         column_config=config_numerica(res, porcentajes=('% de sus pasajeros',)))

            top_mono = g_mono.sort_values('Pasajeros', ascending=False).head(25).rename(columns={'ruta_label': 'Ruta', 'aerolinea': 'Operador único'})
            top_mono['Ocupación'] = np.where(top_mono['Asientos'] > 0, top_mono['Pasajeros'] / top_mono['Asientos'] * 100, np.nan).round(1)
            st.markdown("**Rutas más grandes con un solo operador**")
            st.dataframe(top_mono[['Ruta', 'Operador único', 'Pasajeros', 'Vuelos', 'Ocupación']], use_container_width=True, hide_index=True,
                         column_config=config_numerica(top_mono[['Ruta', 'Operador único', 'Pasajeros', 'Vuelos', 'Ocupación']], porcentajes=('Ocupación',)))
            st.caption("Son las rutas más frágiles: si esa aerolínea se retira o reduce frecuencias, el corredor queda sin servicio.")

    st.markdown("---")

    # Cuadro 1: Ranking de rutas
    st.subheader("Ranking de Rutas")
    df_rank_disp = df_rank.copy()
    df_rank_disp[['Share', 'Ocupación', 'Asientos/vuelo', 'Vuelos/día']] = df_rank_disp[['Share', 'Ocupación', 'Asientos/vuelo', 'Vuelos/día']].round(1)
    if 'Δ% vs año ant.' in df_rank_disp.columns:
        df_rank_disp['Δ% vs año ant.'] = df_rank_disp['Δ% vs año ant.'].round(1)
    st.dataframe(
        df_rank_disp, use_container_width=True, hide_index=True,
        column_config=config_numerica(df_rank_disp, porcentajes=('Share', 'Ocupación'))
    )
    if hay_base_prev:
        st.caption(
            f"Δ% compara con el mismo período del año anterior ({restar_ano(f_d_efectiva).strftime('%d/%m/%Y')} a "
            f"{restar_ano(f_h_efectiva).strftime('%d/%m/%Y')}). “Nueva” = ruta sin pasajeros en ese período."
        )
        if rutas_suspendidas:
            with st.expander(f"Rutas que operaban el año anterior y hoy no registran vuelos ({len(rutas_suspendidas)})"):
                st.write(" · ".join(rutas_suspendidas))
    else:
        st.caption("La base no tiene datos del año anterior para este período, por eso no se calcula la variación.")
    st.markdown("---")

    # 4. Gráfico por Sentido de Vuelo (Ida vs Vuelta)
    st.markdown("#### Pasajeros por Sentido de Vuelo (Ida vs. Vuelta)")
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
    st.markdown("---")

    # Cuadro 2: Desempeño por Sentido de Vuelo
    st.subheader("Desempeño por Sentido de Vuelo (Tramo)")
    df_tramo = df_filtrado.groupby(['tramo_label', 'aerolinea'], observed=True).agg(
        Pasajeros=('pasajeros', 'sum'),
        Vuelos=('vuelos', 'sum'),
        Asientos=('asientos', 'sum')
    ).reset_index()
    df_tramo = df_tramo[df_tramo['Vuelos'] > 0].sort_values(by=['tramo_label', 'Pasajeros'], ascending=[True, False])
    df_tramo['Ocupación'] = np.where(df_tramo['Asientos'] > 0, (df_tramo['Pasajeros'] / df_tramo['Asientos']) * 100, np.nan)
    df_tramo['Pax/Vuelo'] = np.where(df_tramo['Vuelos'] > 0, df_tramo['Pasajeros'] / df_tramo['Vuelos'], 0)

    df_t_disp = df_tramo[['tramo_label', 'aerolinea', 'Pasajeros', 'Vuelos', 'Asientos', 'Ocupación', 'Pax/Vuelo']].rename(
        columns={'tramo_label': 'Tramo Operado', 'aerolinea': 'Aerolínea'}
    ).copy()
    df_t_disp[['Ocupación', 'Pax/Vuelo']] = df_t_disp[['Ocupación', 'Pax/Vuelo']].round(1)
    st.dataframe(
        df_t_disp, use_container_width=True, hide_index=True,
        column_config=config_numerica(df_t_disp, porcentajes=('Ocupación',))
    )

with tab_datos:
    # Cuadro 3: Matriz Mensual Detallada
    st.subheader("Matriz Mensual de Pasajeros por Operador")
    pivot_pax = df_filtrado.pivot_table(
        index='aerolinea',
        columns='periodo_mes_es',
        values='pasajeros',
        aggfunc='sum',
        fill_value=0,
        observed=True
    )

    meses_presentes = df_filtrado[['periodo_orden', 'periodo_mes_es']].drop_duplicates().sort_values('periodo_orden')['periodo_mes_es'].tolist()
    columnas_ordenadas = [m for m in meses_presentes if m in pivot_pax.columns]
    pivot_pax = pivot_pax[columnas_ordenadas]

    pivot_pax_con_total = pivot_pax.copy()
    pivot_pax_con_total['Total General'] = pivot_pax_con_total.sum(axis=1)
    fila_total = pivot_pax_con_total.sum(axis=0)
    fila_total.name = 'Total Mercado'
    pivot_pax_con_total = pd.concat([pivot_pax_con_total, fila_total.to_frame().T])

    st.dataframe(pivot_pax_con_total, use_container_width=True, column_config=config_numerica(pivot_pax_con_total))
    st.markdown("---")

# =============================================================
# SECCIÓN 3: ESTACIONALIDAD DE LA RUTA (CON SELECTOR DE AÑO)
# =============================================================
with tab_estacionalidad:
    st.markdown("### Análisis de Estacionalidad de la Demanda")
    st.markdown("Comportamiento intra-anual del segmento elegido (ruta, aeropuertos y aerolíneas), **sin importar el período de fechas** del filtro: usa toda la base disponible.")

    mascara_est = pd.Series(True, index=df_raw.index)
    if not filtros.get('todo_el_pais', False):
        if filtros.get('rutas'):
            mascara_est &= df_raw['ruta_label'].isin(filtros['rutas'])
        if filtros.get('origenes'):
            mascara_est &= df_raw['origen_label'].isin(filtros['origenes'])
        if filtros.get('destinos'):
            mascara_est &= df_raw['destino_label'].isin(filtros['destinos'])
    if filtros.get('aerolineas'):
        mascara_est &= df_raw['aerolinea'].isin(filtros['aerolineas'])
    df_est_total = df_raw[mascara_est]

    meses_por_ano = df_est_total.groupby('ano_num', observed=True)['mes_num'].nunique()
    anos_completos = sorted(meses_por_ano[meses_por_ano == 12].index.tolist())
    anos_disp_est = sorted(df_est_total['ano_num'].unique().tolist(), reverse=True)

    # Años superpuestos (índice 100 = promedio mensual del propio año)
    if len(anos_completos) >= 1:
        df_sup = df_est_total[df_est_total['ano_num'].isin(anos_completos)].groupby(['ano_num', 'mes_num'], observed=True)['pasajeros'].sum().reset_index()
        df_sup['indice'] = df_sup['pasajeros'] / df_sup.groupby('ano_num')['pasajeros'].transform('mean') * 100
        df_sup['Mes'] = df_sup['mes_num'].map(meses_es)
        df_sup['Año'] = df_sup['ano_num'].astype(str)
        fig_sup = px.line(
            df_sup.sort_values('mes_num'), x='Mes', y='indice', color='Año', markers=True,
            category_orders={'Mes': [meses_es[i] for i in range(1, 13)]},
            labels={'indice': 'Índice (100 = promedio mensual del año)'},
            title="Estacionalidad por año (solo años completos)"
        )
        fig_sup.add_hline(y=100, line_dash='dot', line_color='#94a3b8')
        fig_sup.update_layout(height=420, margin=dict(l=20, r=20, t=50, b=40))
        st.plotly_chart(fig_sup, use_container_width=True)
        st.caption("Líneas que se superponen indican una estacionalidad estable; un año que se separa del resto marca un quiebre (shock, nueva oferta o crisis).")

    # Día de la semana x mes
    df_dia = df_est_total.groupby('fecha')['pasajeros'].sum().reset_index()
    if len(df_dia) >= 28:
        df_dia['dow'] = df_dia['fecha'].dt.dayofweek
        df_dia['mes'] = df_dia['fecha'].dt.month
        mat = df_dia.groupby(['dow', 'mes'])['pasajeros'].mean().unstack('mes').reindex(index=range(7), columns=range(1, 13))
        dias_es = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
        fig_dow = go.Figure(go.Heatmap(
            z=mat.values, x=[meses_es[m] for m in mat.columns], y=dias_es,
            colorscale='Blues', hoverongaps=False,
            hovertemplate='%{y} de %{x}: %{z:,.0f} pax/día<extra></extra>',
            colorbar=dict(title='Pax/día')
        ))
        fig_dow.update_layout(title="Pasajeros promedio por día de la semana y mes", height=360,
                              margin=dict(l=20, r=20, t=50, b=40), yaxis=dict(autorange='reversed'))
        st.plotly_chart(fig_dow, use_container_width=True)

    st.markdown("---")
    st.markdown("#### Detalle por año")

    if len(anos_disp_est) > 0:
        opciones_ano = [str(a) for a in anos_disp_est] + ["Promedio Histórico (Todos los Años)"]
        col_est_sel, _ = st.columns([4, 6])
        with col_est_sel:
            ano_est_sel = st.selectbox(
                "📅 Año para Análisis de Estacionalidad:",
                options=opciones_ano,
                index=0,
                help="Seleccione un año específico para ver sus meses o elija el promedio histórico de todos los años disponibles."
            )

        if ano_est_sel == "Promedio Histórico (Todos los Años)":
            df_est_base = df_est_total[df_est_total['ano_num'].isin(anos_completos)].copy() if anos_completos else df_est_total.copy()
            titulo_graf = "Curva de Estacionalidad Mensual - Promedio Histórico"
            cant_anos = max(1, df_est_base['ano_num'].nunique())
            if not anos_completos:
                st.caption("⚠️ No hay años completos en la base: el promedio incluye años parciales y puede estar sesgado.")
            df_est = df_est_base.groupby('mes_num', observed=True).agg(
                pasajeros=('pasajeros', lambda x: x.sum() / cant_anos),
                vuelos=('vuelos', lambda x: x.sum() / cant_anos),
                asientos=('asientos', lambda x: x.sum() / cant_anos)
            ).reset_index()
            subtitulo_tabla = f"Promedio Mensual Histórico ({cant_anos} años completos)"
        else:
            ano_int = int(ano_est_sel)
            df_est_base = df_est_total[df_est_total['ano_num'] == ano_int].copy()
            if ano_int not in anos_completos:
                st.caption(f"⚠️ {ano_int} es un año incompleto ({int(meses_por_ano.get(ano_int, 0))} de 12 meses): el índice se calcula sobre los meses disponibles.")
            titulo_graf = f"Curva de Estacionalidad Mensual - Año {ano_int}"
            df_est = df_est_base.groupby('mes_num', observed=True).agg(
                pasajeros=('pasajeros', 'sum'),
                vuelos=('vuelos', 'sum'),
                asientos=('asientos', 'sum')
            ).reset_index()
            subtitulo_tabla = f"Estadísticas Mensuales del Año {ano_int}"

        if not df_est.empty and df_est['pasajeros'].sum() > 0:
            promedio_mensual_pax = df_est['pasajeros'].mean()
            df_est['mes_nombre'] = df_est['mes_num'].map(meses_es)
            df_est['indice_estacionalidad_%'] = (df_est['pasajeros'] / promedio_mensual_pax) * 100
            df_est['ocupacion_%'] = np.where(df_est['asientos'] > 0, (df_est['pasajeros'] / df_est['asientos']) * 100, np.nan)
            df_est = df_est.sort_values(by='mes_num')

            col_est1, col_est2 = st.columns([6, 4])

            with col_est1:
                fig_est = px.bar(
                    df_est,
                    x='mes_nombre',
                    y='pasajeros',
                    title=titulo_graf,
                    labels={'mes_nombre': 'Mes', 'pasajeros': 'Pasajeros'},
                    text=df_est['pasajeros'].apply(fmt_entero)
                )
                fig_est.update_traces(textposition='outside')
                fig_est.update_layout(bargap=0.2)
                st.plotly_chart(fig_est, use_container_width=True)

            with col_est2:
                st.markdown(f"#### {subtitulo_tabla}")
                df_est_disp = pd.DataFrame({
                    'Mes': df_est['mes_nombre'],
                    'Pasajeros': df_est['pasajeros'].round(0),
                    'Vuelos': df_est['vuelos'].round(0),
                    'Ocupación': df_est['ocupacion_%'].round(1),
                    'Índice estacional': df_est['indice_estacionalidad_%'].round(1),
                })
                st.dataframe(
                    df_est_disp, use_container_width=True, hide_index=True,
                    column_config=config_numerica(df_est_disp, porcentajes=('Ocupación', 'Índice estacional'))
                )
                st.caption("💡 *Un índice estacional superior al 100% representa meses de temporada alta (demanda por encima de la media anual).*")
        else:
            st.info(f"No se registraron vuelos para la ruta seleccionada en el año {ano_est_sel}.")
    else:
        st.info("No hay suficientes datos temporales para calcular la estacionalidad en el período seleccionado.")

# =============================================================
# SECCIÓN 4: COMPARACIÓN INTERANUAL (YoY) CON CALENDARIO (MÁX 1 AÑO)
# =============================================================
with tab_competencia:
    st.markdown("---")
    st.markdown("### Comparación Interanual (YoY)")
    st.markdown(
        "Seleccione en el **calendario** el rango de fechas que desea analizar (máximo 1 año). "
        "El sistema comparará ese lapso contra el **mismo período del año base** elegido para calcular el crecimiento y el "
        "**desplazamiento de cuota de mercado (Shift Share)** entre aerolíneas."
    )

    def render_yoy():
        anos_disponibles = sorted(df_raw['ano_num'].unique().tolist())

        if len(anos_disponibles) >= 2:
            def_yoy_hasta = f_h_efectiva
            def_yoy_desde = f_d_efectiva
            if (def_yoy_hasta - def_yoy_desde).days > 364:
                def_yoy_desde = max(f_min_total, def_yoy_hasta - timedelta(days=364))
            clave_yoy = f"{f_d_efectiva}_{f_h_efectiva}"
            def_yoy_desde = sanitizar_fecha(def_yoy_desde, f_min_total, f_min_total, f_max_total)
            def_yoy_hasta = sanitizar_fecha(def_yoy_hasta, f_max_total, f_min_total, f_max_total)

            col_cal1, col_cal2, col_cal3 = st.columns([4, 4, 4])
            with col_cal1:
                f_yoy_desde = st.date_input(
                    "📅 Fecha Desde (Período Analizado):",
                    value=def_yoy_desde,
                    min_value=f_min_total,
                    max_value=f_max_total,
                    key=f"cal_yoy_desde_{clave_yoy}",
                    help="Fecha de inicio del rango a analizar (máximo 1 año de amplitud)."
                )
            with col_cal2:
                f_yoy_hasta = st.date_input(
                    "📅 Fecha Hasta (Período Analizado):",
                    value=def_yoy_hasta,
                    min_value=f_min_total,
                    max_value=f_max_total,
                    key=f"cal_yoy_hasta_{clave_yoy}",
                    help="Fecha de fin del rango a analizar."
                )

            f_yoy_desde = sanitizar_fecha(f_yoy_desde, def_yoy_desde, f_min_total, f_max_total)
            f_yoy_hasta = sanitizar_fecha(f_yoy_hasta, def_yoy_hasta, f_min_total, f_max_total)

            if f_yoy_hasta < f_yoy_desde:
                st.error("⚠️ La fecha 'Hasta' debe ser igual o posterior a la fecha 'Desde'.")
                return

            dias_rango = (f_yoy_hasta - f_yoy_desde).days + 1
            if dias_rango > 366:
                st.error(f"⚠️ El rango seleccionado tiene {dias_rango} días y supera el límite de 1 año (365 días). Por favor elija un rango de fechas menor o igual a 1 año.")
                return

            ano_reciente = f_yoy_hasta.year
            anos_posibles_base = [a for a in anos_disponibles if a != ano_reciente]
            if not anos_posibles_base:
                anos_posibles_base = [a for a in anos_disponibles if a < ano_reciente]

            if not anos_posibles_base:
                st.warning("⚠️ No hay un año base anterior disponible para contrastar contra el período seleccionado.")
                return

            idx_base_def = 0
            if (ano_reciente - 1) in anos_posibles_base:
                idx_base_def = anos_posibles_base.index(ano_reciente - 1)
            else:
                idx_base_def = len(anos_posibles_base) - 1

            with col_cal3:
                ano_base = st.selectbox(
                    "⚖️ Año Base a Comparar:",
                    options=anos_posibles_base,
                    index=idx_base_def,
                    help="Año contra el cual se compararán exactamente los mismos días del calendario."
                )

            delta_anios = ano_reciente - ano_base
            def desplazar_fecha(f, d_anios):
                target_y = f.year - d_anios
                try:
                    return f.replace(year=target_y)
                except ValueError:
                    return f.replace(year=target_y, day=28)

            f_base_desde = desplazar_fecha(f_yoy_desde, delta_anios)
            f_base_hasta = desplazar_fecha(f_yoy_hasta, delta_anios)

            st.info(
                f"🔍 **Período Analizado:** del **{f_yoy_desde.strftime('%d/%m/%Y')}** al **{f_yoy_hasta.strftime('%d/%m/%Y')}** ({dias_rango} días)  \n"
                f"⚖️ **Período Base Homólogo ({ano_base}):** del **{f_base_desde.strftime('%d/%m/%Y')}** al **{f_base_hasta.strftime('%d/%m/%Y')}**"
            )

            mask_reciente = (df_raw['fecha'].dt.date >= f_yoy_desde) & (df_raw['fecha'].dt.date <= f_yoy_hasta)
            mask_base = (df_raw['fecha'].dt.date >= f_base_desde) & (df_raw['fecha'].dt.date <= f_base_hasta)

            if not filtros.get('todo_el_pais', False):
                if filtros.get('rutas'):
                    mask_reciente &= df_raw['ruta_label'].isin(filtros['rutas'])
                    mask_base &= df_raw['ruta_label'].isin(filtros['rutas'])
                if filtros.get('origenes'):
                    mask_reciente &= df_raw['origen_label'].isin(filtros['origenes'])
                    mask_base &= df_raw['origen_label'].isin(filtros['origenes'])
                if filtros.get('destinos'):
                    mask_reciente &= df_raw['destino_label'].isin(filtros['destinos'])
                    mask_base &= df_raw['destino_label'].isin(filtros['destinos'])

            if filtros.get('aerolineas'):
                mask_reciente &= df_raw['aerolinea'].isin(filtros['aerolineas'])
                mask_base &= df_raw['aerolinea'].isin(filtros['aerolineas'])

            df_yoy_reciente = df_raw[mask_reciente].copy()
            df_yoy_base = df_raw[mask_base].copy()

            pax_reciente = df_yoy_reciente.groupby('aerolinea', observed=True)['pasajeros'].sum()
            pax_base = df_yoy_base.groupby('aerolinea', observed=True)['pasajeros'].sum()

            vue_reciente = df_yoy_reciente.groupby('aerolinea', observed=True)['vuelos'].sum()
            vue_base = df_yoy_base.groupby('aerolinea', observed=True)['vuelos'].sum()

            asi_reciente = df_yoy_reciente.groupby('aerolinea', observed=True)['asientos'].sum()
            asi_base = df_yoy_base.groupby('aerolinea', observed=True)['asientos'].sum()

            tot_pax_reciente = int(pax_reciente.sum())
            tot_pax_base = int(pax_base.sum())
            tot_vue_reciente = int(vue_reciente.sum())
            tot_vue_base = int(vue_base.sum())

            dif_pax_global = tot_pax_reciente - tot_pax_base
            var_pax_global = (dif_pax_global / tot_pax_base * 100) if tot_pax_base > 0 else 0
            dif_vue_global = tot_vue_reciente - tot_vue_base

            k_c1, k_c2, k_c3 = st.columns(3)
            k_c1.metric(
                f"Total Pasajeros ({ano_reciente})",
                fmt_entero(tot_pax_reciente),
                delta=f"{var_pax_global:+.1f}% vs {ano_base}" if tot_pax_base > 0 else None
            )
            k_c2.metric(
                f"Total Vuelos ({ano_reciente})",
                fmt_entero(tot_vue_reciente),
                delta=f"{dif_vue_global:+d} vuelos vs {ano_base}"
            )
            k_c3.metric(
                f"Pasajeros Base ({ano_base})",
                fmt_entero(tot_pax_base)
            )

            aeros_activas = sorted(list(set(
                [a for a, v in pax_reciente.items() if v > 0] +
                [a for a, v in pax_base.items() if v > 0] +
                [a for a, v in vue_reciente.items() if v > 0] +
                [a for a, v in vue_base.items() if v > 0]
            )))

            if aeros_activas:
                comp_df = pd.DataFrame(index=aeros_activas)
                comp_df[f'Vuelos {ano_base}'] = [int(vue_base.get(a, 0)) for a in aeros_activas]
                comp_df[f'Vuelos {ano_reciente}'] = [int(vue_reciente.get(a, 0)) for a in aeros_activas]
                comp_df['Δ Vuelos'] = comp_df[f'Vuelos {ano_reciente}'] - comp_df[f'Vuelos {ano_base}']

                comp_df[f'Pax {ano_base}'] = [int(pax_base.get(a, 0)) for a in aeros_activas]
                comp_df[f'Pax {ano_reciente}'] = [int(pax_reciente.get(a, 0)) for a in aeros_activas]
                comp_df['Δ Pax'] = comp_df[f'Pax {ano_reciente}'] - comp_df[f'Pax {ano_base}']

                comp_df[f'Share {ano_base}'] = np.where(tot_pax_base > 0, (comp_df[f'Pax {ano_base}'] / tot_pax_base) * 100, 0)
                comp_df[f'Share {ano_reciente}'] = np.where(tot_pax_reciente > 0, (comp_df[f'Pax {ano_reciente}'] / tot_pax_reciente) * 100, 0)
                comp_df['Shift Share (pts)'] = comp_df[f'Share {ano_reciente}'] - comp_df[f'Share {ano_base}']

                as_b = np.array([asi_base.get(a, 0) for a in aeros_activas])
                as_r = np.array([asi_reciente.get(a, 0) for a in aeros_activas])
                comp_df[f'Ocup {ano_base}'] = np.where(as_b > 0, (comp_df[f'Pax {ano_base}'] / as_b) * 100, np.nan)
                comp_df[f'Ocup {ano_reciente}'] = np.where(as_r > 0, (comp_df[f'Pax {ano_reciente}'] / as_r) * 100, np.nan)

                comp_df = comp_df.sort_values(by=f'Pax {ano_reciente}', ascending=False)

                st.markdown(f"#### Cuadro Comparativo por Operador ({f_base_desde.strftime('%d/%m/%Y')} vs. {f_yoy_desde.strftime('%d/%m/%Y')})")

                comp_disp = comp_df.reset_index().rename(columns={'index': 'Aerolínea', 'aerolinea': 'Aerolínea', 'Shift Share (pts)': 'Shift Share'})
                cols_pct = tuple(c for c in comp_disp.columns if c.startswith(('Share ', 'Ocup ')))
                comp_disp[list(cols_pct)] = comp_disp[list(cols_pct)].round(1)
                comp_disp['Shift Share'] = comp_disp['Shift Share'].round(1)
                st.dataframe(
                    comp_disp, use_container_width=True, hide_index=True,
                    column_config=config_numerica(
                        comp_disp, porcentajes=cols_pct, deltas=('Δ Vuelos', 'Δ Pax'), deltas_pts=('Shift Share',)
                    )
                )

                st.caption(
                    "💡 **Interpretación de Métricas:**  \n"
                    "• **Δ Vuelos / Δ Pax:** Variación neta entre ambos períodos analizados.  \n"
                    "• **Share:** Porcentaje de pasajeros que transportó cada aerolínea sobre el total de la ruta en cada período.  \n"
                    "• **Shift Share (pts):** Puntos porcentuales ganados o perdidos por la aerolínea (Share Reciente − Share Base). Permite verificar exactamente qué compañía absorbió mercado de otra.  \n"
                    "• **Ocupación:** Factor de ocupación de los vuelos en cada período."
                )

                st.markdown("---")

                # Gráficos verticales uno abajo del otro
                st.markdown("#### Comparación Gráfica de Pasajeros por Operador")
                df_bar_pax = pd.DataFrame({
                    'Aerolínea': aeros_activas * 2,
                    'Período': [f'Base ({ano_base})'] * len(aeros_activas) + [f'Reciente ({ano_reciente})'] * len(aeros_activas),
                    'Pasajeros': [int(pax_base.get(a, 0)) for a in aeros_activas] + [int(pax_reciente.get(a, 0)) for a in aeros_activas]
                })

                fig_pax_comp = px.bar(
                    df_bar_pax,
                    x='Aerolínea',
                    y='Pasajeros',
                    color='Período',
                    barmode='group',
                    title=f"Volumen de Pasajeros por Aerolínea ({ano_base} vs. {ano_reciente})",
                    labels={'Pasajeros': 'Pasajeros Transportados'}
                )
                fig_pax_comp.update_layout(
                    xaxis_tickangle=-20,
                    height=480,
                    margin=dict(l=20, r=20, t=50, b=40)
                )
                st.plotly_chart(fig_pax_comp, use_container_width=True)

                st.markdown("---")

                st.markdown("#### Desplazamiento Neto de Cuota de Mercado (Shift Share en Puntos Porcentuales)")
                df_shift = comp_df[['Shift Share (pts)']].reset_index().rename(columns={'index': 'Aerolínea'})
                df_shift['Color'] = np.where(df_shift['Shift Share (pts)'] >= 0, 'Ganancia de Cuota', 'Pérdida de Cuota')

                fig_shift = px.bar(
                    df_shift,
                    x='Aerolínea',
                    y='Shift Share (pts)',
                    color='Color',
                    color_discrete_map={'Ganancia de Cuota': '#2ecc71', 'Pérdida de Cuota': '#e74c3c'},
                    title="Shift Share por Operador (Puntos Porcentuales de Cuota de Mercado Ganados o Cedidos)",
                    labels={'Shift Share (pts)': 'Shift Share (puntos porcentuales)'},
                    text=df_shift['Shift Share (pts)'].apply(lambda x: f"{x:+.1f} pts".replace(".", ","))
                )
                fig_shift.update_traces(textposition='outside')
                fig_shift.update_layout(
                    xaxis_tickangle=-20,
                    height=450,
                    margin=dict(l=20, r=20, t=50, b=40)
                )
                st.plotly_chart(fig_shift, use_container_width=True)

            else:
                st.warning("No se encontraron vuelos para la combinación de fechas y filtros seleccionada.")
        else:
            st.info("💡 Para utilizar la comparación interanual (YoY), la base oficial debe contener datos de al menos dos años diferentes.")

    render_yoy()

# =============================================================
# SECCIÓN 5: DESCARGAS OFICIALES
# =============================================================
with tab_datos:
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

    @st.cache_data(show_spinner=False)
    def generar_excel_bytes(df_f, pivot_f, aero_f):
        output_excel = io.BytesIO()
        try:
            with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
                if len(df_f) > 100000:
                    df_f.head(100000).to_excel(writer, sheet_name='Microdatos_Muestra', index=False)
                else:
                    df_f.to_excel(writer, sheet_name='Microdatos', index=False)
                pivot_f.to_excel(writer, sheet_name='Matriz_Pasajeros')
                aero_f.to_excel(writer, sheet_name='Resumen_Operadores', index=False)
            return output_excel.getvalue()
        except Exception:
            return None

    excel_bytes = generar_excel_bytes(df_filtrado, pivot_pax_con_total, df_aero)
    with col_exp2:
        if excel_bytes:
            st.download_button(
                label="📥 Descargar Reporte Completo (Excel)",
                data=excel_bytes,
                file_name=f"reporte_conectividad_oficial_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
