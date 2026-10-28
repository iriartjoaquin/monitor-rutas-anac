"""
Lectura y limpieza de la base de cabotaje (sin Streamlit).

Lo usa la página (app.py) y también el agente mensual (generar_novedades.py), que corre en GitHub Actions
sin abrir la página.
"""
import io
import re
import zipfile
from collections import Counter
from datetime import datetime, date

import numpy as np
import pandas as pd

import internacional

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


def cargar_cabotaje(ruta):
    """Lee y procesa la base de cabotaje. Devuelve (DataFrame, error)."""
    df_leido, err = cargar_archivo_en_memoria(ruta)
    if err:
        return None, err
    return procesar_dataframe_oficial(df_leido)
