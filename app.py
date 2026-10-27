import os
import io
import re
import calendar
import math
from collections import Counter
import zipfile
from types import SimpleNamespace

import internacional
import mapas
from manual import mostrar_manual
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
.block-container { padding-top: 2rem; padding-bottom: 4rem; max-width: 1400px; }
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
div[data-testid="stColumn"]:has(div[data-testid="stMetric"]) { container-type: inline-size; }
/* El número se achica según el ancho de la tarjeta, así siempre se ve completo */
div[data-testid="stMetricValue"] { color: #0f172a; font-weight: 700; font-size: clamp(0.9rem, 12cqw, 2.25rem); line-height: 1.2; }
div[data-testid="stMetricValue"] > div { overflow: visible !important; text-overflow: clip !important; white-space: nowrap !important; }
div[data-testid="stMetricLabel"] *, div[data-testid="stMetricDelta"] * { white-space: normal !important; overflow: visible !important; text-overflow: clip !important; }

/* Pestañas */
button[data-baseweb="tab"] { font-weight: 600; padding: .7rem .8rem; }
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
    div[data-testid="stHorizontalBlock"]:has(div[data-testid="stMetric"]) { flex-wrap: wrap; gap: .6rem; }
    div[data-testid="stHorizontalBlock"]:has(div[data-testid="stMetric"]) > div[data-testid="stColumn"] {
        min-width: calc(50% - .6rem); flex: 1 1 calc(50% - .6rem);
    }
    button[data-baseweb="tab"] { padding: .5rem .6rem; font-size: .85rem; }
}
div[data-testid="stButtonGroup"] button { font-size: 1.05rem; font-weight: 600; padding: .55rem 1.3rem; }
#MainMenu, footer { visibility: hidden; }
[data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"] { display: none; }
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

# Cuántas ciudades comparten cada palabra clave (una clave repetida no identifica a una ciudad)
_CONTEO_KW = Counter(normalizar_texto_aeropuerto(kw) for d in AEROPUERTOS_EXHAUSTIVO.values() for kw in d['keywords'])

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
                puntaje += 100 if (n_kw == 0 and _CONTEO_KW[kw_norm] == 1) else 1
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

# Una ruta se considera "activa" en un mes si tuvo al menos esta cantidad de vuelos (criterio de SINTA)
UMBRAL_FRECUENCIAS_MES = 4

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

# Coordenadas (latitud, longitud) de los aeropuertos, por sigla IATA, para el mapa de conexiones
COORDENADAS = {
    'AEP': (-34.559, -58.416), 'EZE': (-34.822, -58.536), 'EPA': (-34.610, -58.613), 'MOR': (-34.676, -58.643),
    'AFA': (-34.588, -68.404), 'BHI': (-38.725, -62.169), 'BRC': (-41.151, -71.158), 'CNQ': (-27.446, -58.762),
    'COR': (-31.324, -64.208), 'CPC': (-40.075, -71.137), 'CRD': (-45.785, -67.466), 'CTC': (-28.596, -65.752),
    'EQS': (-42.908, -71.140), 'FMA': (-26.213, -58.228), 'FTE': (-50.280, -72.053), 'IGR': (-25.737, -54.473),
    'IRJ': (-29.382, -66.796), 'JSM': (-44.059, -70.469), 'JUJ': (-24.393, -65.098), 'LUQ': (-33.273, -66.356),
    'MDQ': (-37.934, -57.573), 'MDZ': (-32.832, -68.793), 'MLG': (-35.494, -69.574), 'NCJ': (-30.959, -61.535),
    'NQN': (-38.949, -68.156), 'OMR': (-45.590, -69.075), 'PMQ': (-46.538, -70.979), 'PMY': (-42.759, -65.103),
    'PRA': (-31.795, -60.480), 'PSS': (-27.386, -55.971), 'RCQ': (-29.210, -59.680), 'RCU': (-33.085, -64.261),
    'REL': (-43.211, -65.270), 'RES': (-27.450, -59.056), 'RGA': (-53.778, -67.749), 'RGL': (-51.609, -69.313),
    'RHD': (-27.497, -64.936), 'RLO': (-32.385, -65.187), 'ROS': (-32.904, -60.785), 'ROY': (-45.704, -70.246),
    'RSA': (-36.588, -64.276), 'RZA': (-50.017, -68.579), 'SDE': (-27.766, -64.310), 'SFN': (-31.712, -60.812),
    'SLA': (-24.856, -65.486), 'UAQ': (-31.572, -68.418), 'TUC': (-26.841, -65.105), 'USH': (-54.843, -68.296), 'VDM': (-40.869, -63.000),
}


# Cada aerolínea tiene siempre el mismo color, en todos los gráficos
COLORES_AEROLINEAS = {
    'Aerolíneas Argentinas': '#1d4ed8',
    'JetSMART Airlines': '#e11d48',
    'Flybondi': '#f59e0b',
    'Andes Líneas Aéreas': '#10b981',
    'LADE - Líneas Aéreas Del Estado': '#8b5cf6',
    'LATAM': '#0ea5e9',
    'Copa Airlines': '#84cc16',
    'American Jet': '#64748b',
    'Otras aerolíneas': '#cbd5e1',
}


def graficar(fig, mapa=False, leyenda_abajo=False):
    """Muestra un gráfico Plotly pensado también para pantallas chicas: sin título interno ni barra de
    herramientas (salvo el mapa, que la necesita para hacer zoom)."""
    for tr in fig.data:
        color = COLORES_AEROLINEAS.get(getattr(tr, 'name', None))
        if color and tr.type == 'bar':
            tr.marker.color = color
        elif color and tr.type == 'scatter':
            tr.line.color = color
            tr.marker.color = color
    if not mapa:
        fig.update_layout(title_text=None)
        lg = fig.layout.legend
        arriba = lg.orientation == 'h' and lg.y is not None and lg.y >= 1
        if leyenda_abajo:
            fig.update_layout(height=(fig.layout.height or 450) + 120,
                              legend=dict(orientation='h', yanchor='top', y=-0.4, xanchor='left', x=0, title_text=''),
                              margin=dict(t=30, b=190))
        else:
            fig.update_layout(margin=dict(t=90 if arriba else 30))
    st.plotly_chart(fig, width='stretch', config={'displayModeBar': bool(mapa), 'displaylogo': False, 'scrollZoom': bool(mapa)})


def mostrar_metodologia(f_desde_base, f_hasta_base):
    with st.expander("ℹ️ Metodología y definiciones"):
        st.markdown(f"""
**Fuente de los datos.** Estadísticas oficiales de conectividad aérea del Ministerio de Turismo (SINTA, Dirección de Mercados y Estadística),
elaboradas a partir de los registros de movimientos de vuelos de la ANAC. Esta página muestra únicamente **vuelos de cabotaje** y no genera ni
estima datos propios. Cobertura cargada: del **{f_desde_base.strftime('%d/%m/%Y')}** al **{f_hasta_base.strftime('%d/%m/%Y')}**.
La base se revisa automáticamente entre el 10 y el 20 de cada mes; la fuente puede corregir datos de meses anteriores.

**Indicadores**
- **Vuelos / frecuencias:** cantidad de vuelos operados. En los rankings de destinos, vuelos que llegan a ese destino.
- **Pasajeros y asientos:** pasajeros transportados y asientos ofrecidos en esos vuelos.
- **Ocupación (factor de ocupación):** pasajeros ÷ asientos × 100. Se muestra "s/d" cuando no hay asientos informados.
- **Pax / vuelo y asientos / vuelo:** promedio de pasajeros y de asientos por vuelo; el segundo refleja el tamaño medio de la aeronave.
- **Vuelos por día:** vuelos del período ÷ días con datos.
- **Variación interanual:** compara contra el mismo período calendario del año anterior.
- **Asientos-km y pasajeros-km:** asientos o pasajeros multiplicados por la distancia en línea recta entre los dos aeropuertos (aproximada: no es la distancia exacta que vuela cada avión).
- **Resumen del último mes:** compara con el mismo mes del año anterior; las aerolíneas que empezaron o dejaron de volar una ruta se comparan con el mes anterior.

**Rutas y sentidos**
- **Ruta:** corredor entre dos aeropuertos, sumando ambos sentidos. **Tramo:** un sentido (origen ➔ destino).
- **Ruta activa:** ruta con al menos **{UMBRAL_FRECUENCIAS_MES} vuelos en el mes**; evita contar vuelos sueltos o charters como rutas regulares.
- **Ruta transversal:** ruta que no toca el AMBA (Aeroparque, Ezeiza, El Palomar, Morón ni San Fernando).
- **Ruta con un solo operador:** ruta donde una única aerolínea transportó pasajeros en el período.

**Competencia**
- **Participación (market share):** pasajeros de la aerolínea ÷ pasajeros totales del segmento.
- **HHI (Herfindahl-Hirschman):** suma de los cuadrados de las participaciones (en %), de 0 a 10.000.
  Menos de 1.500: competitivo · 1.500 a 2.500: moderado · más de 2.500: concentrado.

**Estacionalidad.** Índice 100 = promedio mensual del año. Se calcula solo con años completos; un año incompleto se indica en pantalla.
""")


def restar_ano(f):
    try:
        return f.replace(year=f.year - 1)
    except ValueError:
        return f.replace(year=f.year - 1, day=28)

def entre_fechas(fechas, desde, hasta):
    """Máscara de fechas entre 'desde' y 'hasta' (ambos incluidos), comparando directamente las fechas
    (mucho más rápido que convertir cada fila con .dt.date)."""
    return (fechas >= pd.Timestamp(desde)) & (fechas < pd.Timestamp(hasta) + pd.Timedelta(days=1))


def filtrar_segmento(df, filtros, desde, hasta):
    """Aplica los filtros activos de ruta/aeropuertos/aerolínea y un rango de fechas."""
    m = entre_fechas(df['fecha'], desde, hasta)
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

def _formateador_es(formato, serie):
    """Convierte un formato de columna ("localized", "%.1f%%", "%+d"…) en una función que escribe 1.234,5."""
    m = re.fullmatch(r'%(\+?)(?:\.(\d+))?([df])(.*)', str(formato))
    if m:
        signo, decimales, sufijo = m.group(1), int(m.group(2) or 0), m.group(4).replace('%%', '%')
    else:  # "localized": sin decimales si la columna es entera; si no, 1 (o 2 para valores chicos, como 1,09)
        s = pd.to_numeric(serie, errors='coerce').dropna()
        entera = s.empty or bool((s == s.round()).all())
        signo, sufijo = '', ''
        decimales = 0 if entera else (2 if s.abs().max() < 10 else 1)

    def formatear(x):
        if pd.isna(x):
            return ''
        texto = f"{x:{signo},.{decimales}f}"
        return texto.replace(',', '_').replace('.', ',').replace('_', '.') + sufijo
    return formatear


def tabla(data, column_config=None, **kwargs):
    """st.dataframe con los números en formato argentino (1.234,5) que se siguen ordenando como números."""
    if isinstance(data, pd.DataFrame) and column_config and data.size <= 200_000 and data.columns.is_unique and data.index.is_unique:
        formatos, cfg = {}, dict(column_config)
        for c, conf in column_config.items():
            tc = conf.get('type_config') if isinstance(conf, dict) else None
            if c in data.columns and tc and tc.get('type') == 'number' and tc.get('format') and pd.api.types.is_numeric_dtype(data[c]):
                formatos[c] = _formateador_es(tc['format'], data[c])
                cfg[c] = {**conf, 'type_config': {**tc, 'format': None}}
        if formatos:
            data, column_config = data.style.format(formatos, na_rep=''), cfg
    return st.dataframe(data, column_config=column_config, **kwargs)


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

def aplicar_unicos(serie, func):
    """Aplica 'func' una sola vez por cada valor distinto de la serie (en vez de fila por fila)."""
    codigos, unicos = pd.factorize(serie, use_na_sentinel=True)
    valores = np.empty(len(unicos) + 1, dtype=object)
    valores[:len(unicos)] = [func(u) for u in unicos]
    valores[-1] = func(np.nan)  # código -1 = valores vacíos
    return pd.Series(valores[codigos], index=serie.index)


# -------------------------------------------------------------
# DETECCIÓN Y PROCESAMIENTO ESTRICTO DE DATOS REALES (OPTIMIZADO EN RAM)
# -------------------------------------------------------------
def procesar_dataframe_oficial(df_in):
    if df_in is None or df_in.empty:
        return None, "El archivo proporcionado está vacío."

    df = df_in  # el DataFrame viene recién leído del archivo: no hace falta copiarlo
    
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
        df['aerolinea'] = aplicar_unicos(df['aerolinea_raw'].astype(str), limpiar_mojibake_texto).replace({'nan': 'Otras Aerolíneas', '': 'Otras Aerolíneas'})
    else:
        df['aerolinea'] = 'Línea Regular'

    # Métricas numéricas con tipos compactos
    for col_met, col_dest, col_type in [
        ('pasajeros_raw', 'pasajeros', np.int32),
        ('vuelos_raw', 'vuelos', np.int16),
        ('asientos_raw', 'asientos', np.int32)
    ]:
        if col_met in df.columns and pd.api.types.is_integer_dtype(df[col_met]):
            df[col_dest] = df[col_met].fillna(0).astype(col_type)  # ya viene como número entero
        elif col_met in df.columns:
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
        anos = pd.to_numeric(aplicar_unicos(df['ano_raw'], parsear_ano), errors='coerce')
        meses = pd.to_numeric(aplicar_unicos(df['mes_raw'], parsear_mes), errors='coerce')
        dias = pd.to_numeric(aplicar_unicos(df['dia_raw'], parsear_dia), errors='coerce') if 'dia_raw' in df.columns else pd.Series(1, index=df.index)

        # Fecha año/mes/día; si el día no existe en ese mes (ej. 31/04), se usa el 28, como antes
        hay_ano = anos.notna()
        base_ano = anos.where(hay_ano, 2000)
        f_exacta = pd.to_datetime(pd.DataFrame({'year': base_ano, 'month': meses, 'day': dias}), errors='coerce')
        f_dia28 = pd.to_datetime(pd.DataFrame({'year': base_ano, 'month': meses, 'day': 28}), errors='coerce')
        fechas_fb = f_exacta.fillna(f_dia28).where(hay_ano)
        fechas = fechas.combine_first(fechas_fb)

    df['fecha'] = fechas
    df = df[df['fecha'].notna() & (df['fecha'].dt.year >= 2000)].copy()
    if df.empty:
        return None, "No se pudieron construir fechas válidas a partir de los datos."

    df['ano_num'] = df['fecha'].dt.year.astype(np.int16)
    df['mes_num'] = df['fecha'].dt.month.astype(np.int8)
    anio_txt = df['ano_num'].astype(str)
    df['periodo_orden'] = anio_txt + '-' + df['mes_num'].astype(str).str.zfill(2)
    df['periodo_mes_es'] = df['mes_num'].map(meses_es) + '-' + anio_txt.str[2:]

    # Etiquetas de aeropuertos con sigla oficial estricta
    cache_etiquetas = {}
    def cached_etiqueta(nombre):
        if nombre not in cache_etiquetas:
            cache_etiquetas[nombre] = construir_etiqueta_aeropuerto(nombre)
        return cache_etiquetas[nombre]

    df['origen_label'] = aplicar_unicos(df['origen_raw'], cached_etiqueta)
    df['destino_label'] = aplicar_unicos(df['destino_raw'], cached_etiqueta)

    # Rutas (ambos sentidos) y tramos: las etiquetas se arman una vez por combinación distinta
    # de aeropuertos (unas pocas centenas) en vez de una vez por fila
    pares = pd.DataFrame({'o': df['origen_label'].to_numpy(), 'd': df['destino_label'].to_numpy()})
    cod_par, pares_unicos = pd.factorize(pd.MultiIndex.from_frame(pares))
    o_u = np.array([o for o, _ in pares_unicos], dtype=object)
    d_u = np.array([d for _, d in pares_unicos], dtype=object)
    p1 = np.where(o_u < d_u, o_u, d_u)
    p2 = np.where(o_u < d_u, d_u, o_u)
    ruta_u = pd.Series(p1 + " ⇄ " + p2)
    tramo_u = pd.Series(o_u + " ➔ " + d_u)
    df['ruta_label'] = pd.Series(ruta_u.to_numpy()[cod_par], index=df.index).astype('category')
    df['tramo_label'] = pd.Series(tramo_u.to_numpy()[cod_par], index=df.index).astype('category')
    km_u = np.array([internacional.distancia_km(COORDENADAS.get(str(o)[:3]), COORDENADAS.get(str(d)[:3]))
                     for o, d in zip(o_u, d_u)], dtype=np.float32)
    df['km'] = km_u[cod_par]  # distancia en línea recta, para asientos-km y pasajeros-km

    # Convertir columnas repetitivas a category para reducir la RAM en un 90%
    for c in ['aerolinea', 'origen_label', 'destino_label', 'periodo_orden', 'periodo_mes_es']:
        df[c] = df[c].astype('category')

    cols_finales = [
        'fecha', 'ano_num', 'mes_num', 'periodo_orden', 'periodo_mes_es',
        'aerolinea', 'origen_label', 'destino_label', 'ruta_label', 'tramo_label',
        'pasajeros', 'vuelos', 'asientos', 'km'
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
                    # Las columnas de texto se leen como categorías: los nombres se repiten miles de veces
                    # y así la lectura usa mucha menos memoria (importante en Streamlit Cloud)
                    tipos = {c: 'category' for c in df.columns if df[c].dtype == object}
                    if isinstance(archivo_bytes_o_path, str):
                        df_completo = pd.read_csv(archivo_bytes_o_path, sep=sep, encoding=enc, low_memory=False, dtype=tipos)
                    else:
                        archivo_bytes_o_path.seek(0)
                        df_completo = pd.read_csv(archivo_bytes_o_path, sep=sep, encoding=enc, low_memory=False, dtype=tipos)
                    return df_completo, None
            except Exception:
                continue

    return None, "No se pudo interpretar el archivo (CSV/ZIP/GZ) con las codificaciones habituales."

@st.cache_resource(show_spinner="Cargando la base de datos…")
def cargar_base_repositorio(ruta, modificado):
    """Lee y procesa la base del repositorio una sola vez y la comparte entre visitas.
    'modificado' (fecha del archivo) hace que se vuelva a leer sólo cuando el archivo cambia."""
    df_leido, err = cargar_archivo_en_memoria(ruta)
    if err:
        return None, err
    return procesar_dataframe_oficial(df_leido)


# -------------------------------------------------------------
# CABECERA Y REGLA ESTRICTA CONTRA DATOS INVENTADOS
# -------------------------------------------------------------
st.markdown(
    '<div class="hero">'
    '<h1>✈️ Monitor de Rutas Aéreas de Argentina</h1>'
    '<p>Vuelos de cabotaje y conexiones con el resto de América, con estadísticas oficiales de SINTA (Turismo) y ANAC.</p>'
    '</div>',
    unsafe_allow_html=True
)

# -------------------------------------------------------------
# SELECTOR DE SECCIÓN: cabotaje o internacional (América)
# -------------------------------------------------------------
SECCIONES = ["✈️ Cabotaje", "🌎 Internacional – América"]
if 'seccion' not in st.session_state:
    st.session_state['seccion'] = SECCIONES[1] if st.query_params.get('seccion') == 'internacional' else SECCIONES[0]


def _mantener_seccion():
    # si se vuelve a tocar la sección ya elegida, el control queda vacío: se conserva la anterior
    if not st.session_state.get('seccion'):
        st.session_state['seccion'] = st.session_state.get('_seccion_previa', SECCIONES[0])
    st.session_state['_seccion_previa'] = st.session_state['seccion']


seccion = st.segmented_control("Sección", SECCIONES, key='seccion', on_change=_mantener_seccion,
                               label_visibility='collapsed') or SECCIONES[0]
st.query_params['seccion'] = 'internacional' if seccion == SECCIONES[1] else 'cabotaje'
mostrar_manual(internacional=seccion == SECCIONES[1])

# Utilidades que comparten las dos secciones
UTILES = SimpleNamespace(
    graficar=graficar, config_numerica=config_numerica, tabla=tabla, fmt_entero=fmt_entero, fmt_porcentaje=fmt_porcentaje,
    fmt_decimal=fmt_decimal, meses_es=meses_es, sanitizar_fecha=sanitizar_fecha, restar_ano=restar_ano,
    construir_etiqueta_aeropuerto=construir_etiqueta_aeropuerto, limpiar_mojibake_texto=limpiar_mojibake_texto,
    COORDENADAS=COORDENADAS, COLORES_AEROLINEAS=COLORES_AEROLINEAS, PALETA=PALETA)

if seccion == SECCIONES[1]:
    internacional.mostrar(UTILES)
    st.stop()

# -------------------------------------------------------------
# FUENTE DE DATOS: archivo oficial del repositorio (lo actualiza el agente mensual)
# -------------------------------------------------------------
df_raw = None
fuente_activa = None

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
        df_procesado, err_proc = cargar_base_repositorio(ruta, os.path.getmtime(ruta))
        if not err_proc and df_procesado is not None:
            df_raw = df_procesado
            fuente_activa = f"Repositorio GitHub ({ruta})"
            break

if df_raw is None or df_raw.empty:
    st.error(
        "⛔ **NO HAY DATOS REALES CARGADOS O VÁLIDOS**  \n\n"
        "Esta aplicación tiene **estrictamente prohibido generar, simular o inventar datos**.  \n"
        "Para ver información:  \n"
        "Asegurate de que el archivo oficial `conectividad_aerea.zip` esté en la raíz del repositorio de GitHub."
    )
    st.info("ℹ️ Una vez cargado el archivo oficial con columnas de fecha, aerolínea, origen, destino, pasajeros y vuelos, se habilitará el monitor.")
    st.stop()

# Si hay datos reales cargados:
f_min_total = df_raw['fecha'].min().date()
f_max_total = df_raw['fecha'].max().date()
total_registros = len(df_raw)

st.markdown(
    '<div class="chips" style="margin:-.4rem 0 1.2rem 0;">'
    '<span class="chip" style="background:#e0f2fe;color:#0c4a6e;border-color:#bae6fd;">📡 Fuente: SINTA (Turismo) con datos de ANAC</span>'
    f'<span class="chip" style="background:#e0f2fe;color:#0c4a6e;border-color:#bae6fd;">📅 Datos del {f_min_total.strftime("%d/%m/%Y")} al {f_max_total.strftime("%d/%m/%Y")}</span>'
    '<span class="chip" style="background:#e0f2fe;color:#0c4a6e;border-color:#bae6fd;">🔄 Se actualiza cada mes</span>'
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

def restablecer_filtros():
    st.session_state['sel_origenes_key'] = []
    st.session_state['sel_destinos_key'] = []
    st.session_state['sel_rutas_key'] = []
    st.session_state['sel_aerolineas_key'] = []
    st.session_state['chk_pais_key'] = False
    st.session_state['f_desde_key'] = def_desde
    st.session_state['f_hasta_key'] = def_hasta
    st.session_state['criterios_activos'] = {
        'rutas': [], 'origenes': [], 'destinos': [], 'aerolineas': [],
        'desde': def_desde, 'hasta': def_hasta, 'todo_el_pais': False
    }
    st.session_state['busqueda_activa'] = False


def intercambiar_origen_destino():
    st.session_state['sel_origenes_key'], st.session_state['sel_destinos_key'] = (
        st.session_state.get('sel_destinos_key', []),
        st.session_state.get('sel_origenes_key', [])
    )

if 'busqueda_activa' not in st.session_state:
    st.session_state['busqueda_activa'] = False  # la página abre vacía hasta tocar "Buscar vuelos"
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

# Valores iniciales de los controles del panel (se guardan con clave para poder restablecerlos)
st.session_state.setdefault('chk_pais_key', st.session_state['criterios_activos'].get('todo_el_pais', True))
st.session_state.setdefault('sel_rutas_key', list(st.session_state['criterios_activos'].get('rutas', [])))
st.session_state.setdefault('sel_aerolineas_key', list(st.session_state['criterios_activos'].get('aerolineas', [])))
st.session_state['f_desde_key'] = sanitizar_fecha(st.session_state.get('f_desde_key', def_desde), def_desde, f_min_total, f_max_total)
st.session_state['f_hasta_key'] = sanitizar_fecha(st.session_state.get('f_hasta_key', def_hasta), def_hasta, f_min_total, f_max_total)

# --- Panel de filtros ---
def describir_busqueda(c):
    """Texto corto de lo que se está mostrando."""
    if c.get('todo_el_pais'):
        partes = ["Total país"]
    else:
        partes = []
        if c.get('rutas'):
            partes.append(", ".join(c['rutas']))
        if c.get('origenes'):
            partes.append("desde " + ", ".join(c['origenes']))
        if c.get('destinos'):
            partes.append("hacia " + ", ".join(c['destinos']))
    if c.get('aerolineas'):
        partes.append(", ".join(c['aerolineas']))
    partes.append(f"{c['desde'].strftime('%d/%m/%Y')} al {c['hasta'].strftime('%d/%m/%Y')}")
    return " · ".join(partes)


@st.fragment
def panel_filtros():
    """Tocar un filtro recarga solo este panel (al instante); la página se recalcula con Buscar vuelos o Restablecer."""
    with st.container(border=True):
        col_t1, col_t2 = st.columns([6, 4], vertical_alignment="center")
        with col_t1:
            st.markdown("#### 🔍 Filtros de búsqueda")
        with col_t2:
            chk_pais = st.toggle(
                "Analizar total país (todas las rutas)",
                key='chk_pais_key',
                help="Ignora los filtros de ruta y aeropuertos y analiza todo el cabotaje. La aerolínea y las fechas siguen aplicando."
            )

        # 1. Ruta y aerolínea
        col_r1, col_r2 = st.columns([7, 5])
        with col_r1:
            sel_rutas = st.multiselect(
                "Ruta (ida y vuelta)", options=rutas_disponibles, key='sel_rutas_key',
                placeholder="Elegí uno o más corredores", disabled=chk_pais,
                help="Agrupa ambos sentidos de vuelo del corredor (ej. Aeroparque ⇄ Bariloche incluye idas y vueltas)."
            )
        with col_r2:
            sel_aerolineas = st.multiselect(
                "Aerolínea / operador", options=aerolineas_disponibles, key='sel_aerolineas_key',
                placeholder="Todas", help="Si lo dejás vacío, incluye todas las aerolíneas."
            )

        # 2. Origen ⇄ Destino
        col_orig, col_inv, col_dest = st.columns([10, 2, 10], vertical_alignment="bottom")
        with col_orig:
            st.multiselect("🛫 Origen", options=origenes_disponibles, key='sel_origenes_key',
                           placeholder="Aeropuerto de salida", disabled=chk_pais,
                           help="Filtra los despegues desde este aeropuerto.")
        with col_inv:
            st.button("⇄", on_click=intercambiar_origen_destino, width='stretch',
                      disabled=chk_pais, help="Invertir origen y destino")
        with col_dest:
            st.multiselect("🛬 Destino", options=destinos_disponibles, key='sel_destinos_key',
                           placeholder="Aeropuerto de llegada", disabled=chk_pais,
                           help="Filtra los aterrizajes en este aeropuerto.")

        # 3. Período y acciones
        col_d1, col_d2, col_b1, col_b2 = st.columns([3, 3, 3, 3], vertical_alignment="bottom")
        ayuda_fechas = f"Base disponible: {f_min_total.strftime('%d/%m/%Y')} a {f_max_total.strftime('%d/%m/%Y')}."
        with col_d1:
            f_desde = st.date_input("📅 Desde", key='f_desde_key', min_value=f_min_total, max_value=f_max_total,
                                    format="DD/MM/YYYY", help=ayuda_fechas)
        with col_d2:
            f_hasta = st.date_input("📅 Hasta", key='f_hasta_key', min_value=f_min_total, max_value=f_max_total,
                                    format="DD/MM/YYYY", help=ayuda_fechas)
        f_desde = sanitizar_fecha(f_desde, def_desde, f_min_total, f_max_total)
        f_hasta = sanitizar_fecha(f_hasta, def_hasta, f_min_total, f_max_total)
        with col_b1:
            btn_buscar = st.button("🔍 Buscar vuelos", type="primary", width='stretch')
        with col_b2:
            if st.button("↺ Restablecer", width='stretch', on_click=restablecer_filtros,
                         help="Vuelve a la vista inicial: filtros vacíos y la página sin resultados."):
                st.rerun(scope="app")

        elegidos = {
            'rutas': sel_rutas, 'origenes': st.session_state['sel_origenes_key'],
            'destinos': st.session_state['sel_destinos_key'], 'aerolineas': sel_aerolineas,
            'desde': f_desde, 'hasta': f_hasta, 'todo_el_pais': chk_pais
        }
        if btn_buscar:
            if f_desde > f_hasta:
                st.warning("La fecha inicial es posterior a la final: ajustá el período.")
            elif sel_rutas or elegidos['origenes'] or elegidos['destinos'] or sel_aerolineas or chk_pais:
                st.session_state['criterios_activos'] = elegidos
                st.session_state['busqueda_activa'] = True
                st.rerun(scope="app")
            else:
                st.warning("⚠️ Elegí una ruta, un aeropuerto de origen o destino o una aerolínea (o activá "
                           "'Analizar total país') y tocá 'Buscar vuelos'.")

        activos = st.session_state['criterios_activos']
        if not st.session_state.get('busqueda_activa'):
            st.caption("Todavía no buscaste nada: elegí qué mirar y tocá **🔍 Buscar vuelos**.")
        else:
            st.caption(f"**Mostrando:** {describir_busqueda(activos)}")
            if elegidos != {k: activos.get(k) for k in elegidos}:
                st.caption("Cambiaste filtros: tocá **🔍 Buscar vuelos** para aplicarlos.")


panel_filtros()

# -------------------------------------------------------------
# ESTADO INICIAL EN CERO (SIN PESAR LA PÁGINA)
# -------------------------------------------------------------
st.markdown("---")
st.subheader("📌 Resumen del segmento seleccionado")

if not st.session_state.get('busqueda_activa', False):
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Pasajeros", "0")
    k2.metric("Vuelos", "0")
    k3.metric("Asientos", "0")
    k4.metric("Ocupación", "0,0%")
    k5.metric("Pax / Vuelo", "0,0")
    k6.metric("HHI", "-")

    st.info("💡 **El monitor está listo.** Elegí una **ruta**, un **origen y destino** o una **aerolínea** en los filtros de arriba (o activá **Analizar total país** para ver todo el cabotaje) y tocá **🔍 Buscar vuelos**.")

    tab_g, tab_c, tab_dest, tab_r, tab_e, tab_d = st.tabs([
        "📊 Panorama",
        "⚖️ Competencia",
        "🛬 Destinos y aeropuertos",
        "🗺️ Rutas",
        "📅 Estacionalidad",
        "📋 Datos y descargas"
    ])
    with tab_g:
        st.info("Elegí una ruta o un tramo y tocá 'Buscar vuelos' para visualizar la evolución de oferta, demanda y ocupación.")
    with tab_c:
        st.info("Elegí una ruta o un tramo y tocá 'Buscar vuelos' para ver cuotas de mercado y comparación interanual por aerolínea.")
    with tab_dest:
        st.info("Elegí una ruta o un tramo y tocá 'Buscar vuelos' para ver destinos, aeropuertos y conectividad federal.")
    with tab_r:
        st.info("Elegí una ruta o un tramo y tocá 'Buscar vuelos' para ver el ranking de rutas y el balance entre sentidos.")
    with tab_e:
        st.info("Elegí una ruta o un tramo y tocá 'Buscar vuelos' para ver el comportamiento estacional y los índices de temporada.")
    with tab_d:
        st.info("Elegí una ruta o un tramo y tocá 'Buscar vuelos' para descargar los microdatos y reportes del segmento.")
    mostrar_metodologia(f_min_total, f_max_total)
    st.stop()

# -------------------------------------------------------------
# EJECUCIÓN FILTRADA (INSTANTÁNEA)
# -------------------------------------------------------------
filtros = st.session_state['criterios_activos']
f_d_efectiva = sanitizar_fecha(filtros.get('desde'), def_desde, f_min_total, f_max_total)
f_h_efectiva = sanitizar_fecha(filtros.get('hasta'), def_hasta, f_min_total, f_max_total)
mascara = entre_fechas(df_raw['fecha'], f_d_efectiva, f_h_efectiva)

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
    st.warning("⚠️ No se encontraron vuelos para los criterios seleccionados. Ajustá los filtros y tocá **Buscar vuelos**.")
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
kpi6.metric("HHI", f"{hhi_val:,}".replace(",", "."), delta=hhi_desc, delta_color="off", delta_arrow="off",
            help="Índice Herfindahl-Hirschman sobre pasajeros: menos de 1.500 = competitivo, 1.500 a 2.500 = moderado, más de 2.500 = concentrado.")

# -------------------------------------------------------------
# ESTRUCTURA ORGANIZADA POR PESTAÑAS FUNCIONALES
# -------------------------------------------------------------
tab_panorama, tab_competencia, tab_destinos, tab_rutas, tab_estacionalidad, tab_datos = st.tabs([
    "📊 Panorama",
    "⚖️ Competencia",
    "🛬 Destinos y aeropuertos",
    "🗺️ Rutas",
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
df_rank['Participación'] = df_rank['Pasajeros'] / max(df_rank['Pasajeros'].sum(), 1) * 100
df_rank['Ocupación'] = np.where(df_rank['Asientos'] > 0, df_rank['Pasajeros'] / df_rank['Asientos'] * 100, np.nan)
dias_periodo = dias_operados(df_filtrado)
df_rank['Asientos/vuelo'] = np.where(df_rank['Vuelos'] > 0, df_rank['Asientos'] / df_rank['Vuelos'], np.nan)
df_rank['Vuelos/día'] = df_rank['Vuelos'] / dias_periodo
_km_ruta = df_filtrado.groupby('ruta_label', observed=True)['km'].first()
df_rank['Distancia (km)'] = df_rank['Ruta'].map({str(k): v for k, v in _km_ruta.items()}).round(0)

rutas_suspendidas = []
hay_base_prev = restar_ano(f_d_efectiva) >= f_min_total
df_prev = filtrar_segmento(df_raw, filtros, restar_ano(f_d_efectiva), restar_ano(f_h_efectiva)) if hay_base_prev else df_filtrado.iloc[0:0]
if hay_base_prev:
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

# Para los gráficos por aerolínea: las 8 con más pasajeros y el resto agrupado (leyendas legibles, también en celular)
_top_aero = df_filtrado.groupby('aerolinea', observed=True)['pasajeros'].sum().nlargest(8).index
df_top8 = df_filtrado[['periodo_orden', 'periodo_mes_es', 'aerolinea', 'pasajeros', 'asientos']].copy()
_en_top = df_top8['aerolinea'].isin(_top_aero)
df_top8['aerolinea'] = df_top8['aerolinea'].astype(str).where(_en_top, 'Otras aerolíneas')

# =============================================================
# SECCIÓN 1: GRÁFICOS CON INFORMACIÓN BÁSICA (VERTICALES)
# =============================================================
with tab_panorama:
    # Lo que cambió en el último mes publicado (respeta los filtros de ruta/aerolínea, no el rango de fechas)
    internacional.resumen_ultimo_mes(UTILES, lambda desde, hasta: filtrar_segmento(df_raw, filtros, desde, hasta),
                                     f_min_total, f_max_total, 'ruta_label', cuota_argentina=False)

    st.subheader("Mapa de conexiones")
    cm1, cm2, cm3 = st.columns([2, 3, 3])
    with cm1:
        base_grosor = st.radio("Grosor de las líneas según", ["Pasajeros", "Vuelos"], horizontal=True, key="mapa_metrica")
    with cm2:
        sem_min = st.slider("Frecuencia mínima por ruta (vuelos por semana, ida y vuelta)", min_value=0, max_value=30, value=1,
                            key="mapa_sem", help="Muestra solo las rutas con al menos esta cantidad de vuelos semanales promedio en el período.")
    rutas_mapa = df_filtrado.groupby('ruta_label', observed=True)[['pasajeros', 'vuelos', 'asientos']].sum().reset_index()
    rutas_mapa = rutas_mapa[rutas_mapa['vuelos'] > 0]
    rutas_mapa['ruta'] = rutas_mapa['ruta_label'].astype(str)
    rutas_mapa['a'] = rutas_mapa['ruta'].str[:3]
    rutas_mapa['b'] = rutas_mapa['ruta'].str.split(' ⇄ ').str[1].str[:3]
    rutas_mapa['frec'] = rutas_mapa['vuelos'] / dias_periodo * 7 / 2
    rutas_mapa = rutas_mapa[(rutas_mapa['vuelos'] / dias_periodo * 7 >= sem_min)]
    faltan_coord = (set(rutas_mapa['a']) | set(rutas_mapa['b'])) - set(COORDENADAS)
    rutas_mapa = rutas_mapa[rutas_mapa['a'].isin(COORDENADAS) & rutas_mapa['b'].isin(COORDENADAS)]
    nombres_aero = {str(x)[:3]: str(x) for x in df_filtrado['origen_label'].cat.categories}
    nombres_aero.update({str(x)[:3]: str(x) for x in df_filtrado['destino_label'].cat.categories})
    if rutas_mapa.empty:
        st.info("No hay rutas para mostrar con esa frecuencia mínima. Probá bajarla.")
    else:
        nodos_mapa = mapas.nodos_desde_rutas(rutas_mapa, COORDENADAS, nombres_aero,
                                             {k: ('#475569' if k in AMBA_SIGLAS else '#f59e0b') for k in COORDENADAS})
        orden_nodos = nodos_mapa.sort_values('pasajeros', ascending=False)
        opciones_foco = ["Ninguno"] + orden_nodos['nombre'].tolist()
        if st.session_state.get('mapa_foco') not in opciones_foco:
            st.session_state['mapa_foco'] = "Ninguno"
        with cm3:
            foco_txt = st.selectbox("Destacar las rutas de un aeropuerto", opciones_foco, key='mapa_foco',
                                    help="Pinta de naranja sus rutas y muestra al costado el detalle de cada una.")
        foco = None if foco_txt == "Ninguno" else foco_txt[:3]
        col_mapa, col_top = st.columns([3, 2])
        with col_mapa:
            graficar(mapas.mapa_rutas(rutas_mapa, nodos_mapa, base_grosor == "Pasajeros", foco, 'Argentina'), mapa=True)
        with col_top:
            if foco is None:
                st.markdown("**Principales rutas del período**")
                lado = rutas_mapa.sort_values('pasajeros', ascending=False).head(12)
            else:
                st.markdown(f"**Rutas de {foco_txt}**")
                lado = rutas_mapa[(rutas_mapa['a'] == foco) | (rutas_mapa['b'] == foco)].sort_values('pasajeros', ascending=False)
            top_mapa = pd.DataFrame({
                'Ruta': lado['ruta'].str.replace(r'(\w{3}) \([^⇄]*?\)(?= ⇄|$)', r'\1', regex=True),
                'Pasajeros': lado['pasajeros'].astype(int),
                'Frecuencias semanales': lado['frec'].round(1),
                'Ocupación': (lado['pasajeros'] / lado['asientos'].replace(0, np.nan) * 100).round(1)})
            tabla(top_mapa, width='stretch', hide_index=True, height=470,
                  column_config=config_numerica(top_mapa, porcentajes=('Ocupación',)))
        st.caption(f"{len(rutas_mapa)} rutas y {len(nodos_mapa)} aeropuertos. Arrastrá para mover el mapa y usá la rueda del "
                   "mouse (o dos dedos) para acercarte. Líneas más gruesas = más " + base_grosor.lower() + "; círculos más grandes = "
                   "más movimiento; gris = AMBA, naranja = interior. Pasá el mouse por el medio de una línea para ver el detalle de la ruta.")
    if faltan_coord:
        st.caption("Sin coordenadas, no se muestran: " + ", ".join(sorted(faltan_coord)) + ".")
    st.markdown("---")

    # 1. Oferta vs. demanda vs. ocupación
    st.markdown("#### Oferta, demanda y ocupación")
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
    graficar(fig_od)
    st.caption("Si las barras grises superan mucho a las azules, hay capacidad ociosa; si se igualan y la ocupación se acerca al 100%, la ruta está saturada.")

    st.markdown("---")

    # Evolución anual (usa todos los años de la base; respeta ruta/aeropuertos/aerolínea, no el rango de fechas)
    st.markdown("#### Evolución anual")
    ea1, ea2 = st.columns(2)
    opc_anual = ["Año calendario", f"Acumulado enero–{meses_es[f_max_total.month].lower()}"]
    with ea1:
        med_anual = st.radio("Medir", ["Pasajeros", "Vuelos", "Ocupación", "Pasajeros-km", "Asientos-km"], horizontal=True,
                             key="anual_med", help="Pasajeros-km y asientos-km multiplican por la distancia de cada ruta: miden el "
                                                   "tamaño real del tráfico y de la oferta (un pasajero a Ushuaia pesa más que uno a Rosario).")
    with ea2:
        modo_anual = st.radio("Comparar", opc_anual, horizontal=True, key="anual_modo",
                              help="El acumulado compara los mismos meses de todos los años, para que el año en curso no quede en desventaja.")
    seg_anual = filtrar_segmento(df_raw, filtros, f_min_total, f_max_total)
    if modo_anual != opc_anual[0]:
        seg_anual = seg_anual[seg_anual['mes_num'] <= f_max_total.month]
    seg_anual = seg_anual.assign(pkm=seg_anual['pasajeros'] * seg_anual['km'].fillna(0) / 1e6,
                                 akm=seg_anual['asientos'] * seg_anual['km'].fillna(0) / 1e6)
    g_anual = seg_anual.groupby('ano_num', observed=True)[['pasajeros', 'vuelos', 'asientos', 'pkm', 'akm']].sum().reset_index()
    g_anual['ano_num'] = g_anual['ano_num'].astype(int)
    g_anual['Ocupación'] = np.where(g_anual['asientos'] > 0, g_anual['pasajeros'] / g_anual['asientos'] * 100, np.nan)
    if len(g_anual) < 2:
        st.info("Se necesitan datos de al menos dos años para ver la evolución anual.")
    else:
        col_anual = {'Pasajeros': 'pasajeros', 'Vuelos': 'vuelos', 'Ocupación': 'Ocupación',
                     'Pasajeros-km': 'pkm', 'Asientos-km': 'akm'}[med_anual]
        vals = g_anual[col_anual]
        var_prev = vals.pct_change() * 100
        incompleto = (g_anual['ano_num'] == f_max_total.year) & (modo_anual == opc_anual[0]) & (f_max_total < date(f_max_total.year, 12, 31))
        if med_anual == "Ocupación":
            etiquetas = [fmt_porcentaje(v) for v in vals]
        elif med_anual.endswith("-km"):
            etiquetas = [fmt_entero(v) for v in vals]  # en millones
        else:
            etiquetas = [fmt_entero(v) for v in vals]
        fig_anual = go.Figure(go.Bar(
            x=g_anual['ano_num'].astype(str), y=vals, text=etiquetas, textposition='outside', cliponaxis=False,
            marker=dict(color=PALETA[0], opacity=[0.45 if i else 1 for i in incompleto]),
            customdata=[("s/d" if pd.isna(v) else f"{v:+.1f}%".replace(".", ",")) for v in var_prev],
            hovertemplate='%{x}: %{text}<br>Variación vs. año anterior: %{customdata}<extra></extra>'))
        fig_anual.update_layout(
            height=420, margin=dict(l=20, r=20, t=40, b=40),
            yaxis_title=f"{med_anual} (millones)" if med_anual.endswith("-km") else med_anual,
            yaxis=dict(range=[0, 105]) if med_anual == "Ocupación" else dict(),
            xaxis=dict(type='category'),
            title=f"{med_anual} por año")
        graficar(fig_anual)
        nota_anual = ""
        if incompleto.any():
            nota_anual = f" {f_max_total.year} está incompleto (hasta el {f_max_total.strftime('%d/%m/%Y')}) y se muestra más claro; usá el acumulado para comparar sin sesgo."
        st.caption("Pasá el mouse sobre cada barra para ver la variación contra el año anterior. Respeta los filtros de ruta, aeropuertos y aerolínea; no el rango de fechas." + nota_anual)

    st.markdown("---")

    # Frecuencias y tamaño de aeronave
    st.markdown("#### Frecuencias y tamaño de aeronave")
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

    # escala redonda para el eje de asientos por vuelo (0, 50, 100, 150…)
    max_asientos = float(np.nanmax(g_fq['asientos_vuelo'])) if g_fq['asientos_vuelo'].notna().any() else 1.0
    paso_asientos = 50 if max_asientos > 100 else (20 if max_asientos > 40 else 10)
    tope_asientos = math.ceil(max_asientos * 1.1 / paso_asientos) * paso_asientos
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
        yaxis2=dict(title='Asientos por vuelo', overlaying='y', side='right', showgrid=False,
                    range=[0, tope_asientos], tickmode='linear', tick0=0, dtick=paso_asientos),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0)
    )
    graficar(fig_fq)
    st.caption("Barras: frecuencia operada (vuelos por día). Línea: tamaño promedio de la aeronave. "
               "Si suben las barras, la ruta crece con más frecuencias; si sube la línea, con aviones más grandes.")

with tab_competencia:
    # Participación de mercado en el tiempo (100% apilado)
    st.markdown("#### Participación de mercado, mes a mes")
    df_share = df_top8.groupby(['periodo_orden', 'periodo_mes_es', 'aerolinea'], observed=True)['pasajeros'].sum().reset_index()
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
        graficar(fig_share, leyenda_abajo=True)
        st.caption("Muestra quién gana o pierde cuota a lo largo del tiempo; el HHI de arriba resume la concentración del período.")

    st.markdown("---")

    st.markdown("#### Concentración y cuota de mercado por año")
    if filtros.get('aerolineas'):
        st.info("Con un filtro de aerolínea activo la concentración no es comparable. Quitá el filtro de aerolínea para ver esta sección.")
    else:
        opcion_acum = f"Acumulado enero–{meses_es[f_max_total.month].lower()}"
        modo_hist = st.radio("Comparar", [opcion_acum, "Año completo"], horizontal=True, key="modo_hhi")
        df_hist = filtrar_segmento(df_raw, filtros, f_min_total, f_max_total)
        if modo_hist == opcion_acum:
            df_hist = df_hist[df_hist['mes_num'] <= f_max_total.month]
        g_h = df_hist.groupby(['ano_num', 'aerolinea'], observed=True)['pasajeros'].sum().reset_index()
        g_h['ano_num'] = g_h['ano_num'].astype(int)
        g_h['aerolinea'] = g_h['aerolinea'].astype(str)
        g_h = g_h[g_h['pasajeros'] > 0]
        if g_h['ano_num'].nunique() < 2:
            st.info("Se necesitan datos de al menos dos años para ver la evolución.")
        else:
            g_h['share'] = g_h['pasajeros'] / g_h.groupby('ano_num')['pasajeros'].transform('sum') * 100
            hhi_anio = (g_h['share'] ** 2).groupby(g_h['ano_num']).sum().round(0)

            fig_hhi = go.Figure()
            for y0, y1, color in [(0, 1500, 'rgba(16,185,129,.10)'), (1500, 2500, 'rgba(245,158,11,.12)'), (2500, 10000, 'rgba(239,68,68,.08)')]:
                fig_hhi.add_hrect(y0=y0, y1=y1, fillcolor=color, line_width=0, layer='below')
            fig_hhi.add_scatter(x=[str(a) for a in hhi_anio.index], y=hhi_anio.values, mode='lines+markers+text',
                                text=[fmt_entero(v) for v in hhi_anio.values], textposition='top center',
                                line=dict(color=PALETA[0], width=3), name='HHI',
                                hovertemplate='%{x}: HHI %{y:,.0f}<extra></extra>')
            fig_hhi.update_layout(
                title="Índice de concentración (HHI) por año", height=380, showlegend=False,
                margin=dict(l=20, r=20, t=50, b=40),
                yaxis=dict(range=[0, max(10000, float(hhi_anio.max()) * 1.05)], title='HHI (0 a 10.000)'),
                xaxis=dict(type='category')
            )
            graficar(fig_hhi)
            st.caption("Franjas: verde = competitivo (menos de 1.500), amarillo = moderado (1.500 a 2.500), rojo = concentrado (más de 2.500).")

            # Cuota por aerolínea y año (las aerolíneas con menos de 1% en todos los años se agrupan)
            piv = g_h.pivot_table(index='aerolinea', columns='ano_num', values='share', aggfunc='sum', fill_value=0)
            grandes = piv.index[piv.max(axis=1) >= 1]
            piv_t = piv.loc[grandes].copy()
            otras = piv.drop(index=grandes).sum(axis=0)
            if otras.sum() > 0:
                piv_t.loc['Otras aerolíneas'] = otras
            piv_t = piv_t.sort_values(piv_t.columns[-1], ascending=False).round(1)
            piv_t.columns = [str(c) for c in piv_t.columns]
            piv_t = piv_t.reset_index().rename(columns={'aerolinea': 'Aerolínea', 'index': 'Aerolínea'})
            st.markdown("**Cuota de mercado por aerolínea (% de pasajeros)**")
            tabla(piv_t, width='stretch', hide_index=True,
                         column_config=config_numerica(piv_t, porcentajes=tuple(c for c in piv_t.columns if c != 'Aerolínea')))
            nota_inc = ""
            if modo_hist == "Año completo" and f_max_total.month < 12:
                nota_inc = f" {f_max_total.year} está incompleto (hasta el {f_max_total.strftime('%d/%m/%Y')})."
            st.caption("Cada columna es un año; con “Acumulado” se comparan los mismos meses de todos los años." + nota_inc)
    st.markdown("---")

    # 2. Factor de Ocupación mensual por aerolínea (Curva individual por cada aerolínea)
    st.markdown("#### Ocupación por aerolínea, mes a mes")
    df_mes_ocup = df_top8.groupby(['periodo_orden', 'periodo_mes_es', 'aerolinea'], observed=True).agg(
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
        graficar(fig_line, leyenda_abajo=True)
    else:
        st.info("No se registran asientos ofertados para calcular el factor de ocupación en este segmento.")

    st.markdown("---")

    # Cuadro 2: Desempeño por Aerolínea
    st.subheader("Desempeño por aerolínea")
    df_aero = df_filtrado.groupby('aerolinea', observed=True).agg(
        Pasajeros=('pasajeros', 'sum'),
        Vuelos=('vuelos', 'sum'),
        Asientos=('asientos', 'sum')
    ).reset_index()

    df_aero = df_aero[df_aero['Vuelos'] > 0].sort_values(by='Pasajeros', ascending=False)
    total_pax_seg = df_aero['Pasajeros'].sum()
    df_aero['Participación'] = np.where(total_pax_seg > 0, (df_aero['Pasajeros'] / total_pax_seg) * 100, 0)
    df_aero['Ocupación'] = np.where(df_aero['Asientos'] > 0, (df_aero['Pasajeros'] / df_aero['Asientos']) * 100, np.nan)
    df_aero['Pax / Vuelo'] = np.where(df_aero['Vuelos'] > 0, df_aero['Pasajeros'] / df_aero['Vuelos'], 0)
    df_aero['Asientos / Vuelo'] = np.where(df_aero['Vuelos'] > 0, df_aero['Asientos'] / df_aero['Vuelos'], np.nan)
    df_aero['Vuelos / día'] = df_aero['Vuelos'] / dias_periodo

    df_aero_disp = df_aero.rename(columns={'aerolinea': 'Aerolínea'}).copy()
    cols_dec = ['Participación', 'Ocupación', 'Pax / Vuelo', 'Asientos / Vuelo', 'Vuelos / día']
    df_aero_disp[cols_dec] = df_aero_disp[cols_dec].round(1)
    km_aero = internacional.medir_km(df_filtrado, 'aerolinea')
    nombres_aero = df_aero_disp['Aerolínea'].astype(str)
    df_aero_disp['Asientos-km (millones)'] = nombres_aero.map(km_aero['ask']).round(1)
    df_aero_disp['Pasajeros-km (millones)'] = nombres_aero.map(km_aero['rpk']).round(1)
    df_aero_disp['Cuota de pasajeros-km'] = (df_aero_disp['Pasajeros-km (millones)'] / max(km_aero['rpk'].sum(), 1e-9) * 100).round(1)
    df_aero_disp['Distancia media (km)'] = nombres_aero.map(km_aero['dist']).round(0)
    tabla(
        df_aero_disp, width='stretch', hide_index=True,
        column_config=config_numerica(df_aero_disp, porcentajes=('Participación', 'Ocupación', 'Cuota de pasajeros-km'))
    )
    st.caption("Asientos-km y pasajeros-km = asientos o pasajeros multiplicados por la distancia de cada ruta (en línea recta): "
               "miden el tamaño real de cada aerolínea, porque no pesa lo mismo un pasajero a Ushuaia que uno a Rosario. "
               "Distancia media = kilómetros que vuela en promedio cada pasajero.")

with tab_destinos:
    st.subheader("Ranking de destinos")

    def _por_destino(df):
        g = df.groupby('destino_label', observed=True)[['vuelos', 'pasajeros']].sum()
        g.index = g.index.astype(str)
        return g[g['vuelos'] > 0]

    d_act = _por_destino(df_filtrado)
    d_ant = _por_destino(df_prev) if hay_base_prev else d_act.iloc[0:0]
    if d_act.empty:
        st.info("No hay vuelos para armar el ranking de destinos.")
    else:
        d_act = d_act.sort_values('vuelos', ascending=False)
        pos_ant = d_ant['vuelos'].rank(ascending=False, method='first').astype(int) if hay_base_prev else None
        total_v = d_act['vuelos'].sum()

        filas = []
        for i, (dest, r) in enumerate(d_act.iterrows(), start=1):
            fila = {'Posición': str(i), 'Destino': dest, 'Vuelos': int(r['vuelos']),
                    'Participación': r['vuelos'] / total_v * 100, 'Pasajeros': int(r['pasajeros'])}
            if hay_base_prev:
                v_ant = int(d_ant['vuelos'].get(dest, 0))
                p_ant = pos_ant.get(dest)
                if p_ant is None:
                    cambio = "Nuevo"
                elif p_ant > i:
                    cambio = f"▲ {p_ant - i}"
                elif p_ant < i:
                    cambio = f"▼ {i - p_ant}"
                else:
                    cambio = "="
                fila.update({'Cambio': cambio, 'Vuelos año ant.': v_ant,
                             'Var. %': ((r['vuelos'] - v_ant) / v_ant * 100) if v_ant > 0 else np.nan})
            filas.append(fila)
        df_dest = pd.DataFrame(filas)
        orden_cols = ['Posición', 'Cambio', 'Destino', 'Vuelos', 'Var. %', 'Participación', 'Vuelos año ant.', 'Pasajeros']
        df_dest = df_dest[[c for c in orden_cols if c in df_dest.columns]]
        df_dest[['Participación'] + (['Var. %'] if 'Var. %' in df_dest.columns else [])] = \
            df_dest[['Participación'] + (['Var. %'] if 'Var. %' in df_dest.columns else [])].round(1)

        cfg_dest = config_numerica(df_dest, porcentajes=('Participación',))
        cfg_dest['Posición'] = st.column_config.TextColumn('Posición', width='small')
        if 'Var. %' in df_dest.columns:
            cfg_dest['Var. %'] = st.column_config.NumberColumn('Var. %', format="%+.1f%%")

        top_dest = df_dest.head(15).copy()
        resto = df_dest.iloc[15:]
        if not resto.empty:
            fila_resto = {c: np.nan for c in top_dest.columns}
            fila_resto.update({'Posición': f"16–{len(df_dest)}", 'Destino': f"Resto ({len(resto)} destinos)", 'Vuelos': resto['Vuelos'].sum(),
                               'Participación': round(resto['Participación'].sum(), 1), 'Pasajeros': resto['Pasajeros'].sum()})
            if 'Cambio' in top_dest.columns:
                fila_resto['Cambio'] = ''
                fila_resto['Vuelos año ant.'] = resto['Vuelos año ant.'].sum()
                fila_resto['Var. %'] = round((resto['Vuelos'].sum() - resto['Vuelos año ant.'].sum()) / resto['Vuelos año ant.'].sum() * 100, 1) \
                    if resto['Vuelos año ant.'].sum() > 0 else np.nan
            top_dest = pd.concat([top_dest, pd.DataFrame([fila_resto])], ignore_index=True)

        ver_todos = False
        if len(df_dest) > 15:
            ver_todos = st.toggle(f"Mostrar los {len(df_dest)} destinos", key="dest_todos",
                                  help="Amplía esta misma tabla para ver todos los destinos, sin el grupo «Resto».")
        tabla_dest = df_dest if ver_todos else top_dest
        tabla(tabla_dest, width='stretch', hide_index=True, column_config=cfg_dest,
                     height=int((len(tabla_dest) + 1) * 35 + 3))
        if hay_base_prev:
            st.caption("Vuelos = frecuencias que llegan a cada destino. ▲ ▼ indican posiciones ganadas o perdidas respecto del mismo período del año anterior; "
                       "“Nuevo” = no recibía vuelos entonces. Podés ordenar por cualquier columna.")
        else:
            st.caption("Vuelos = frecuencias que llegan a cada destino. La base no tiene datos del año anterior para este período, por eso no se muestran cambios.")

    st.markdown("---")

    st.subheader("Pasajeros por localidad")

    def _mov_pax(df):
        o = df.groupby('origen_label', observed=True)['pasajeros'].sum()
        d = df.groupby('destino_label', observed=True)['pasajeros'].sum()
        o.index, d.index = o.index.astype(str), d.index.astype(str)
        return o.add(d, fill_value=0)

    m_act = _mov_pax(df_filtrado)
    m_act = m_act[m_act > 0]
    if m_act.empty:
        st.info("No hay pasajeros para el segmento seleccionado.")
    elif not hay_base_prev:
        st.info("La base no tiene datos del año anterior para este período, por eso no se calcula la variación por localidad.")
    else:
        m_ant = _mov_pax(df_prev)
        df_loc = pd.DataFrame({'Localidad': m_act.index,
                               'Pasajeros año ant.': m_ant.reindex(m_act.index).fillna(0).astype(int).values,
                               'Pasajeros': m_act.astype(int).values})
        df_loc['Var. %'] = np.where(df_loc['Pasajeros año ant.'] > 0,
                                    (df_loc['Pasajeros'] - df_loc['Pasajeros año ant.']) / df_loc['Pasajeros año ant.'].replace(0, np.nan) * 100,
                                    np.nan).round(1)
        df_loc['Participación'] = (df_loc['Pasajeros'] / df_loc['Pasajeros'].sum() * 100).round(1)
        df_loc = df_loc.sort_values('Pasajeros', ascending=False).reset_index(drop=True)

        min_loc = st.number_input("Mínimo de pasajeros del año anterior para destacar variaciones", min_value=0,
                                  max_value=10_000_000, value=10000, step=5000, key="min_loc",
                                  help="Evita que localidades con muy poco movimiento aparezcan como las que más crecen o caen.")
        elegibles = df_loc[(df_loc['Pasajeros año ant.'] >= min_loc)].dropna(subset=['Var. %'])
        if len(elegibles) >= 2:
            n_g = min(8, max(1, len(elegibles) // 2))
            destacados = pd.concat([elegibles.nlargest(n_g, 'Var. %'), elegibles.nsmallest(n_g, 'Var. %')]).drop_duplicates('Localidad')
            destacados = destacados.sort_values('Var. %')
            destacados['Tendencia'] = np.where(destacados['Var. %'] >= 0, 'Crece', 'Cae')
            fig_loc = px.bar(
                destacados, x='Var. %', y='Localidad', orientation='h', color='Tendencia',
                color_discrete_map={'Crece': '#10b981', 'Cae': '#ef4444'},
                text=destacados['Var. %'].apply(lambda v: f"{v:+.1f}%".replace(".", ",")),
                title="Localidades que más crecen y más caen (pasajeros que salen + llegan)"
            )
            fig_loc.update_traces(textposition='outside', cliponaxis=False)
            fig_loc.update_layout(height=max(320, 30 * len(destacados) + 100), margin=dict(l=20, r=60, t=50, b=40),
                                  yaxis_title=None, xaxis_ticksuffix='%', showlegend=False)
            graficar(fig_loc)
        else:
            st.info("Ninguna localidad alcanza el mínimo de pasajeros del año anterior; bajá el valor para ver variaciones.")

        df_loc_v = df_loc[['Localidad', 'Pasajeros', 'Var. %', 'Participación', 'Pasajeros año ant.']]
        tabla(df_loc_v, width='stretch', hide_index=True,
                     column_config={**config_numerica(df_loc_v, porcentajes=('Participación',)),
                                    'Var. %': st.column_config.NumberColumn('Var. %', format="%+.1f%%")})
        st.caption(f"Pasajeros que salen y llegan de cada localidad, de {f_d_efectiva.strftime('%d/%m/%Y')} a {f_h_efectiva.strftime('%d/%m/%Y')}, "
                   f"contra el mismo período del año anterior. Un pasajero cuenta en la localidad de origen y en la de destino.")

    st.markdown("---")

    st.subheader("Conectividad federal")
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
        m2.metric("Aeropuertos", fmt_entero(n_aeropuertos))
        m3.metric("Sin pasar por AMBA", fmt_porcentaje(pct_transv),
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
            graficar(fig_fed)

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
        graficar(fig_mov)

with tab_rutas:
    # Cuadro 1: Ranking de rutas
    st.subheader("Ranking de rutas")
    df_rank_disp = df_rank.copy()
    df_rank_disp[['Participación', 'Ocupación', 'Asientos/vuelo', 'Vuelos/día']] = df_rank_disp[['Participación', 'Ocupación', 'Asientos/vuelo', 'Vuelos/día']].round(1)
    if 'Δ% vs año ant.' in df_rank_disp.columns:
        df_rank_disp['Δ% vs año ant.'] = df_rank_disp['Δ% vs año ant.'].round(1)
    tabla(
        df_rank_disp, width='stretch', hide_index=True,
        column_config=config_numerica(df_rank_disp, porcentajes=('Participación', 'Ocupación'))
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

    st.subheader("Rutas activas")
    if len(df_rank) < 3:
        st.info("Seleccioná un segmento con varias rutas (por ejemplo, 'Analizar total país') para ver las rutas activas.")
    else:
        y_ref, m_ref = map(int, str(df_filtrado['periodo_orden'].astype(str).max()).split('-'))
        ini_ref = date(y_ref, m_ref, 1)
        fin_ref = date(y_ref, m_ref, calendar.monthrange(y_ref, m_ref)[1])

        def _rutas_activas(desde, hasta):
            v = filtrar_segmento(df_raw, filtros, desde, hasta).groupby('ruta_label', observed=True)['vuelos'].sum()
            return set(str(r) for r in v[v >= UMBRAL_FRECUENCIAS_MES].index)

        act_set = _rutas_activas(ini_ref, fin_ref)
        hay_ant_mes = restar_ano(ini_ref) >= f_min_total
        ant_set = _rutas_activas(restar_ano(ini_ref), restar_ano(fin_ref)) if hay_ant_mes else set()
        etiqueta_mes = f"{meses_es[m_ref]} {y_ref}"

        c1, c2 = st.columns(2)
        c1.metric(f"Activas {meses_es[m_ref]} {y_ref}", fmt_entero(len(act_set)),
                  delta=(f"{len(act_set) - len(ant_set):+d} vs {meses_es[m_ref]} {y_ref - 1}" if hay_ant_mes else None),
                  help=f"Rutas (ambos sentidos) con al menos {UMBRAL_FRECUENCIAS_MES} vuelos en el mes.")
        c2.metric(f"Activas {meses_es[m_ref]} {y_ref - 1}", fmt_entero(len(ant_set)) if hay_ant_mes else "s/d")

        if hay_ant_mes:
            nuevas_act = sorted(act_set - ant_set)
            dejaron = sorted(ant_set - act_set)
            if nuevas_act:
                with st.expander(f"Pasaron a ser activas ({len(nuevas_act)})"):
                    st.write(" · ".join(nuevas_act))
            if dejaron:
                with st.expander(f"Dejaron de ser activas ({len(dejaron)})"):
                    st.write(" · ".join(dejaron))
        st.caption(f"Se considera ruta activa a la que tuvo al menos {UMBRAL_FRECUENCIAS_MES} vuelos en el mes (ambos sentidos). "
                   "Se mide sobre el último mes del período elegido y respeta los filtros de aerolínea, ruta y aeropuertos.")

    st.markdown("---")

    st.subheader("Dependencia de un solo operador")
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
        c1.metric("Rutas de un operador", f"{int((ops_ruta == 1).sum())} de {len(ops_ruta)}")
        c2.metric("Sus pasajeros", fmt_porcentaje(pax_mono / pax_total * 100 if pax_total > 0 else 0),
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
            tabla(res, width='stretch', hide_index=True,
                         column_config=config_numerica(res, porcentajes=('% de sus pasajeros',)))

            top_mono = g_mono.sort_values('Pasajeros', ascending=False).head(25).rename(columns={'ruta_label': 'Ruta', 'aerolinea': 'Operador único'})
            top_mono['Ocupación'] = np.where(top_mono['Asientos'] > 0, top_mono['Pasajeros'] / top_mono['Asientos'] * 100, np.nan).round(1)
            st.markdown("**Rutas más grandes con un solo operador**")
            tabla(top_mono[['Ruta', 'Operador único', 'Pasajeros', 'Vuelos', 'Ocupación']], width='stretch', hide_index=True,
                         column_config=config_numerica(top_mono[['Ruta', 'Operador único', 'Pasajeros', 'Vuelos', 'Ocupación']], porcentajes=('Ocupación',)))
            st.caption("Son las rutas más frágiles: si esa aerolínea se retira o reduce frecuencias, el corredor queda sin servicio.")

    st.markdown("---")

    # Balance entre sentidos: qué parte de los pasajeros de cada ruta viaja en cada dirección
    st.markdown("#### Balance entre sentidos (ida y vuelta)")
    g_sent = df_filtrado.groupby(['ruta_label', 'origen_label'], observed=True)['pasajeros'].sum().reset_index()
    g_sent['ruta_label'] = g_sent['ruta_label'].astype(str)
    g_sent['origen_label'] = g_sent['origen_label'].astype(str)
    extremos = g_sent['ruta_label'].str.split(' ⇄ ', n=1, expand=True)
    g_sent['primero'] = g_sent['origen_label'] == extremos[0]
    bal = g_sent.pivot_table(index='ruta_label', columns='primero', values='pasajeros', aggfunc='sum', fill_value=0)
    bal = bal.reindex(columns=[True, False], fill_value=0)
    bal.columns = ['pax_1', 'pax_2']
    bal['total'] = bal['pax_1'] + bal['pax_2']
    bal = bal[bal['total'] > 0].sort_values('total', ascending=False).head(15)
    if bal.empty:
        st.info("No hay pasajeros para analizar el balance entre sentidos.")
    else:
        cod = bal.index.to_series().str.split(' ⇄ ', n=1, expand=True)
        a, b = cod[0].str[:3], cod[1].str[:3]
        bal['pct_1'] = bal['pax_1'] / bal['total'] * 100
        bal['pct_2'] = 100 - bal['pct_1']
        bal['etq'] = a + ' ⇄ ' + b
        bal = bal.iloc[::-1]
        fig_bal = go.Figure()
        fig_bal.add_bar(y=bal['etq'], x=bal['pct_1'], orientation='h', name='Sentido de ida (primer aeropuerto → segundo)',
                        marker_color=PALETA[0], text=[f"{x:.0f}%" for x in bal['pct_1']], textposition='inside',
                        customdata=list(zip((a + ' → ' + b).iloc[::-1], bal['pax_1'])),
                        hovertemplate='%{customdata[0]}: %{x:.1f}% (%{customdata[1]:,} pasajeros)<extra></extra>')
        fig_bal.add_bar(y=bal['etq'], x=bal['pct_2'], orientation='h', name='Sentido de vuelta (segundo → primero)',
                        marker_color=PALETA[1], text=[f"{x:.0f}%" for x in bal['pct_2']], textposition='inside',
                        customdata=list(zip((b + ' → ' + a).iloc[::-1], bal['pax_2'])),
                        hovertemplate='%{customdata[0]}: %{x:.1f}% (%{customdata[1]:,} pasajeros)<extra></extra>')
        fig_bal.add_vline(x=50, line_dash='dot', line_color='#475569')
        fig_bal.update_layout(barmode='stack', height=max(260, 34 * len(bal) + 120), margin=dict(l=20, r=20, t=30, b=40),
                              xaxis=dict(range=[0, 100], ticksuffix='%'), yaxis_title=None,
                              legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0))
        graficar(fig_bal)
        st.caption("Rutas con más pasajeros del período. La línea punteada marca el 50%: cerca de ella, la ruta está balanceada. "
                   "Un desbalance marcado suele deberse a flujos de una sola dirección (por ejemplo, inicio o fin de temporada) "
                   "o a vuelos que regresan por otra ruta. Pasá el mouse para ver pasajeros por sentido.")

    st.markdown("---")

    # Cuadro 2: Desempeño por Sentido de Vuelo
    st.subheader("Desempeño por tramo (cada sentido)")
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
    tabla(
        df_t_disp, width='stretch', hide_index=True,
        column_config=config_numerica(df_t_disp, porcentajes=('Ocupación',))
    )

with tab_datos:
    # Cuadro 3: Matriz Mensual Detallada
    st.subheader("Matriz mensual de pasajeros por aerolínea")
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

    tabla(pivot_pax_con_total, width='stretch', column_config=config_numerica(pivot_pax_con_total))
    st.markdown("---")

# =============================================================
# SECCIÓN 3: ESTACIONALIDAD DE LA RUTA (CON SELECTOR DE AÑO)
# =============================================================
with tab_estacionalidad:
    st.markdown("### Estacionalidad de la demanda")
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
    anos_completos_todos = sorted(meses_por_ano[meses_por_ano == 12].index.tolist())
    incluir_pandemia = st.checkbox("Incluir 2020 y 2021 (pandemia)", value=False, key="est_pandemia",
                                   help="La pandemia distorsiona la estacionalidad: en 2020 casi no hubo vuelos entre abril y septiembre. "
                                        "Por eso se excluyen por defecto de las curvas y del promedio histórico.")
    anos_completos = [a for a in anos_completos_todos if incluir_pandemia or a not in (2020, 2021)]
    if not anos_completos:
        anos_completos = anos_completos_todos
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
        graficar(fig_sup)
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
        graficar(fig_dow)

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
                help="Elegí un año para ver sus meses, o el promedio histórico de todos los años disponibles."
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
            subtitulo_tabla = f"Promedio mensual histórico ({cant_anos} años completos" + ("" if incluir_pandemia else ", sin 2020 ni 2021") + ")"
        else:
            ano_int = int(ano_est_sel)
            df_est_base = df_est_total[df_est_total['ano_num'] == ano_int].copy()
            if ano_int not in anos_completos_todos:
                st.caption(f"⚠️ {ano_int} es un año incompleto ({int(meses_por_ano.get(ano_int, 0))} de 12 meses): el índice se calcula sobre los meses disponibles.")
            titulo_graf = f"Curva de Estacionalidad Mensual - Año {ano_int}"
            df_est = df_est_base.groupby('mes_num', observed=True).agg(
                pasajeros=('pasajeros', 'sum'),
                vuelos=('vuelos', 'sum'),
                asientos=('asientos', 'sum')
            ).reset_index()
            subtitulo_tabla = f"Estadísticas mensuales de {ano_int}"

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
                graficar(fig_est)

            with col_est2:
                st.markdown(f"#### {subtitulo_tabla}")
                df_est_disp = pd.DataFrame({
                    'Mes': df_est['mes_nombre'],
                    'Pasajeros': df_est['pasajeros'].round(0),
                    'Vuelos': df_est['vuelos'].round(0),
                    'Ocupación': df_est['ocupacion_%'].round(1),
                    'Índice estacional': df_est['indice_estacionalidad_%'].round(1),
                })
                tabla(
                    df_est_disp, width='stretch', hide_index=True,
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
    st.markdown("### Comparación interanual por aerolínea")
    if not hay_base_prev or df_prev.empty:
        st.info("La base no tiene datos del mismo período del año anterior para comparar.")
    else:
        st.caption(f"Compara el período elegido en los filtros ({f_d_efectiva.strftime('%d/%m/%Y')} al {f_h_efectiva.strftime('%d/%m/%Y')}) "
                   f"con el mismo período del año anterior ({restar_ano(f_d_efectiva).strftime('%d/%m/%Y')} al "
                   f"{restar_ano(f_h_efectiva).strftime('%d/%m/%Y')}). Para comparar otras fechas, cambiá el período arriba.")

        def _por_aero(df):
            g = df.groupby('aerolinea', observed=True)[['pasajeros', 'vuelos', 'asientos']].sum()
            g.index = g.index.astype(str)
            return g[g['vuelos'] > 0]

        comp = _por_aero(df_filtrado).join(_por_aero(df_prev), how='outer', rsuffix='_ant').fillna(0)
        comp['cuota'] = comp['pasajeros'] / max(comp['pasajeros'].sum(), 1) * 100
        comp['cuota_ant'] = comp['pasajeros_ant'] / max(comp['pasajeros_ant'].sum(), 1) * 100
        chicas = (comp['cuota'] < 1) & (comp['cuota_ant'] < 1)
        if chicas.sum() > 1:  # las aerolíneas con menos del 1% en ambos períodos se agrupan
            otras = comp[chicas].sum(numeric_only=True)
            comp = pd.concat([comp[~chicas], otras.to_frame('Otras aerolíneas').T])

        def _pct_txt(v):
            return "Nueva" if pd.isna(v) else f"{v:+.1f}%".replace(".", ",")

        def _ocup(pax, asi):
            return fmt_porcentaje(pax / asi * 100) if asi > 0 else "s/d"

        tabla_yoy = pd.DataFrame({
            'Aerolínea': comp.index,
            'Pasajeros año ant.': comp['pasajeros_ant'].round().astype(int).values,
            'Pasajeros': comp['pasajeros'].round().astype(int).values,
            'Var. %': [_pct_txt((p - pa) / pa * 100 if pa > 0 else np.nan) for p, pa in zip(comp['pasajeros'], comp['pasajeros_ant'])],
            'Cuota año ant.': comp['cuota_ant'].round(1).values,
            'Cuota': comp['cuota'].round(1).values,
            'Cambio de cuota': (comp['cuota'] - comp['cuota_ant']).round(1).values,
            'Vuelos año ant.': comp['vuelos_ant'].round().astype(int).values,
            'Vuelos': comp['vuelos'].round().astype(int).values,
            'Ocupación año ant.': [_ocup(p, a) for p, a in zip(comp['pasajeros_ant'], comp['asientos_ant'])],
            'Ocupación': [_ocup(p, a) for p, a in zip(comp['pasajeros'], comp['asientos'])],
        })
        tabla_yoy['_orden'] = (tabla_yoy['Aerolínea'] == 'Otras aerolíneas').astype(int)
        tabla_yoy = tabla_yoy.sort_values(['_orden', 'Pasajeros'], ascending=[True, False]).drop(columns='_orden')
        cfg_yoy = config_numerica(tabla_yoy, porcentajes=('Cuota año ant.', 'Cuota'))
        cfg_yoy['Cambio de cuota'] = st.column_config.NumberColumn('Cambio de cuota', format="%+.1f pp")
        tabla(tabla_yoy, width='stretch', hide_index=True, column_config=cfg_yoy,
                     height=int((len(tabla_yoy) + 1) * 35 + 3))
        st.caption("Cuota = porcentaje de los pasajeros del segmento. Cambio de cuota = puntos porcentuales (pp) que cada aerolínea "
                   "ganó o perdió. Las aerolíneas con menos del 1% en ambos períodos se agrupan en “Otras aerolíneas”.")

        cambios = tabla_yoy[tabla_yoy['Cambio de cuota'].abs() >= 0.1].sort_values('Cambio de cuota')
        if not cambios.empty:
            st.markdown("#### Quién ganó y quién perdió cuota frente al mismo período del año anterior")
            fig_shift = go.Figure(go.Bar(
                x=cambios['Cambio de cuota'], y=cambios['Aerolínea'], orientation='h',
                marker_color=['#10b981' if v >= 0 else '#ef4444' for v in cambios['Cambio de cuota']],
                text=[f"{v:+.1f} pp".replace(".", ",") for v in cambios['Cambio de cuota']], textposition='outside', cliponaxis=False,
                hovertemplate='%{y}: %{x:+.1f} puntos porcentuales<extra></extra>'))
            fig_shift.update_layout(height=max(240, 40 * len(cambios) + 100), margin=dict(l=20, r=60, t=30, b=40),
                                    xaxis=dict(title='Cambio de cuota (puntos porcentuales)', zeroline=True, zerolinecolor='#94a3b8'),
                                    yaxis_title=None, showlegend=False)
            graficar(fig_shift)

# =============================================================
# SECCIÓN 5: DESCARGAS OFICIALES
# =============================================================
with tab_datos:
    st.markdown("### Descarga de datos filtrados")
    st.markdown("Descargá los microdatos del filtro aplicado para analizarlos en Excel o Python.")

    col_exp1, col_exp2 = st.columns(2)

    def generar_csv(df_f=df_filtrado):
        return df_f.to_csv(index=False, sep=';').encode('utf-8-sig')

    def generar_excel(df_f=df_filtrado, pivot_f=pivot_pax_con_total, aero_f=df_aero):
        salida = io.BytesIO()
        try:
            import xlsxwriter  # noqa: F401  (más rápido que openpyxl para archivos grandes)
            motor = 'xlsxwriter'
        except ImportError:
            motor = 'openpyxl'
        with pd.ExcelWriter(salida, engine=motor) as writer:
            if len(df_f) > 100000:
                df_f.head(100000).to_excel(writer, sheet_name='Microdatos_Muestra', index=False)
            else:
                df_f.to_excel(writer, sheet_name='Microdatos', index=False)
            pivot_f.to_excel(writer, sheet_name='Matriz_Pasajeros')
            aero_f.to_excel(writer, sheet_name='Resumen_Operadores', index=False)
        return salida.getvalue()

    with col_exp1:
        st.download_button(
            label="📥 Descargar Microdatos Oficiales (CSV)",
            data=generar_csv,
            file_name=f"conectividad_oficial_filtrada_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    with col_exp2:
        st.download_button(
            label="📥 Descargar Reporte Completo (Excel)",
            data=generar_excel,
            file_name=f"reporte_conectividad_oficial_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="El archivo se arma al tocar el botón; con muchos datos puede tardar unos segundos."
        )

mostrar_metodologia(f_min_total, f_max_total)
