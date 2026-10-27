"""
Sección "Internacional – América": vuelos entre Argentina y el resto de América.

Pensada como herramienta de trabajo para una aerolínea: todas las rutas Argentina ⇄ América, todas las
aerolíneas que las operan, con ficha por ruta, análisis de competidores, capacidad y ocupación, y
oportunidades de mercado. Las rutas se pueden ver por aeropuerto, por ciudad (mercado) o aeropuerto a aeropuerto.

Fuente: tablero de conectividad aérea de SINTA (Ministerio de Turismo) con datos de ANAC, clasificación
"Internacional", filtrado a vuelos cuyo otro extremo está en América. Lo descarga y actualiza el agente
mensual (actualizar_zip.py --tipo internacional) en internacional_america.zip.

La función principal es mostrar(h), donde h trae las utilidades compartidas con la sección de cabotaje.
"""
import os
from datetime import date, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import mapas

ZIP_INTERNACIONAL = "internacional_america.zip"
MESES_NOMBRE = {"Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, "Mayo": 5, "Junio": 6, "Julio": 7,
                "Agosto": 8, "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12}
MESES_CORTOS = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
DIAS_SEMANA = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
AMBA = {'AEP', 'EZE', 'EPA', 'MOR', 'FDO'}

# ---------------------------------------------------------------------------------------------- aerolíneas
# Aerolíneas con certificado argentino. SINTA agrupa a JetSMART en un solo nombre; sus vuelos se reparten entre
# la filial argentina y la chilena con los movimientos de ANAC (ver actualizar_jetsmart.py y _separar_jetsmart).
JETSMART_AR, JETSMART_CL = 'JetSMART Argentina', 'JetSMART Chile'
ARGENTINAS = {'Aerolíneas Argentinas', 'Flybondi', 'Andes Líneas Aéreas', 'LADE - Líneas Aéreas Del Estado',
              'American Jet', 'Flyest', JETSMART_AR}
JETSMART = {'JetSMART Airlines', JETSMART_AR, JETSMART_CL}
REFERENCIA_JETSMART = "jetsmart_operador.csv"
OTRAS = 'Otras aerolíneas'  # en los gráficos de una ruta, el resto de las aerolíneas va junto
MAX_AEROLINEAS_GRAFICO = 6
FUERA_DE_AMERICA = {'Turkish Airlines', 'KLM', 'Emirates Airline', 'Ethiopian Airlines', 'British Airways',
                    'Qatar Airways', 'Swiss International Air Lines', 'Air Europa', 'Lufthansa', 'Iberia Airlines',
                    'ITA Airways', 'Air France', 'Air New Zealand', 'Plus Ultra', 'Icelandair', 'ASL Airlines France'}
GRUPOS = ['Argentinas', 'Extranjeras de América', 'Extranjeras de fuera de América']
COLORES_GRUPO = {'Argentinas': '#1d4ed8', 'Extranjeras de América': '#94a3b8', 'Extranjeras de fuera de América': '#f59e0b'}
COLORES_REGION = {'América del Sur': '#1d4ed8', 'América Central y Caribe': '#10b981', 'América del Norte': '#f59e0b'}
# Colores fijos de las principales aerolíneas internacionales (se suman a los de cabotaje)
COLORES_INTERNACIONALES = {
    OTRAS: '#cbd5e1', JETSMART_AR: '#e11d48', JETSMART_CL: '#fb7185', 'Gol Transportes Aéreos': '#f97316', 'Avianca': '#7c3aed', 'American Airlines': '#0f766e', 'Sky Airline': '#14b8a6',
    'Arajet': '#9f1239', 'United Airlines': '#1e3a8a', 'Delta Air Lines': '#b91c1c', 'Aeroméxico': '#334155',
    'Boliviana de Aviación': '#65a30d', 'Azul Linhas Aereas Brasileiras': '#38bdf8', 'Air Canada': '#dc2626',
    'Paranair': '#a855f7', 'Turkish Airlines': '#be123c', 'Emirates Airline': '#ca8a04', 'KLM': '#0284c7',
    'Ethiopian Airlines': '#15803d', 'Qatar Airways': '#701a75', 'British Airways': '#475569',
}
# País o países "de casa" de cada aerolínea de América. Si vuela a Argentina desde otro país,
# ese tramo es la continuación de un vuelo con escala (ej. Air Canada: Toronto → San Pablo → Buenos Aires).
PAISES_DE_ORIGEN = {
    'LATAM': {'Chile', 'Brasil', 'Perú', 'Colombia', 'Ecuador', 'Paraguay'},
    'Gol Transportes Aéreos': {'Brasil'}, 'Azul Linhas Aereas Brasileiras': {'Brasil'}, 'Copa Airlines': {'Panamá'},
    'American Airlines': {'Estados Unidos'}, 'United Airlines': {'Estados Unidos'}, 'Delta Air Lines': {'Estados Unidos'},
    'Eastern Air Lines': {'Estados Unidos'},
    'Avianca': {'Colombia', 'Ecuador', 'Perú', 'El Salvador', 'Costa Rica', 'Guatemala'},
    'Sky Airline': {'Chile', 'Perú'}, 'Arajet': {'República Dominicana'}, 'Aeroméxico': {'México'},
    'Boliviana de Aviación': {'Bolivia'}, 'Air Canada': {'Canadá'}, 'Paranair': {'Paraguay'},
    'Amaszonas': {'Bolivia', 'Uruguay', 'Paraguay'}, 'Viva Air': {'Colombia', 'Perú'}, 'Estelar Latinoamerica': {'Venezuela'},
    'Cubana de Aviación': {'Cuba'}, 'Conviasa': {'Venezuela'}, 'Latin American Wings': {'Chile'},
    'Aerovías DAP': {'Chile'}, 'Aero Regional Paraguaya': {'Paraguay'}, 'TAME': {'Ecuador'}, 'BQB Líneas Aéreas': {'Uruguay'},
}

# ---------------------------------------------------------------------------------------------- lugares
COORD_CIUDADES = {
    'Santiago|Chile': (-33.39, -70.79), 'São Paulo|Brasil': (-23.43, -46.47), 'Río de Janeiro|Brasil': (-22.81, -43.25),
    'Lima|Perú': (-12.02, -77.11), 'Miami|Estados Unidos': (25.80, -80.29), 'Panamá|Panamá': (9.07, -79.38),
    'Bogotá|Colombia': (4.70, -74.15), 'Nueva York|Estados Unidos': (40.64, -73.78), 'Florianópolis|Brasil': (-27.67, -48.55),
    'Asunción|Paraguay': (-25.24, -57.52), 'Santa Cruz de la Sierra|Bolivia': (-17.65, -63.14), 'Montevideo|Uruguay': (-34.84, -56.03),
    'México DF|México': (19.44, -99.07), 'Houston|Estados Unidos': (29.99, -95.34), 'Atlanta|Estados Unidos': (33.64, -84.43),
    'Punta Cana|República Dominicana': (18.57, -68.36), 'Dallas-Fort Worth|Estados Unidos': (32.90, -97.04),
    'Salvador|Brasil': (-12.91, -38.33), 'Punta del Este|Uruguay': (-34.86, -55.09), 'Cancún|México': (21.04, -86.88),
    'Porto Alegre|Brasil': (-29.99, -51.17), 'Brasilia|Brasil': (-15.87, -47.92), 'Belo Horizonte|Brasil': (-19.62, -43.97),
    'Curitiba|Brasil': (-25.53, -49.18), 'Recife|Brasil': (-8.13, -34.92), 'Porto Seguro|Brasil': (-16.44, -39.08),
    'Medellín|Colombia': (6.16, -75.42), 'Quito|Ecuador': (-0.13, -78.36), 'Natal|Brasil': (-5.77, -35.37),
    'Fortaleza|Brasil': (-3.78, -38.53), 'Maceió|Brasil': (-9.51, -35.79), 'Guayaquil|Ecuador': (-2.16, -79.88),
    'Caracas|Venezuela': (10.60, -66.99), 'Los Angeles|Estados Unidos': (33.94, -118.41), 'Navegantes|Brasil': (-26.88, -48.65),
    'Toronto|Canadá': (43.68, -79.63), 'Foz Do Iguaçu|Brasil': (-25.60, -54.49), 'João Pessoa|Brasil': (-7.15, -34.95),
    'Cabo Frio|Brasil': (-22.92, -42.07), 'Cayo Coco|Cuba': (22.46, -78.33), 'La Habana|Cuba': (22.99, -82.41),
    'Cochabamba|Bolivia': (-17.42, -66.18), 'Manaus|Brasil': (-3.04, -60.05), 'Iquique|Chile': (-20.54, -70.18),
    'Dallas|Estados Unidos': (32.85, -96.85), 'Parnamirim|Brasil': (-5.91, -35.25), 'Porlamar|Venezuela': (10.91, -63.97),
    'Orlando|Estados Unidos': (28.43, -81.31), 'Samana|República Dominicana': (19.27, -69.74), 'La Serena|Chile': (-29.92, -71.20),
    'Concepcion|Chile': (-36.77, -73.06), 'Punta Arenas|Chile': (-53.00, -70.86), 'Pisco|Perú': (-13.75, -76.22),
    'Cartagena|Colombia': (10.44, -75.51), 'Santa Clara|Cuba': (22.49, -79.94), 'Salt Lake City|Estados Unidos': (40.79, -111.98),
    'Alajuela|Costa Rica': (9.99, -84.21), 'Cali|Colombia': (3.54, -76.38), 'Ciudad del Este|Paraguay': (-25.46, -54.84),
    'Santiago de Cuba|Cuba': (19.97, -75.84), 'Barranquilla|Colombia': (10.89, -74.78), 'Arica|Chile': (-18.35, -70.34),
    'La Paz|Bolivia': (-16.51, -68.19), 'Goiânia|Brasil': (-16.63, -49.22), 'Puerto Natales|Chile': (-51.67, -72.53),
    'Calama|Chile': (-22.50, -68.90), 'Fort Lauderdale|Estados Unidos': (26.07, -80.15), 'Puerto Montt|Chile': (-41.44, -73.09),
    'Ocumare del Tuy|Venezuela': (10.12, -66.78), 'Cuiaba|Brasil': (-15.65, -56.12), 'Manta|Ecuador': (-0.95, -80.68),
    'Encarnación|Paraguay': (-27.23, -55.84), 'Montreal|Canadá': (45.47, -73.74), 'Nueva Orleans|Estados Unidos': (29.99, -90.26),
    'Rioja|Perú': (-6.07, -77.16), 'Puerto Maldonado|Perú': (-12.61, -69.23),
    'Oranjestad|Aruba': (12.50, -70.02), 'Santo Domingo|República Dominicana': (18.43, -69.67),
    'Puerto España|Trinidad y Tobago': (10.60, -61.34), 'Antofagasta|Chile': (-23.44, -70.45), 'Holguín|Cuba': (20.79, -76.32),
    'Boa Vista|Brasil': (2.84, -60.69), 'Washington|Estados Unidos': (38.95, -77.45), 'Mérida|México': (20.94, -89.66),
    'Cusco|Perú': (-13.54, -71.94), 'Arequipa|Perú': (-16.34, -71.58), 'Iquitos|Perú': (-3.78, -73.31),
    'Fernando de Noronha|Brasil': (-3.85, -32.42), 'Minera Escondida|Chile': (-24.29, -69.17),
    'São José dos Campos|Brasil': (-23.23, -45.86), 'Campos dos Goytacazes|Brasil': (-21.70, -41.30),
    'San José del Guaviare|Colombia': (2.57, -72.64),
}
COORD_ARG_EXTRA = {'FDO': (-34.45, -58.59)}  # San Fernando (Buenos Aires)

# Aeropuertos que la fuente informa sin ciudad: se les asigna la ciudad a la que sirven
CIUDAD_POR_AEROPUERTO = {
    'Queen Beatrix International Airport': 'Oranjestad', 'Las Américas International Airport': 'Santo Domingo',
    'Piarco International Airport': 'Puerto España', 'Andrés Sabella Gálvez International Airport': 'Antofagasta',
    'Enrique Olaya Herrera Airport': 'Medellín', 'Frank Pais International Airport': 'Holguín',
    'Atlas Brasil Cantanhede Airport': 'Boa Vista', 'Washington Dulles International Airport': 'Washington',
    'Baltimore/Washington International Thurgood Marshall Airport': 'Washington', 'La Escondida Airport': 'Minera Escondida',
    'Montreal / Pierre Elliott Trudeau International Airport': 'Montreal', 'Licenciado Manuel Crescencio Rejon Int Airport': 'Mérida',
    'Alejandro Velasco Astete International Airport': 'Cusco', 'Rodríguez Ballón International Airport': 'Arequipa',
    'Coronel FAP Francisco Secada Vignetta International Airport': 'Iquitos', 'Jorge E. Gonzalez Torres Airport': 'San José del Guaviare',
    'Ponta Pelada Airport': 'Manaus', 'Fernando de Noronha Airport': 'Fernando de Noronha',
    'Pampulha - Carlos Drummond de Andrade Airport': 'Belo Horizonte', 'Santa Cruz Air Force Base': 'Río de Janeiro',
    'Jacarepaguá - Roberto Marinho Airport': 'Río de Janeiro', 'Professor Urbano Ernesto Stumpf Airport': 'São José dos Campos',
    'Bartolomeu Lisandro Airport': 'Campos dos Goytacazes', 'Orlando Sanford International Airport': 'Orlando',
}
# Código IATA de los aeropuertos extranjeros principales (por una parte única de su nombre)
CODIGOS_IATA = [
    ('Merino Ben', 'SCL'), ('Guarulhos', 'GRU'), ('Gale', 'GIG'), ('Santos Dumont', 'SDU'), ('Congonhas', 'CGH'),
    ('Viracopos', 'VCP'), ('Jorge Ch', 'LIM'), ('Miami International', 'MIA'), ('Tocumen', 'PTY'), ('El Dorado', 'BOG'),
    ('Hercílio Luz', 'FLN'), ('Silvio Pettirossi', 'ASU'), ('John F Kennedy', 'JFK'), ('Newark', 'EWR'), ('Viru Viru', 'VVI'),
    ('Carrasco', 'MVD'), ('Benito Juarez', 'MEX'), ('George Bush', 'IAH'), ('Hartsfield', 'ATL'), ('Punta Cana', 'PUJ'),
    ('Dallas Fort Worth', 'DFW'), ('Luiz Eduardo Magalh', 'SSA'), ('Curbelo', 'PDP'), ('Cancún', 'CUN'), ('Salgado Filho', 'POA'),
    ('Juscelino Kubitschek', 'BSB'), ('Tancredo Neves', 'CNF'), ('Afonso Pena', 'CWB'), ('Guararapes', 'REC'),
    ('Porto Seguro', 'BPS'), ('María Córdova', 'MDE'), ('Olaya Herrera', 'EOH'), ('Mariscal Sucre', 'UIO'),
    ('Aluízio Alves', 'NAT'), ('Pinto Martins', 'FOR'), ('Zumbi dos Palmares', 'MCZ'), ('Olmedo', 'GYE'),
    ('Maiquet', 'CCS'), ('Los Angeles International', 'LAX'), ('Victor Konder', 'NVT'), ('Las Américas', 'SDQ'),
    ('Pearson', 'YYZ'), ('Cataratas', 'IGU'), ('Queen Beatrix', 'AUA'), ('Castro Pinto', 'JPA'), ('Cabo Frio', 'CFB'),
    ('Jardines Del Rey', 'CCC'), ('José Martí', 'HAV'), ('Piarco', 'POS'), ('Andrés Sabella', 'ANF'),
    ('Velasco Astete', 'CUZ'), ('Orlando International', 'MCO'), ('Fort Lauderdale', 'FLL'), ('Washington Dulles', 'IAD'),
    ('Diego Aracena', 'IQQ'), ('Juan Santamaría', 'SJO'), ('Rafael Núñez', 'CTG'), ('Eduardo Gomes', 'MAO'),
]


def _combinar(a, b, armar):
    """Arma etiquetas a partir de dos columnas, una vez por combinación distinta (rápido y liviano)."""
    cod, unicos = pd.factorize(pd.MultiIndex.from_arrays([np.asarray(a, dtype=object), np.asarray(b, dtype=object)]))
    etiquetas = np.array([armar(x, y) for x, y in unicos], dtype=object)
    return pd.Categorical(etiquetas[cod])


def _grupo(aerolinea):
    if aerolinea in ARGENTINAS:
        return 'Argentinas'
    if aerolinea in FUERA_DE_AMERICA:
        return 'Extranjeras de fuera de América'
    return 'Extranjeras de América'


def _es_escala(aerolinea, pais):
    """El tramo es la continuación de un vuelo con escala si la aerolínea vuela desde un país que no es el suyo."""
    if aerolinea in ARGENTINAS or aerolinea in JETSMART:  # JetSMART Chile también vuela a Lima o Brasil con su certificado
        return False
    if aerolinea in FUERA_DE_AMERICA:
        return True
    casa = PAISES_DE_ORIGEN.get(aerolinea)
    return bool(casa) and pais not in casa


def _ciudad(localidad, aeropuerto):
    """Ciudad del aeropuerto extranjero; si la fuente no la informa, se deduce del aeropuerto."""
    if isinstance(localidad, str) and localidad.strip():
        return localidad
    nombre = str(aeropuerto)
    if nombre in CIUDAD_POR_AEROPUERTO:
        return CIUDAD_POR_AEROPUERTO[nombre]
    for sufijo in (' International Airport', ' Int Airport', ' Regional Airport', ' Airport'):
        if nombre.endswith(sufijo):
            return 'Aeropuerto ' + nombre[:-len(sufijo)]
    return nombre


def _codigo_aeropuerto(nombre):
    """Código IATA si se conoce; si no, un nombre corto del aeropuerto."""
    nombre = str(nombre)
    for clave, cod in CODIGOS_IATA:
        if clave in nombre:
            return cod
    corto = nombre.split(' - ')[0]
    for sufijo in (' International Airport', ' Int Airport', ' Regional Airport', ' Airport'):
        corto = corto.replace(sufijo, '')
    return corto.replace('Aeropuerto Internacional ', '').strip()


def distancia_km(a, b):
    """Distancia ortodrómica (en línea recta sobre la Tierra) entre dos puntos (lat, lon); NaN si falta alguno."""
    if not a or not b:
        return np.nan
    la1, lo1, la2, lo2 = map(np.radians, (a[0], a[1], b[0], b[1]))
    x = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
    return float(round(6371 * 2 * np.arcsin(np.sqrt(x))))


def _ciudad_argentina(etiqueta):
    """'EZE (Ezeiza)' -> 'Buenos Aires'; 'COR (Córdoba)' -> 'Córdoba'."""
    sigla = etiqueta[:3]
    if sigla in AMBA:
        return 'Buenos Aires'
    i = etiqueta.find('(')
    return etiqueta[i + 1:-1] if i >= 0 else etiqueta


def _separar_jetsmart(empresa, ano, mes, dia, sigla_arg, ciudad, vuelos, referencia):
    """Reparte los vuelos de 'JetSMART Airlines' entre su filial argentina y la chilena.

    Para cada mes, aeropuerto argentino y ciudad extranjera, ANAC dice qué parte de los vuelos hizo cada filial.
    Cada fila (un día de una ruta) se asigna entera a una filial: dentro del grupo, ordenadas por día, las primeras
    filas hasta completar la parte argentina van a JetSMART Argentina y el resto a JetSMART Chile. Así los totales
    por mes y ruta coinciden con ANAC sin partir vuelos en fracciones. Si ANAC no tiene ese mes y ruta, se usa la
    parte de la ciudad en ese mes, después la de la ciudad en el año y después la de la ciudad en toda la serie;
    sin ningún dato (vuelos anteriores a 2019) se asigna a JetSMART Chile, la única filial que volaba a Argentina.
    """
    empresa = np.asarray(empresa, dtype=object).copy()
    es_js = empresa == 'JetSMART Airlines'
    if not es_js.any():
        return empresa
    t = pd.DataFrame({'anio': ano[es_js], 'mes': mes[es_js], 'dia': dia[es_js], 'sigla_arg': sigla_arg[es_js],
                      'ciudad': ciudad[es_js], 'vuelos': vuelos[es_js], 'pos': np.flatnonzero(es_js)})
    t['parte_ar'] = np.nan
    if referencia is not None and not referencia.empty:
        r = referencia.copy()
        for claves in (['anio', 'mes', 'sigla_arg', 'ciudad'], ['anio', 'mes', 'ciudad'], ['anio', 'ciudad'], ['ciudad']):
            g = r.groupby(claves)[['vuelos_ar', 'vuelos_cl']].sum()
            parte = (g['vuelos_ar'] / (g['vuelos_ar'] + g['vuelos_cl'])).rename('p')
            p = t[claves].join(parte, on=claves)['p']
            t['parte_ar'] = t['parte_ar'].fillna(p)
        t.loc[t['anio'] < r['anio'].min(), 'parte_ar'] = 0.0
    t['parte_ar'] = t['parte_ar'].fillna(0.0)
    t = t.sort_values(['anio', 'mes', 'sigla_arg', 'ciudad', 'dia', 'pos'])
    grupo = t.groupby(['anio', 'mes', 'sigla_arg', 'ciudad'], sort=False)['vuelos']
    acumulado, total = grupo.cumsum(), grupo.transform('sum')
    medio = acumulado - t['vuelos'] / 2  # el vuelo "del medio" de la fila
    a_argentina = medio < t['parte_ar'] * total
    empresa[t['pos'].to_numpy()] = np.where(a_argentina, JETSMART_AR, JETSMART_CL)
    return empresa


def _leer_referencia_jetsmart(ruta):
    try:
        return pd.read_csv(ruta, dtype={'sigla_arg': str, 'ciudad': str})
    except (OSError, ValueError):
        return None


@st.cache_resource(show_spinner="Cargando la base internacional…")
def cargar_internacional(ruta, modificado, _etiqueta_aeropuerto, _limpiar_texto, modificado_jetsmart=0, _coord_arg=None):
    """Lee y prepara la base internacional una sola vez (se vuelve a leer sólo si el archivo cambia)."""
    if not os.path.exists(ruta):
        return None
    cols_texto = ['Mes', 'Empresa agrupada', 'Ruta', 'Origen aeropuerto', 'Origen localidad', 'Origen país',
                  'Origen continente', 'Destino aeropuerto', 'Destino localidad', 'Destino país', 'Destino continente']
    df = pd.read_csv(ruta, dtype={c: 'category' for c in cols_texto})
    sale = (df['Origen país'] == 'Argentina').to_numpy()
    llega = (df['Destino país'] == 'Argentina').to_numpy()
    df = df[sale ^ llega].reset_index(drop=True)  # exactamente un extremo en Argentina
    sale = (df['Origen país'] == 'Argentina').to_numpy()

    def lado(col_origen, col_destino, extranjero):
        o, d = df[col_origen].astype(object).to_numpy(), df[col_destino].astype(object).to_numpy()
        return np.where(sale, d, o) if extranjero else np.where(sale, o, d)

    out = pd.DataFrame(index=df.index)
    mes = df['Mes'].map(MESES_NOMBRE).astype(int)
    out['fecha'] = pd.to_datetime(dict(year=df['Año'], month=mes, day=df['Dia']), errors='coerce')
    out['ano_num'] = df['Año'].astype(np.int16)
    out['mes_num'] = mes.astype(np.int8)
    out['dia_semana'] = out['fecha'].dt.dayofweek.fillna(0).astype(np.int8)
    out['periodo_orden'] = _combinar(out['ano_num'], out['mes_num'], lambda y, m: f"{y}-{m:02d}")
    out['periodo_mes_es'] = _combinar(out['ano_num'], out['mes_num'], lambda y, m: f"{MESES_CORTOS[m - 1]}-{str(y)[2:]}")
    aero_arg = lado('Origen aeropuerto', 'Destino aeropuerto', extranjero=False)
    etiquetas_arg = {a: _etiqueta_aeropuerto(a) for a in pd.unique(aero_arg)}
    etiqueta_arg = np.array([etiquetas_arg[a] for a in aero_arg], dtype=object)
    pais = lado('Origen país', 'Destino país', extranjero=True)
    aero_ext = lado('Origen aeropuerto', 'Destino aeropuerto', extranjero=True)
    loc_ext = lado('Origen localidad', 'Destino localidad', extranjero=True)
    ciudad = np.asarray(_combinar(loc_ext, aero_ext, _ciudad), dtype=object)

    aer = df['Empresa agrupada'].astype(object)
    nombres = {a: _limpiar_texto(a) for a in aer.unique()}
    aerolinea = _separar_jetsmart(
        aer.map(nombres).to_numpy(dtype=object), out['ano_num'].to_numpy(), out['mes_num'].to_numpy(),
        df['Dia'].to_numpy(), np.array([e[:3] for e in etiqueta_arg], dtype=object), ciudad,
        pd.to_numeric(df['Vuelos'], errors='coerce').fillna(0).to_numpy(), _leer_referencia_jetsmart(REFERENCIA_JETSMART))
    out['aerolinea'] = pd.Categorical(aerolinea)
    out['grupo'] = pd.Categorical(out['aerolinea'].astype(object).map(_grupo), categories=GRUPOS)
    out['aeropuerto_arg'] = pd.Categorical(etiqueta_arg)
    ciudad_arg = _combinar(etiqueta_arg, etiqueta_arg, lambda e, _: _ciudad_argentina(e))
    out['ciudad_arg'] = ciudad_arg
    codigo = np.asarray(_combinar(aero_ext, aero_ext, lambda a, _: _codigo_aeropuerto(a)), dtype=object)
    out['pais'] = pd.Categorical(pais)
    out['region'] = pd.Categorical(lado('Origen continente', 'Destino continente', extranjero=True))
    out['ciudad_clave'] = _combinar(ciudad, pais, lambda c, p: f"{c}|{p}")
    out['destino'] = _combinar(ciudad, pais, lambda c, p: f"{c} ({p})")
    out['aeropuerto_ext'] = _combinar(codigo, ciudad, lambda a, c: f"{a} ({c})")
    # tres formas de ver una ruta
    out['ruta'] = _combinar(etiqueta_arg, out['destino'].astype(object), lambda a, b: f"{a} ⇄ {b}")
    out['ruta_mercado'] = _combinar(np.asarray(ciudad_arg, dtype=object), out['destino'].astype(object), lambda a, b: f"{a} ⇄ {b}")
    out['ruta_aeropuerto'] = _combinar(np.array([e[:3] for e in etiqueta_arg], dtype=object), out['aeropuerto_ext'].astype(object),
                                       lambda a, b: f"{a} ⇄ {b}")
    out['escala'] = np.asarray(_combinar(aerolinea, pais, lambda a, p: 'si' if _es_escala(a, p) else 'no'), dtype=object) == 'si'
    for c in ['vuelos', 'pasajeros', 'asientos']:
        out[c] = pd.to_numeric(df[c.capitalize()], errors='coerce').fillna(0).astype(np.int32)
    # distancia de la ruta (aeropuerto argentino -> ciudad extranjera), para asientos-km y pasajeros-km
    coord_arg = _coord_arg or {}
    out['km'] = np.asarray(_combinar(np.array([e[:3] for e in etiqueta_arg], dtype=object), out['ciudad_clave'].astype(object),
                                     lambda a, c: distancia_km(coord_arg.get(a), COORD_CIUDADES.get(c))), dtype=float).astype(np.float32)
    return out[out['fecha'].notna()].reset_index(drop=True)


# ---------------------------------------------------------------------------------------------- utilidades
def _filtrar(df, desde, hasta, f):
    m = (df['fecha'] >= pd.Timestamp(desde)) & (df['fecha'] < pd.Timestamp(hasta) + pd.Timedelta(days=1))
    for col, valores in (('region', f['regiones']), ('pais', f['paises']), ('aerolinea', f['aerolineas']),
                         ('grupo', f['grupos']), ('aeropuerto_arg', f['aeropuertos'])):
        if valores:
            m &= df[col].isin(valores)
    return df[m]


def _cuota_arg(df):
    tot = df['pasajeros'].sum()
    return df.loc[df['grupo'] == 'Argentinas', 'pasajeros'].sum() / tot * 100 if tot > 0 else np.nan


def _var(act, ant):
    return (act - ant) / ant * 100 if ant else np.nan


def _txt_var(act, ant):
    """Variación en texto; si el año anterior casi no hubo tráfico, la ruta se considera nueva o reanudada."""
    if ant < max(500, act * 0.05):
        return "Nueva" if ant == 0 else "Nueva o reanudada"
    return f"{_var(act, ant):+.1f}%".replace(".", ",")


def _frecuencia(vuelos, dias):
    """Frecuencias semanales por sentido (un vuelo diario de ida y vuelta = 7)."""
    return vuelos / max(dias, 1) * 7 / 2


def _por(df, col):
    g = df.groupby(col, observed=True).agg(pasajeros=('pasajeros', 'sum'), vuelos=('vuelos', 'sum'),
                                           asientos=('asientos', 'sum')).reset_index()
    g[col] = g[col].astype(str)
    return g.set_index(col)


def _tabla(h, t, porcentajes=(), alto_max=20, **kwargs):
    cfg = h.config_numerica(t, porcentajes=tuple(c for c in porcentajes if c in t.columns))
    for c in t.columns:
        if c.startswith('Δ ocupación') or c.startswith('Cambio de cuota'):
            cfg[c] = st.column_config.NumberColumn(c, format="%+.1f pp")
    h.tabla(t, width='stretch', hide_index=True, column_config=cfg,
                 height=int(max(min(len(t), alto_max), 1) * 35 + 38), **kwargs)


def _ranking(actual, previo, col, hay_prev, dias):
    """Ranking por la columna pedida, con frecuencias, ocupación, variación y cuota argentina."""
    g = _por(actual, col)
    g = g[g['vuelos'] > 0]
    total = max(g['pasajeros'].sum(), 1)
    t = pd.DataFrame({'clave': g.index, 'Pasajeros': g['pasajeros'].values})
    if hay_prev and not previo.empty:
        p = _por(previo, col)['pasajeros']
        ant = np.array([p.get(k, 0) for k in g.index], dtype=float)
        t['Pasajeros año ant.'] = ant.astype(int)
        t['Var. %'] = [_txt_var(a, b) for a, b in zip(g['pasajeros'], ant)]
    t['Frecuencias semanales'] = _frecuencia(g['vuelos'].values, dias).round(1)
    t['Vuelos'] = g['vuelos'].values
    t['Asientos'] = g['asientos'].values
    t['Ocupación'] = np.where(g['asientos'] > 0, g['pasajeros'] / g['asientos'].clip(lower=1) * 100, np.nan).round(1)
    t['Participación'] = (g['pasajeros'].values / total * 100).round(1)
    arg = actual[actual['grupo'] == 'Argentinas'].groupby(col, observed=True)['pasajeros'].sum()
    arg.index = arg.index.astype(str)
    t['Cuota argentina'] = (t['clave'].map(arg).fillna(0) / t['Pasajeros'].replace(0, np.nan) * 100).round(1)
    return t.sort_values('Pasajeros', ascending=False).reset_index(drop=True)


def medir_km(df, col):
    """Asientos-km y pasajeros-km (en millones) por la columna pedida, y distancia media por pasajero."""
    d = df[df['km'].notna()]
    g = pd.DataFrame({'ask': d['asientos'] * d['km'], 'rpk': d['pasajeros'] * d['km'], 'pasajeros': d['pasajeros'],
                      col: d[col]}).groupby(col, observed=True).sum()
    g.index = g.index.astype(str)
    g['dist'] = g['rpk'] / g['pasajeros'].replace(0, np.nan)
    g[['ask', 'rpk']] = g[['ask', 'rpk']] / 1e6
    return g


def _hhi(serie):
    tot = serie.sum()
    return int(round(((serie / tot * 100) ** 2).sum())) if tot > 0 else 0


def _principales(df, n=MAX_AEROLINEAS_GRAFICO):
    """Las n aerolíneas con más pasajeros (para no llenar los gráficos de colores)."""
    return set(df.groupby('aerolinea', observed=True)['pasajeros'].sum().nlargest(n).index.astype(str))


def _agrupar_otras(aerolineas, principales):
    """Deja las aerolíneas principales y junta el resto en «Otras aerolíneas»."""
    a = pd.Series(aerolineas, copy=False).astype(str)
    return a.where(a.isin(principales), OTRAS)


def _lista_aerolineas(df, col):
    """Aerolíneas que operan cada valor de la columna, en texto."""
    s = df[df['pasajeros'] > 0].groupby(col, observed=True)['aerolinea'].agg(lambda x: ", ".join(sorted(set(map(str, x)))))
    s.index = s.index.astype(str)
    return s


# Por defecto, rutas por mercado (ciudad ⇄ ciudad): es la vista estándar para analizar competencia y no se corta
# cuando una aerolínea muda sus vuelos de aeropuerto (por ejemplo, de Aeroparque a Ezeiza)
NIVELES = {"Ciudad ⇄ ciudad (mercado)": 'ruta_mercado', "Aeropuerto argentino ⇄ ciudad": 'ruta',
           "Aeropuerto ⇄ aeropuerto": 'ruta_aeropuerto'}


def _describir(a):
    """Texto corto de lo que se está mostrando."""
    partes = ["Toda América"] if a['todo'] else [", ".join(a['regiones'] + a['paises'] + a['aeropuertos']) or "Toda América"]
    partes += [", ".join(a['grupos'])] if a['grupos'] else []
    partes += [", ".join(a['aerolineas'])] if a['aerolineas'] else []
    partes.append(f"{a['desde'].strftime('%d/%m/%Y')} al {a['hasta'].strftime('%d/%m/%Y')}")
    return " · ".join(partes)


@st.fragment
def _panel_filtros(df, f_min, f_max, def_desde):
    """Tocar un filtro recarga solo este panel (al instante); la página se recalcula con Buscar vuelos o Restablecer."""
    def _restablecer():
        for k in ('int_regiones', 'int_paises', 'int_aerolineas', 'int_grupos', 'int_aeropuertos'):
            st.session_state[k] = []
        st.session_state['int_todo'] = True
        st.session_state['int_desde'], st.session_state['int_hasta'] = def_desde, f_max
        st.session_state['int_nivel'] = list(NIVELES)[0]
        st.session_state['int_aplicado'] = {'todo': True, 'regiones': [], 'paises': [], 'aerolineas': [], 'grupos': [],
                                            'aeropuertos': [], 'desde': def_desde, 'hasta': f_max}

    with st.container(border=True):
        t1, t2 = st.columns([3, 2], vertical_alignment="center")
        t1.markdown("#### 🔍 Filtros")
        todo = t2.toggle("Analizar todas las rutas (toda América)", key='int_todo',
                         help="Ignora los filtros de región, país y aeropuerto argentino. La aerolínea, el tipo de aerolínea y "
                              "las fechas siguen aplicando.")
        c1, c2, c3 = st.columns(3)
        regiones = c1.multiselect("Región", sorted(df['region'].astype(str).unique()), key='int_regiones', placeholder="Toda América",
                                  disabled=todo)
        base_paises = df[df['region'].isin(regiones)] if regiones else df
        paises = c2.multiselect("País", sorted(base_paises['pais'].astype(str).unique()), key='int_paises', placeholder="Todos",
                                disabled=todo)
        grupos = c3.multiselect("Tipo de aerolínea", GRUPOS, key='int_grupos', placeholder="Todas",
                                help="Argentinas: con certificado argentino (incluye JetSMART Argentina; JetSMART Chile cuenta como extranjera). "
                                     "Las de fuera de América llegan con escala en otra ciudad de América.")
        c4, c5, c6, c7 = st.columns([3, 3, 2, 2])
        aerolineas = c4.multiselect("Aerolínea", sorted(df['aerolinea'].astype(str).unique()), key='int_aerolineas', placeholder="Todas")
        aeropuertos = c5.multiselect("Aeropuerto argentino", sorted(df['aeropuerto_arg'].astype(str).unique()), key='int_aeropuertos',
                                     placeholder="Todos", disabled=todo)
        c6.date_input("📅 Desde", key='int_desde', min_value=f_min, max_value=f_max, format="DD/MM/YYYY")
        c7.date_input("📅 Hasta", key='int_hasta', min_value=f_min, max_value=f_max, format="DD/MM/YYYY")
        c8, c9, c10 = st.columns([6, 2, 2], vertical_alignment="bottom")
        buscar = c9.button("🔍 Buscar vuelos", type="primary", width='stretch', key='int_buscar')
        if c10.button("↺ Restablecer", on_click=_restablecer, width='stretch', key='int_reset'):
            st.rerun(scope="app")

        elegidos = {'todo': todo, 'regiones': regiones, 'paises': paises, 'aerolineas': aerolineas, 'grupos': grupos,
                    'aeropuertos': aeropuertos, 'desde': st.session_state['int_desde'], 'hasta': st.session_state['int_hasta']}
        if buscar:
            if elegidos['desde'] > elegidos['hasta']:
                st.warning("La fecha inicial es posterior a la final: ajustá el período.")
            else:
                st.session_state['int_aplicado'] = elegidos
                st.rerun(scope="app")
        aplicado = st.session_state['int_aplicado']
        c8.caption(f"**Mostrando:** {_describir(aplicado)}")
        if elegidos != aplicado:
            st.caption("Cambiaste filtros: tocá **🔍 Buscar vuelos** para aplicarlos.")


# ---------------------------------------------------------------------------------------------- página
def mostrar(h):
    h.COLORES_AEROLINEAS.update(COLORES_INTERNACIONALES)
    df = cargar_internacional(ZIP_INTERNACIONAL, os.path.getmtime(ZIP_INTERNACIONAL) if os.path.exists(ZIP_INTERNACIONAL) else 0,
                              h.construir_etiqueta_aeropuerto, h.limpiar_mojibake_texto,
                              os.path.getmtime(REFERENCIA_JETSMART) if os.path.exists(REFERENCIA_JETSMART) else 0,
                              {**h.COORDENADAS, **COORD_ARG_EXTRA})
    if df is None or df.empty:
        st.info("Todavía no está cargada la base internacional (internacional_america.zip).")
        return

    f_min, f_max = df['fecha'].min().date(), df['fecha'].max().date()
    st.markdown(
        '<div class="chips" style="margin:-.4rem 0 1.2rem 0;">'
        '<span class="chip" style="background:#e0f2fe;color:#0c4a6e;border-color:#bae6fd;">📡 Fuente: SINTA (Turismo) con datos de ANAC</span>'
        f'<span class="chip" style="background:#e0f2fe;color:#0c4a6e;border-color:#bae6fd;">📅 Datos del {f_min.strftime("%d/%m/%Y")} al {f_max.strftime("%d/%m/%Y")}</span>'
        '<span class="chip" style="background:#e0f2fe;color:#0c4a6e;border-color:#bae6fd;">🌎 Todas las rutas entre Argentina y el resto de América</span>'
        '</div>', unsafe_allow_html=True)

    # ------------------------------------------------------------------ filtros
    def_desde = date(f_max.year, 1, 1) if date(f_max.year, 1, 1) >= f_min else f_min
    st.session_state.setdefault('int_desde', def_desde)
    st.session_state.setdefault('int_hasta', f_max)
    st.session_state['int_desde'] = h.sanitizar_fecha(st.session_state['int_desde'], def_desde, f_min, f_max)
    st.session_state['int_hasta'] = h.sanitizar_fecha(st.session_state['int_hasta'], f_max, f_min, f_max)

    st.session_state.setdefault('int_todo', True)
    st.session_state.setdefault('int_aplicado', {'todo': True, 'regiones': [], 'paises': [], 'aerolineas': [], 'grupos': [],
                                                 'aeropuertos': [], 'desde': def_desde, 'hasta': f_max})
    _panel_filtros(df, f_min, f_max, def_desde)
    nivel_txt = st.radio("Ver las rutas como", list(NIVELES), horizontal=True, key='int_nivel',
                         help="Se aplica al instante. Por ciudad suma todos los aeropuertos de cada ciudad: por ejemplo, "
                              "Buenos Aires = Aeroparque + Ezeiza y San Pablo = Guarulhos + Viracopos + Congonhas.")
    rc = NIVELES[nivel_txt]
    aplicado = st.session_state['int_aplicado']

    desde, hasta = aplicado['desde'], aplicado['hasta']
    if desde > hasta:
        st.warning("La fecha inicial es posterior a la final: ajustá el período y tocá Buscar vuelos.")
        return
    filtros = {'regiones': [] if aplicado['todo'] else aplicado['regiones'],
               'paises': [] if aplicado['todo'] else aplicado['paises'],
               'aerolineas': aplicado['aerolineas'], 'grupos': aplicado['grupos'],
               'aeropuertos': [] if aplicado['todo'] else aplicado['aeropuertos']}
    actual = _filtrar(df, desde, hasta, filtros)
    hay_prev = h.restar_ano(desde) >= f_min
    previo = _filtrar(df, h.restar_ano(desde), h.restar_ano(hasta), filtros) if hay_prev else actual.iloc[0:0]
    if actual.empty:
        st.warning("No hay vuelos para los filtros elegidos. Probá ampliar el período o quitar algún filtro.")
        return
    dias = max((hasta - desde).days + 1, 1)

    # ------------------------------------------------------------------ indicadores
    pax, vue, asi = int(actual['pasajeros'].sum()), int(actual['vuelos'].sum()), int(actual['asientos'].sum())
    frec_ciudad = _frecuencia(actual.groupby('destino', observed=True)['vuelos'].sum(), dias)
    st.subheader("📌 Resumen del período")
    k = st.columns(6)
    k[0].metric("Pasajeros", h.fmt_entero(pax))
    k[1].metric("Vuelos", h.fmt_entero(vue))
    k[2].metric("Asientos", h.fmt_entero(asi))
    k[3].metric("Ocupación", h.fmt_porcentaje(pax / asi * 100 if asi else np.nan))
    k[4].metric("Destinos regulares", h.fmt_entero((frec_ciudad >= 1).sum()),
                help=f"Ciudades con al menos una frecuencia semanal (un vuelo por semana en cada sentido) en promedio en el "
                     f"período. Con algún vuelo (incluye chárters, vuelos de temporada y desvíos): {(frec_ciudad > 0).sum()}.")
    k[5].metric("Cuota argentina", h.fmt_porcentaje(_cuota_arg(actual)),
                help="Porcentaje de los pasajeros transportados por aerolíneas argentinas (incluye JetSMART Argentina).")

    tabs = st.tabs(["📊 Panorama", "🛫 Ficha de ruta", "🏢 Competidores", "📦 Capacidad", "💡 Oportunidades",
                    "🏙️ Destinos", "🔁 Escalas", "📋 Datos"])
    with tabs[0]:
        _panorama(h, df, actual, filtros, f_min, f_max, dias, rc)
    with tabs[1]:
        _ficha_ruta(h, df, actual, previo, filtros, rc, nivel_txt, hay_prev, dias, f_min, f_max)
    with tabs[2]:
        _competidores(h, actual, previo, rc, hay_prev, dias)
        _cuota_mensual(h, df, actual, filtros, f_min, f_max)
    with tabs[3]:
        _capacidad(h, actual, previo, rc, hay_prev, dias)
    with tabs[4]:
        _oportunidades(h, actual, previo, rc, hay_prev, dias)
    with tabs[5]:
        _destinos(h, actual, previo, hay_prev, dias)
    with tabs[6]:
        _escalas(h, actual, dias)
    with tabs[7]:
        _datos(actual, f_min, f_max)


# ---------------------------------------------------------------------------------------------- pestañas
def _num(x, signo=False):
    """1234.5 -> '1.235' (o '+1.235')."""
    return f"{x:{'+' if signo else ''},.0f}".replace(",", ".")


def _barras_cambio(serie, etiquetas, sufijo, alto_min=220):
    """Barras horizontales verdes (sube) y rojas (baja), de mayor a menor."""
    serie = serie.sort_values()
    fig = go.Figure(go.Bar(
        x=serie.values, y=serie.index, orientation='h', text=[etiquetas[k] for k in serie.index], textposition='outside',
        cliponaxis=False, marker_color=['#16a34a' if v >= 0 else '#dc2626' for v in serie.values],
        hovertemplate='%{y}: %{text}<extra></extra>'))
    bajo, alto = min(float(serie.min()), 0.0), max(float(serie.max()), 0.0)
    margen = (alto - bajo) * 0.45 or 1.0  # lugar para que las etiquetas no pisen los nombres
    fig.update_layout(height=max(alto_min, 34 * len(serie) + 60), showlegend=False, margin=dict(l=10, r=10),
                      xaxis=dict(title=sufijo, zeroline=True, zerolinecolor='#94a3b8',
                                 range=[bajo - margen if bajo < 0 else 0, alto + margen if alto > 0 else 0]),
                      yaxis=dict(title=''))
    return fig


def _cuota_mensual(h, df, actual, filtros, f_min, f_max):
    """Cuota argentina mes a mes, en total y por país, desde 2017."""
    st.subheader("Cuota argentina mes a mes")
    sin_aer = {**filtros, 'grupos': [], 'aerolineas': []}  # la cuota se calcula sobre todas las aerolíneas
    base = _filtrar(df, f_min, f_max, sin_aer)
    if base.empty:
        st.info("No hay datos con los filtros elegidos.")
        return
    paises_top = (actual.groupby('pais', observed=True)['pasajeros'].sum().sort_values(ascending=False)
                  .index.astype(str)[:12].tolist())
    defecto = [p for p in paises_top[:3]]
    st.session_state.setdefault('int_cuota_paises', defecto)
    st.session_state['int_cuota_paises'] = [p for p in st.session_state['int_cuota_paises'] if p in paises_top]
    elegidos = st.multiselect("Sumar países al gráfico", paises_top, key='int_cuota_paises',
                              help="La línea gruesa es el total; podés sumar la cuota argentina en cada país.")
    arg = base['grupo'] == 'Argentinas'
    m = pd.DataFrame({'periodo': base['periodo_orden'].astype(str), 'pais': base['pais'].astype(str),
                      'total': base['pasajeros'], 'arg': np.where(arg, base['pasajeros'], 0)})
    tot = m.groupby('periodo')[['total', 'arg']].sum()
    fig = go.Figure()
    fig.add_scatter(x=tot.index, y=(tot['arg'] / tot['total'].replace(0, np.nan) * 100).round(1), name='Total',
                    mode='lines', line=dict(color='#1d4ed8', width=3))
    paleta = ['#f97316', '#10b981', '#a855f7', '#ef4444', '#0ea5e9', '#ca8a04', '#64748b', '#db2777']
    por_pais = m[m['pais'].isin(elegidos)].groupby(['pais', 'periodo'])[['total', 'arg']].sum()
    for i, pais in enumerate(elegidos):
        if pais not in por_pais.index.get_level_values(0):
            continue
        t = por_pais.loc[pais]
        fig.add_scatter(x=t.index, y=(t['arg'] / t['total'].replace(0, np.nan) * 100).round(1), name=pais, mode='lines',
                        line=dict(color=paleta[i % len(paleta)], width=1.6))
    if '2020-03' in tot.index and '2021-10' in tot.index:
        fig.add_vrect(x0='2020-03', x1='2021-10', fillcolor='#e2e8f0', opacity=0.5, line_width=0, layer='below',
                      annotation_text='Pandemia', annotation_position='top left', annotation_font_color='#64748b')
    fig.update_layout(height=400, yaxis=dict(title='Cuota argentina', ticksuffix='%', rangemode='tozero'),
                      xaxis=dict(title='', type='category', nticks=20, tickangle=-45), hovermode='x unified')
    h.graficar(fig, leyenda_abajo=True)
    st.caption("Parte de los pasajeros llevada por aerolíneas argentinas (incluye JetSMART Argentina), cada mes desde 2017. "
               "Respeta los filtros de región, país y aeropuerto, pero no los de aerolínea ni tipo de aerolínea (la cuota siempre "
               "se mide sobre todas). En la pandemia (zona gris) casi no hubo vuelos y los saltos son vuelos especiales de repatriación.")
    st.markdown("---")


def _resumen_mes(h, df, filtros, f_min, f_max, rc):
    resumen_ultimo_mes(h, lambda desde, hasta: _filtrar(df, desde, hasta, filtros), f_min, f_max, rc)


def resumen_ultimo_mes(h, filtrar, f_min, f_max, rc, cuota_argentina=True):
    """Lo que cambió en el último mes publicado: el bloque que se mira cuando sale un mes nuevo.

    filtrar(desde, hasta) devuelve la base con los filtros de la página aplicados. Lo usan las dos secciones:
    en cabotaje (cuota_argentina=False) la quinta tarjeta muestra la concentración del mercado (HHI).
    """
    ini_u = date(f_max.year, f_max.month, 1)
    mes_txt = f"{h.meses_es[f_max.month]} {f_max.year}"
    u = filtrar(ini_u, f_max)
    hay_ly = h.restar_ano(ini_u) >= f_min
    up = filtrar(h.restar_ano(ini_u), h.restar_ano(f_max)) if hay_ly else u.iloc[0:0]
    ini_m = (pd.Timestamp(ini_u) - pd.DateOffset(months=1)).date()
    um = filtrar(ini_m, ini_u - timedelta(days=1)) if ini_m >= f_min else u.iloc[0:0]
    mes_ant_txt = f"{h.meses_es[ini_m.month]} {ini_m.year}"
    ly_txt = f"{h.meses_es[f_max.month]} {f_max.year - 1}"

    st.subheader(f"📰 Resumen de {mes_txt}, el último mes publicado")
    if u.empty:
        st.info("Los filtros elegidos no tienen vuelos en el último mes publicado.")
        st.markdown("---")
        return

    def _d(a, b):
        return None if up.empty or not b else f"{_var(a, b):+.1f}%".replace(".", ",")
    pax, asi = u['pasajeros'].sum(), u['asientos'].sum()
    uc = st.columns(5)
    uc[0].metric("Vuelos", h.fmt_entero(u['vuelos'].sum()), delta=_d(u['vuelos'].sum(), up['vuelos'].sum()))
    uc[1].metric("Pasajeros", h.fmt_entero(pax), delta=_d(pax, up['pasajeros'].sum()))
    uc[2].metric("Asientos", h.fmt_entero(asi), delta=_d(asi, up['asientos'].sum()))
    oc = pax / asi * 100 if asi else np.nan
    ocp = up['pasajeros'].sum() / up['asientos'].sum() * 100 if not up.empty and up['asientos'].sum() else np.nan
    uc[3].metric("Ocupación", h.fmt_porcentaje(oc), delta=None if pd.isna(ocp) else f"{oc - ocp:+.1f} pp".replace(".", ","))
    if cuota_argentina:
        ca, cp = _cuota_arg(u), _cuota_arg(up) if not up.empty else np.nan
        uc[4].metric("Cuota argentina", h.fmt_porcentaje(ca), delta=None if pd.isna(cp) else f"{ca - cp:+.1f} pp".replace(".", ","))
    else:
        hh = _hhi(u.groupby('aerolinea', observed=True)['pasajeros'].sum())
        hp = _hhi(up.groupby('aerolinea', observed=True)['pasajeros'].sum()) if not up.empty else None
        uc[4].metric("HHI", h.fmt_entero(hh), delta=None if hp is None else _num(hh - hp, True), delta_color="inverse",
                     help="Concentración del mercado (0 a 10.000; más de 2.500 = concentrado). Si sube, hay menos competencia.")
    st.caption(f"Del {ini_u.strftime('%d/%m/%Y')} al {f_max.strftime('%d/%m/%Y')}, comparado con {ly_txt} "
               "(el mismo mes del año anterior, para no confundir cambios con temporada). Respeta los filtros, salvo las fechas.")

    # 1) aerolíneas: capacidad y cuota contra el mismo mes del año anterior
    if not up.empty:
        a, b = _por(u, 'aerolinea'), _por(up, 'aerolinea')
        t = a[['asientos', 'pasajeros']].join(b[['asientos', 'pasajeros']], rsuffix='_ant', how='outer').fillna(0)
        t['d_asientos'] = t['asientos'] - t['asientos_ant']
        t['d_cuota'] = t['pasajeros'] / max(t['pasajeros'].sum(), 1) * 100 - t['pasajeros_ant'] / max(t['pasajeros_ant'].sum(), 1) * 100
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Quién agregó o sacó asientos")
            cambio = t.loc[t['d_asientos'] != 0, 'd_asientos']
            cambio = cambio.loc[cambio.abs().sort_values(ascending=False).index[:8]]
            if cambio.empty:
                st.caption("Nadie cambió su capacidad.")
            else:
                etiq = {k: _num(v, True) + (f" ({_var(t.at[k, 'asientos'], t.at[k, 'asientos_ant']):+.0f}%)"
                                             if t.at[k, 'asientos_ant'] else " (nueva)") for k, v in cambio.items()}
                h.graficar(_barras_cambio(cambio, etiq, f"Asientos frente a {ly_txt}"))
        with c2:
            st.markdown(f"#### Quién ganó o perdió cuota frente a {ly_txt}")
            cambio = t['d_cuota'].round(1)
            cambio = cambio[cambio != 0]
            cambio = cambio.loc[cambio.abs().sort_values(ascending=False).index[:8]]
            if cambio.empty:
                st.caption("Las cuotas no cambiaron.")
            else:
                etiq = {k: f"{v:+.1f} pp".replace(".", ",") for k, v in cambio.items()}
                h.graficar(_barras_cambio(cambio, etiq, f"Puntos de cuota de pasajeros frente a {ly_txt}"))
        st.caption("Las 8 aerolíneas con el cambio más grande. Asientos: diferencia de asientos ofrecidos (entre paréntesis, en %). "
                   "Cuota: puntos porcentuales de participación en los pasajeros.")

    # 2) aerolíneas que empezaron o dejaron de volar una ruta, contra el mes anterior
    if not um.empty:
        st.markdown(f"#### Novedades frente a {mes_ant_txt}: quién empezó o dejó de volar cada ruta")
        ahora = u.groupby([rc, 'aerolinea'], observed=True)[['vuelos', 'pasajeros']].sum()
        antes = um.groupby([rc, 'aerolinea'], observed=True)[['vuelos', 'pasajeros']].sum()
        m = ahora.join(antes, rsuffix='_ant', how='outer').fillna(0).reset_index()
        m[rc], m['aerolinea'] = m[rc].astype(str), m['aerolinea'].astype(str)
        altas = m[(m['vuelos'] >= 4) & (m['vuelos_ant'] == 0)].sort_values('pasajeros', ascending=False)
        bajas = m[(m['vuelos_ant'] >= 4) & (m['vuelos'] == 0)].sort_values('pasajeros_ant', ascending=False)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**🟢 Empezaron a volar ({len(altas)})**")
            if altas.empty:
                st.caption("Ninguna aerolínea empezó a volar una ruta nueva para ella.")
            else:
                _tabla(h, altas.rename(columns={'aerolinea': 'Aerolínea', rc: 'Ruta', 'vuelos': 'Vuelos', 'pasajeros': 'Pasajeros'})[
                    ['Aerolínea', 'Ruta', 'Vuelos', 'Pasajeros']].astype({'Vuelos': int, 'Pasajeros': int}), alto_max=8)
        with c2:
            st.markdown(f"**🔴 Dejaron de volar ({len(bajas)})**")
            if bajas.empty:
                st.caption("Ninguna aerolínea dejó de volar una ruta.")
            else:
                _tabla(h, bajas.rename(columns={'aerolinea': 'Aerolínea', rc: 'Ruta', 'vuelos_ant': f'Vuelos en {mes_ant_txt}',
                                                'pasajeros_ant': f'Pasajeros en {mes_ant_txt}'})[
                    ['Aerolínea', 'Ruta', f'Vuelos en {mes_ant_txt}', f'Pasajeros en {mes_ant_txt}']].astype(
                    {f'Vuelos en {mes_ant_txt}': int, f'Pasajeros en {mes_ant_txt}': int}), alto_max=8)
        st.caption(f"Aerolíneas con al menos 4 vuelos en una ruta en {mes_txt} que no la volaron en {mes_ant_txt}, y al revés. "
                   "Acá se compara con el mes anterior para ver los cambios apenas pasan; pueden ser rutas de temporada.")

    # 3) rutas: las que más cambiaron y las más llenas o vacías
    rt = _por(u, rc)
    rt = rt[(rt['vuelos'] >= 8) & (rt['pasajeros'] >= 3000)]
    if not rt.empty:
        c1, c2 = st.columns(2)
        if not up.empty:
            with c1:
                st.markdown("#### Rutas que más crecieron y más cayeron")
                rp = _por(up, rc)['pasajeros']
                v = pd.DataFrame({'Ruta': rt.index, 'Pasajeros': rt['pasajeros'].values,
                                  f'Pasajeros {f_max.year - 1}': [int(rp.get(k, 0)) for k in rt.index]})
                v = v[v[f'Pasajeros {f_max.year - 1}'] >= 3000]
                v['Δ% pasajeros'] = ((v['Pasajeros'] / v[f'Pasajeros {f_max.year - 1}'] - 1) * 100).round(1)
                v = v.sort_values('Δ% pasajeros', ascending=False)
                cambio = pd.concat([v.head(5), v.tail(5)]).drop_duplicates('Ruta')
                _tabla(h, cambio, alto_max=10)
                st.caption(f"Las 5 que más crecieron y las 5 que más cayeron frente a {ly_txt}, entre las rutas con al menos 3.000 "
                           "pasajeros en los dos meses.")
        with c2:
            st.markdown("#### Rutas más llenas y más vacías")
            o = pd.DataFrame({'Ruta': rt.index, 'Pasajeros': rt['pasajeros'].values,
                              'Ocupación': (rt['pasajeros'] / rt['asientos'].replace(0, np.nan) * 100).round(1).values})
            if not up.empty:
                pp = _por(up, rc)
                ant = (pp['pasajeros'] / pp['asientos'].replace(0, np.nan) * 100)
                o['Δ ocupación (pp)'] = (o['Ocupación'] - o['Ruta'].map(ant)).round(1)
            o = o.dropna(subset=['Ocupación']).sort_values('Ocupación', ascending=False)
            _tabla(h, pd.concat([o.head(5), o.tail(5)]).drop_duplicates('Ruta'), porcentajes=('Ocupación',), alto_max=10)
            st.caption("Las 5 rutas con más ocupación y las 5 con menos, entre las que tuvieron al menos 8 vuelos y 3.000 pasajeros. "
                       f"Δ ocupación: puntos frente a {ly_txt}.")
    st.markdown("---")


def _panorama(h, df, actual, filtros, f_min, f_max, dias, rc):
    _resumen_mes(h, df, filtros, f_min, f_max, rc)

    st.subheader("Mapa de conexiones")
    mc1, mc2, mc3 = st.columns([2, 2, 3])
    grosor = mc1.radio("Grosor de las líneas según", ["Pasajeros", "Vuelos"], horizontal=True, key="int_mapa_metrica")
    vista = mc2.radio("Encuadre", ["Sudamérica", "Toda América"], horizontal=True, key="int_mapa_vista",
                      help="Dónde arranca el mapa. Después se puede mover y acercar libremente.")
    sem_min = mc3.slider("Frecuencia mínima por ruta (vuelos semanales, ida y vuelta)", 0, 30, 1, key="int_mapa_sem",
                         help="Muestra solo las rutas con al menos esta cantidad de vuelos semanales promedio en el período.")
    rutas, nodos, faltan = _rutas_mapa(actual, h, sem_min, dias)
    if nodos is None:
        st.info("No hay rutas para mostrar con esa frecuencia mínima. Probá bajarla.")
    else:
        opciones = ["Ninguno"] + nodos.sort_values('pasajeros', ascending=False)['nombre'].tolist()
        if st.session_state.get('int_mapa_foco') not in opciones:
            st.session_state['int_mapa_foco'] = "Ninguno"
        foco_txt = st.selectbox("Destacar las rutas de un aeropuerto argentino o de una ciudad", opciones, key='int_mapa_foco',
                                help="Pinta de naranja sus rutas y muestra al costado el detalle de cada una.")
        foco = None if foco_txt == "Ninguno" else nodos.index[nodos['nombre'] == foco_txt][0]
        cm, ct = st.columns([3, 2])
        with cm:
            h.graficar(mapas.mapa_rutas(rutas, nodos, grosor == "Pasajeros", foco, vista), mapa=True)
        with ct:
            if foco is None:
                st.markdown("**Principales rutas del período**")
                lado = rutas.sort_values('pasajeros', ascending=False).head(12)
            else:
                st.markdown(f"**Rutas de {foco_txt}**")
                lado = rutas[(rutas['a'] == foco) | (rutas['b'] == foco)].sort_values('pasajeros', ascending=False)
            t = pd.DataFrame({'Ruta': lado['a'] + ' ⇄ ' + lado['destino'], 'Pasajeros': lado['pasajeros'].astype(int),
                              'Frecuencias semanales': lado['frec'].round(1),
                              'Ocupación': (lado['pasajeros'] / lado['asientos'].replace(0, np.nan) * 100).round(1)})
            h.tabla(t, width='stretch', hide_index=True, height=470,
                    column_config=h.config_numerica(t, porcentajes=('Ocupación',)))
        st.caption(f"{len(rutas)} conexiones entre aeropuertos argentinos y {int(nodos.index.str.contains('|', regex=False).sum())} ciudades de América. "
                   "Arrastrá para mover el mapa y usá la rueda del mouse (o dos dedos) para acercarte. Líneas más gruesas = más "
                   f"{grosor.lower()}; ciudades en azul: Sudamérica, verde: Centroamérica y Caribe, naranja: Norteamérica; gris: "
                   "aeropuertos argentinos. Pasá el mouse por el medio de una línea para ver el detalle de la ruta.")
    if faltan:
        st.caption("Sin coordenadas, no se muestran: " + ", ".join(sorted(faltan)) + ".")
    st.markdown("---")

    st.markdown("#### Pasajeros por mes según tipo de aerolínea")
    g = actual.groupby(['periodo_orden', 'periodo_mes_es', 'grupo'], observed=True)['pasajeros'].sum().reset_index()
    for c in ('periodo_orden', 'periodo_mes_es', 'grupo'):
        g[c] = g[c].astype(str)
    g = g.sort_values('periodo_orden')
    fig = px.bar(g, x='periodo_mes_es', y='pasajeros', color='grupo', color_discrete_map=COLORES_GRUPO,
                 category_orders={'periodo_mes_es': g.drop_duplicates('periodo_orden')['periodo_mes_es'].tolist(), 'grupo': GRUPOS},
                 labels={'periodo_mes_es': 'Período', 'pasajeros': 'Pasajeros', 'grupo': ''})
    fig.update_layout(xaxis_tickangle=-45, height=440)
    h.graficar(fig, leyenda_abajo=True)
    st.markdown("---")

    st.markdown("#### Evolución anual")
    opc = ["Año calendario", f"Acumulado enero–{h.meses_es[f_max.month].lower()}"]
    modo = st.radio("Comparar", opc, horizontal=True, key="int_anual_modo",
                    help="El acumulado compara los mismos meses de todos los años, para que el año en curso no quede en desventaja.")
    base_a = _filtrar(df, f_min, f_max, filtros)
    if modo != opc[0]:
        base_a = base_a[base_a['mes_num'] <= f_max.month]
    medidas = {"Pasajeros": None, "Pasajeros-km": 'pasajeros', "Asientos-km": 'asientos'}
    medida = st.radio("Medir en", list(medidas), horizontal=True, key="int_anual_medida",
                      help="Pasajeros-km y asientos-km multiplican por la distancia de cada ruta: miden el tamaño real del tráfico "
                           "y de la oferta (un pasajero a Miami pesa más que uno a Montevideo).")
    base_m = base_a.assign(valor=base_a['pasajeros'] if medidas[medida] is None
                           else base_a[medidas[medida]] * base_a['km'].fillna(0) / 1e6)
    ga = base_m.groupby(['ano_num', 'grupo'], observed=True)['valor'].sum().reset_index()
    ga['ano_num'], ga['grupo'] = ga['ano_num'].astype(str), ga['grupo'].astype(str)
    eje = 'Pasajeros' if medidas[medida] is None else f"{medida} (millones)"
    fig = px.bar(ga, x='ano_num', y='valor', color='grupo', color_discrete_map=COLORES_GRUPO,
                 category_orders={'grupo': GRUPOS}, labels={'ano_num': 'Año', 'valor': eje, 'grupo': ''})
    incompleto = modo == opc[0] and f_max.month < 12
    if incompleto:  # el año en curso, más claro
        for tr in fig.data:
            tr.marker.opacity = [0.45 if x == str(f_max.year) else 1 for x in tr.x]
    fig.update_layout(height=420, xaxis=dict(type='category'))
    h.graficar(fig, leyenda_abajo=True)
    nota = f" {f_max.year} está incompleto (hasta el {f_max.strftime('%d/%m/%Y')}) y se muestra más claro." if incompleto else ""
    st.caption("Respeta los filtros, salvo las fechas: muestra todos los años de la base." + nota)
    st.markdown("---")

    st.subheader("Puertas de entrada: aeropuertos argentinos")
    pa = _ranking(actual, actual.iloc[0:0], 'aeropuerto_arg', False, dias).rename(columns={'clave': 'Aeropuerto'})
    ciudades = actual[actual['pasajeros'] > 0].groupby('aeropuerto_arg', observed=True)['destino'].nunique()
    ciudades.index = ciudades.index.astype(str)
    pa.insert(2, 'Ciudades conectadas', pa['Aeropuerto'].map(ciudades).fillna(0).astype(int))
    fuera = actual[~actual['aeropuerto_arg'].astype(str).str[:3].isin(AMBA)]['pasajeros'].sum() / max(actual['pasajeros'].sum(), 1) * 100
    st.metric("Pasajeros que usan aeropuertos fuera de Buenos Aires", h.fmt_porcentaje(fuera),
              help="Parte de los pasajeros internacionales a América que salen o llegan por aeropuertos del interior.")
    _tabla(h, pa[['Aeropuerto', 'Pasajeros', 'Ciudades conectadas', 'Frecuencias semanales', 'Ocupación', 'Participación',
                  'Cuota argentina']], porcentajes=('Ocupación', 'Participación', 'Cuota argentina'), alto_max=12)
    base_f = _filtrar(df, f_min, f_max, filtros)
    base_f = base_f[base_f['mes_num'] <= f_max.month]
    interior = ~base_f['aeropuerto_arg'].astype(str).str[:3].isin(AMBA)
    tot_anio = base_f.groupby('ano_num')['pasajeros'].sum()
    int_anio = base_f[interior].groupby('ano_num')['pasajeros'].sum().reindex(tot_anio.index, fill_value=0)
    serie = (int_anio / tot_anio.clip(lower=1) * 100)
    if len(serie) > 1:
        fig = go.Figure(go.Scatter(x=serie.index.astype(str), y=serie.values, mode='lines+markers+text',
                                   text=[f"{v:.1f}%".replace(".", ",") for v in serie.values], textposition='top center',
                                   line=dict(color=h.PALETA[0], width=3)))
        fig.update_layout(height=320, yaxis=dict(ticksuffix='%', rangemode='tozero'), xaxis=dict(type='category'),
                          yaxis_title='% fuera de Buenos Aires')
        h.graficar(fig)
        st.caption(f"Porcentaje de pasajeros por aeropuertos del interior, enero–{h.meses_es[f_max.month].lower()} de cada año. "
                   "Muestra cuánto se federaliza la conectividad internacional.")


def _ficha_ruta(h, df, actual, previo, filtros, rc, nivel_txt, hay_prev, dias, f_min, f_max):
    st.subheader("Todas las rutas")
    tr = _ranking(actual, previo, rc, hay_prev, dias)
    tr['Aerolíneas'] = tr['clave'].map(_lista_aerolineas(actual, rc))
    tr = tr.rename(columns={'clave': 'Ruta'})
    _tabla(h, tr, porcentajes=('Ocupación', 'Participación', 'Cuota argentina'), alto_max=12)
    st.caption(f"Rutas vistas como «{nivel_txt}», sumando ambos sentidos. Frecuencias semanales = vuelos por semana en cada "
               "sentido (un vuelo diario = 7). «Nueva o reanudada» = casi sin tráfico el año anterior.")
    st.markdown("---")

    opciones = tr['Ruta'].tolist()
    if st.session_state.get('int_ficha_ruta') not in opciones:
        st.session_state.pop('int_ficha_ruta', None)
    ruta = st.selectbox("🛫 Elegí una ruta para ver su ficha completa", opciones, key='int_ficha_ruta',
                        help="Están ordenadas por pasajeros. Podés escribir para buscar.")
    r = actual[actual[rc] == ruta]
    rp = previo[previo[rc] == ruta] if hay_prev else previo
    if r.empty:
        return
    pax, vue, asi = r['pasajeros'].sum(), r['vuelos'].sum(), r['asientos'].sum()
    por_aer = r.groupby('aerolinea', observed=True)['pasajeros'].sum()

    def _d(a, b):
        return None if not hay_prev or rp.empty or not b else f"{_var(a, b):+.1f}%".replace(".", ",")
    st.markdown(f"### {ruta}")
    k = st.columns(6)
    k[0].metric("Pasajeros", h.fmt_entero(pax), delta=_d(pax, rp['pasajeros'].sum()))
    k[1].metric("Frecuencias semanales", h.fmt_decimal(_frecuencia(vue, dias)), delta=_d(vue, rp['vuelos'].sum()),
                help="Vuelos por semana en cada sentido (un vuelo diario = 7).")
    k[2].metric("Asientos", h.fmt_entero(asi), delta=_d(asi, rp['asientos'].sum()))
    ocup = pax / asi * 100 if asi else np.nan
    ocup_p = rp['pasajeros'].sum() / rp['asientos'].sum() * 100 if hay_prev and rp['asientos'].sum() else np.nan
    k[3].metric("Ocupación", h.fmt_porcentaje(ocup),
                delta=None if pd.isna(ocup_p) or pd.isna(ocup) else f"{ocup - ocup_p:+.1f} pp".replace(".", ","))
    k[4].metric("Asientos por vuelo", h.fmt_entero(asi / vue) if vue else "s/d", help="Tamaño promedio del avión.")
    k[5].metric("Aerolíneas · HHI", f"{(por_aer > 0).sum()} · {h.fmt_entero(_hhi(por_aer))}",
                help="Cantidad de aerolíneas que operan y concentración del mercado (HHI de 0 a 10.000; más de 2.500 = concentrado).")
    dist = r['km'].mean()
    st.caption("Las variaciones comparan con el mismo período del año anterior."
               + (f" Distancia aproximada de la ruta: {h.fmt_entero(dist)} km (en línea recta)." if pd.notna(dist) else ""))

    st.markdown("#### Quién vuela la ruta")
    g = _por(r, 'aerolinea')
    g = g[g['vuelos'] > 0]
    ocasionales = sorted(g.index[_frecuencia(g['vuelos'], dias) < 0.1])
    g = g[_frecuencia(g['vuelos'], dias) >= 0.1]
    gp = _por(rp, 'aerolinea') if hay_prev and not rp.empty else None
    t = pd.DataFrame({
        'Aerolínea': g.index,
        'Frecuencias semanales': _frecuencia(g['vuelos'].values, dias).round(1),
        'Asientos por vuelo': (g['asientos'] / g['vuelos']).round(0).values,
        'Pasajeros': g['pasajeros'].values,
        'Ocupación': np.where(g['asientos'] > 0, g['pasajeros'] / g['asientos'].clip(lower=1) * 100, np.nan).round(1),
        'Cuota de pasajeros': (g['pasajeros'] / max(pax, 1) * 100).round(1).values,
        'Cuota de asientos': (g['asientos'] / max(asi, 1) * 100).round(1).values,
    })
    t['Pasajeros ÷ asientos (cuota)'] = (t['Cuota de pasajeros'] / t['Cuota de asientos'].clip(lower=0.1)).round(2)
    if gp is not None:
        t['Frec. semanales año ant.'] = [round(_frecuencia(gp['vuelos'].get(a, 0), dias), 1) for a in g.index]
        t['Var. % pasajeros'] = [_txt_var(p, gp['pasajeros'].get(a, 0)) for a, p in zip(g.index, g['pasajeros'])]
    t = t.sort_values('Pasajeros', ascending=False)
    _tabla(h, t, porcentajes=('Ocupación', 'Cuota de pasajeros', 'Cuota de asientos'), alto_max=12)
    st.caption("Pasajeros ÷ asientos (cuota): mayor a 1 = la aerolínea capta más pasajeros de los que le corresponderían por su "
               "capacidad (vende mejor que su oferta); menor a 1 = vende por debajo de su oferta."
               + (f" Con vuelos ocasionales (menos de uno cada diez semanas): {', '.join(ocasionales)}." if ocasionales else ""))

    st.markdown("#### Frecuencias semanales por mes")
    principales = _principales(r)
    m = r.groupby(['periodo_orden', 'periodo_mes_es', 'aerolinea'], observed=True)['vuelos'].sum().reset_index()
    for c in ('periodo_orden', 'periodo_mes_es', 'aerolinea'):
        m[c] = m[c].astype(str)
    m['aerolinea'] = _agrupar_otras(m['aerolinea'], principales)
    m = m.groupby(['periodo_orden', 'periodo_mes_es', 'aerolinea'], as_index=False)['vuelos'].sum()
    dias_mes = r.groupby('periodo_orden', observed=True)['fecha'].nunique()
    dias_mes.index = dias_mes.index.astype(str)
    m['frec'] = [_frecuencia(v, dias_mes.get(p, 30)) for v, p in zip(m['vuelos'], m['periodo_orden'])]
    m = m.sort_values('periodo_orden')
    oc = r.groupby(['periodo_orden', 'periodo_mes_es'], observed=True)[['pasajeros', 'asientos']].sum().reset_index()
    oc['periodo_orden'], oc['periodo_mes_es'] = oc['periodo_orden'].astype(str), oc['periodo_mes_es'].astype(str)
    oc = oc.sort_values('periodo_orden')
    fig = go.Figure()
    orden = m.groupby('aerolinea')['frec'].sum().sort_values(ascending=False).index.tolist()
    for aer in [a for a in orden if a != OTRAS] + [a for a in orden if a == OTRAS]:
        sub = m[m['aerolinea'] == aer]
        fig.add_bar(x=sub['periodo_mes_es'], y=sub['frec'].round(1), name=aer)
    fig.add_scatter(x=oc['periodo_mes_es'], y=(oc['pasajeros'] / oc['asientos'].replace(0, np.nan) * 100).round(1),
                    name='Ocupación (%)', yaxis='y2', mode='lines+markers', line=dict(color='#0f172a', width=2, dash='dot'))
    fig.update_layout(barmode='stack', height=440,
                      xaxis=dict(categoryorder='array', categoryarray=oc['periodo_mes_es'].tolist(), tickangle=-45),
                      yaxis=dict(title='Frecuencias semanales (por sentido)'),
                      yaxis2=dict(title='Ocupación', overlaying='y', side='right', range=[0, 105], tickvals=[0, 25, 50, 75, 100],
                                  ticksuffix='%', showgrid=False))
    h.graficar(fig, leyenda_abajo=True)
    if OTRAS in m['aerolinea'].values:
        st.caption(f"Para que se lean mejor, los gráficos de la ficha muestran las {MAX_AEROLINEAS_GRAFICO} aerolíneas con más "
                   "pasajeros y juntan el resto en «Otras aerolíneas». La tabla de arriba las tiene a todas.")

    st.markdown("#### Vuelos por día de la semana")
    dsem = r.groupby(['aerolinea', 'dia_semana'], observed=True)['vuelos'].sum().reset_index()
    dsem['aerolinea'] = _agrupar_otras(dsem['aerolinea'], principales)
    dsem = dsem.groupby(['aerolinea', 'dia_semana'], as_index=False)['vuelos'].sum()
    orden_dsem = dsem.groupby('aerolinea')['vuelos'].sum().sort_values(ascending=False).index.tolist()
    orden_dsem = [a for a in orden_dsem if a != OTRAS] + [a for a in orden_dsem if a == OTRAS]
    dsem['por_dia'] = (dsem['vuelos'] / max(dias / 7, 1) / 2).round(2)
    dsem['Día'] = dsem['dia_semana'].map(dict(enumerate(DIAS_SEMANA)))
    fig = px.bar(dsem, x='Día', y='por_dia', color='aerolinea', barmode='stack',
                 category_orders={'Día': DIAS_SEMANA, 'aerolinea': orden_dsem}, labels={'por_dia': 'Vuelos promedio por sentido', 'aerolinea': ''})
    fig.update_layout(height=360)
    h.graficar(fig, leyenda_abajo=True)
    st.caption("Promedio de vuelos de cada día de la semana, en cada sentido, durante el período elegido.")

    todo = _filtrar(df, f_min, f_max, filtros)
    todo = todo[todo[rc] == ruta]
    st.markdown("#### Historia de la ruta desde 2017")
    ha = todo.groupby(['ano_num', 'aerolinea'], observed=True)['pasajeros'].sum().reset_index()
    ha['ano_num'] = ha['ano_num'].astype(str)
    ha['aerolinea'] = _agrupar_otras(ha['aerolinea'], _principales(todo))
    ha = ha.groupby(['ano_num', 'aerolinea'], as_index=False)['pasajeros'].sum()
    orden_ha = ha.groupby('aerolinea')['pasajeros'].sum().sort_values(ascending=False).index.tolist()
    orden_ha = [a for a in orden_ha if a != OTRAS] + [a for a in orden_ha if a == OTRAS]
    fig = px.bar(ha, x='ano_num', y='pasajeros', color='aerolinea', category_orders={'aerolinea': orden_ha}, labels={'ano_num': 'Año', 'pasajeros': 'Pasajeros', 'aerolinea': ''})
    if f_max.month < 12:
        for tr_ in fig.data:
            tr_.marker.opacity = [0.45 if x == str(f_max.year) else 1 for x in tr_.x]
    fig.update_layout(height=380, xaxis=dict(type='category'))
    h.graficar(fig, leyenda_abajo=True)
    vida = todo[todo['vuelos'] > 0].groupby('aerolinea', observed=True)['fecha'].agg(['min', 'max']).reset_index()
    ultimo_mes = pd.Timestamp(f_max).to_period('M')
    vida['Estado'] = np.where(vida['max'].dt.to_period('M') >= ultimo_mes, 'Opera', 'Dejó de operar')
    vida['Primer vuelo en la base'] = vida['min'].dt.strftime('%m/%Y')
    vida['Último vuelo'] = vida['max'].dt.strftime('%m/%Y')
    vida = vida.rename(columns={'aerolinea': 'Aerolínea'}).sort_values(['Estado', 'min'], ascending=[False, True])
    h.tabla(vida[['Aerolínea', 'Estado', 'Primer vuelo en la base', 'Último vuelo']], width='stretch', hide_index=True)
    st.caption(f"Entradas y salidas de cada aerolínea en la ruta. La base empieza en {f_min.strftime('%m/%Y')}: "
               "«primer vuelo» puede ser anterior. «Dejó de operar» = sin vuelos en el último mes publicado.")

    st.markdown("#### Estacionalidad de la ruta")
    est = todo[~todo['ano_num'].isin([2020, 2021])]
    completos = est.groupby('ano_num')['mes_num'].nunique()
    est = est[est['ano_num'].isin(completos[completos == 12].index)]
    if est.empty:
        st.info("No hay años completos (sin contar 2020 y 2021) para calcular la estacionalidad de esta ruta.")
    else:
        e = est.groupby(['ano_num', 'mes_num'])['pasajeros'].sum().reset_index()
        e['indice'] = e['pasajeros'] / e.groupby('ano_num')['pasajeros'].transform('mean') * 100
        e['Mes'] = e['mes_num'].map(lambda x: MESES_CORTOS[x - 1])
        e['Año'] = e['ano_num'].astype(str)
        fig = px.line(e.sort_values('mes_num'), x='Mes', y='indice', color='Año', markers=True,
                      category_orders={'Mes': MESES_CORTOS, 'Año': sorted(e['Año'].unique())}, labels={'indice': 'Índice (100 = mes promedio del año)'})
        fig.add_hline(y=100, line_dash='dot', line_color='#94a3b8')
        fig.update_layout(height=380)
        h.graficar(fig, leyenda_abajo=True)
        st.caption("Años completos, sin 2020 ni 2021 (pandemia). Más de 100 = temporada alta de la ruta.")


def _competidores(h, actual, previo, rc, hay_prev, dias):
    st.subheader("Ranking de aerolíneas")
    ta = _ranking(actual, previo, 'aerolinea', hay_prev, dias).rename(columns={'clave': 'Aerolínea'})
    grupos = actual.groupby('aerolinea', observed=True)['grupo'].first()
    grupos.index = grupos.index.astype(str)
    ta.insert(1, 'Tipo', ta['Aerolínea'].map(grupos).astype(str))
    rutas_n = actual[actual['vuelos'] > 0].groupby('aerolinea', observed=True)[rc].nunique()
    rutas_n.index = rutas_n.index.astype(str)
    ta.insert(2, 'Rutas', ta['Aerolínea'].map(rutas_n).fillna(0).astype(int))
    if hay_prev and not previo.empty:
        p = _por(previo, 'aerolinea')['pasajeros']
        ta['Cambio de cuota'] = (ta['Participación'] - ta['Aerolínea'].map(p).fillna(0) / max(p.sum(), 1) * 100).round(1)
    km = medir_km(actual, 'aerolinea')
    ta['Asientos-km (millones)'] = ta['Aerolínea'].map(km['ask']).round(1)
    ta['Pasajeros-km (millones)'] = ta['Aerolínea'].map(km['rpk']).round(1)
    ta['Cuota de pasajeros-km'] = (ta['Pasajeros-km (millones)'] / max(km['rpk'].sum(), 1e-9) * 100).round(1)
    ta['Distancia media (km)'] = ta['Aerolínea'].map(km['dist']).round(0)
    _tabla(h, ta.drop(columns=['Cuota argentina']), porcentajes=('Ocupación', 'Participación', 'Cuota de pasajeros-km'), alto_max=15)
    st.caption("Participación = parte de los pasajeros del período. Cambio de cuota = puntos porcentuales ganados o perdidos. "
               "Asientos-km y pasajeros-km = asientos o pasajeros multiplicados por la distancia de cada ruta: es la forma "
               "estándar de medir el tamaño de una aerolínea, porque no pesa lo mismo un pasajero a Montevideo que uno a Miami. "
               "Distancia media = kilómetros que vuela en promedio cada pasajero.")
    top = ta.head(12)
    fig = go.Figure()
    fig.add_bar(y=top['Aerolínea'], x=top['Participación'], name='Cuota de pasajeros', orientation='h', marker_color='#93c5fd')
    fig.add_bar(y=top['Aerolínea'], x=top['Cuota de pasajeros-km'], name='Cuota de pasajeros-km', orientation='h',
                marker_color='#1d4ed8')
    fig.update_layout(barmode='group', height=34 * len(top) * 1.6 + 80, yaxis=dict(autorange='reversed', title=''),
                      xaxis=dict(title='% del total', ticksuffix='%'), legend=dict(orientation='h', y=1.08, x=0))
    st.markdown("#### Cuota de pasajeros vs. cuota de pasajeros-km")
    h.graficar(fig)
    st.caption("Las 12 aerolíneas con más pasajeros. Si la barra oscura es más larga, la aerolínea vuela rutas más largas que el "
               "promedio (por ejemplo, a Estados Unidos o el Caribe); si es más corta, se concentra en rutas cortas (Brasil, Chile, Uruguay).")
    if 'Cambio de cuota' in ta.columns:
        cambios = ta[ta['Cambio de cuota'].abs() >= 0.3].sort_values('Cambio de cuota')
        if not cambios.empty:
            st.markdown("#### Quién ganó y quién perdió cuota frente al mismo período del año anterior")
            fig = go.Figure(go.Bar(x=cambios['Cambio de cuota'], y=cambios['Aerolínea'], orientation='h',
                                   marker_color=['#10b981' if v >= 0 else '#ef4444' for v in cambios['Cambio de cuota']],
                                   text=[f"{v:+.1f} pp".replace(".", ",") for v in cambios['Cambio de cuota']],
                                   textposition='outside', cliponaxis=False))
            fig.update_layout(height=max(240, 34 * len(cambios) + 100), showlegend=False, margin=dict(l=20, r=70),
                              xaxis_title='Cambio de cuota (puntos porcentuales)', yaxis_title=None)
            h.graficar(fig)
    st.markdown("---")

    st.subheader("Análisis de una aerolínea")
    lista = ta['Aerolínea'].tolist()
    c1, c2 = st.columns(2)
    for clave, defecto in (('int_comp_aer', lista[0]),
                           ('int_comp_vs', 'Aerolíneas Argentinas' if 'Aerolíneas Argentinas' in lista else lista[0])):
        if st.session_state.get(clave) not in lista:
            st.session_state[clave] = defecto
    aer = c1.selectbox("Aerolínea a analizar", lista, key='int_comp_aer')
    vs = c2.selectbox("Comparar con", lista, key='int_comp_vs', help="Normalmente, tu propia aerolínea.")
    a = actual[actual['aerolinea'] == aer]
    ap = previo[previo['aerolinea'] == aer] if hay_prev else previo
    k = st.columns(5)
    k[0].metric("Pasajeros", h.fmt_entero(a['pasajeros'].sum()),
                delta=None if ap.empty else f"{_var(a['pasajeros'].sum(), ap['pasajeros'].sum()):+.1f}%".replace(".", ","))
    n_rutas = a[a['vuelos'] > 0][rc].nunique()
    k[1].metric("Rutas", h.fmt_entero(n_rutas))
    k[2].metric("Frecuencias semanales", h.fmt_decimal(_frecuencia(a['vuelos'].sum(), dias)), help="Suma de todas sus rutas, por sentido.")
    k[3].metric("Ocupación", h.fmt_porcentaje(a['pasajeros'].sum() / a['asientos'].sum() * 100 if a['asientos'].sum() else np.nan))
    k[4].metric("Participación total", h.fmt_porcentaje(a['pasajeros'].sum() / max(actual['pasajeros'].sum(), 1) * 100))

    st.markdown(f"#### Rutas de {aer}")
    g = _por(a, rc)
    g = g[g['vuelos'] > 0]
    tot_ruta = _por(actual, rc)
    gp = _por(ap, rc) if not ap.empty else None
    otros = _lista_aerolineas(actual[actual['aerolinea'] != aer], rc)
    vs_rutas = set(actual[(actual['aerolinea'] == vs) & (actual['vuelos'] > 0)][rc].astype(str))
    total_r = np.array([tot_ruta['pasajeros'].get(x, 0) for x in g.index], dtype=float)
    t = pd.DataFrame({
        'Ruta': g.index,
        'Frecuencias semanales': _frecuencia(g['vuelos'].values, dias).round(1),
        'Pasajeros': g['pasajeros'].values,
        'Ocupación': np.where(g['asientos'] > 0, g['pasajeros'] / g['asientos'].clip(lower=1) * 100, np.nan).round(1),
        'Cuota en la ruta': (g['pasajeros'].values / np.clip(total_r, 1, None) * 100).round(1),
    })
    if gp is not None:
        t['Var. % pasajeros'] = [_txt_var(p_, gp['pasajeros'].get(r_, 0)) for r_, p_ in zip(g.index, g['pasajeros'])]
    if vs != aer:
        t[f'¿Vuela {vs}?'] = ['Sí' if r_ in vs_rutas else 'No' for r_ in g.index]
    t['Competidores'] = [otros.get(r_, '—') for r_ in g.index]
    _tabla(h, t.sort_values('Pasajeros', ascending=False), porcentajes=('Ocupación', 'Cuota en la ruta'), alto_max=15)

    if gp is not None:
        nuevas = sorted(set(g[g['pasajeros'] >= 1000].index) - set(gp[gp['pasajeros'] >= 200].index))
        cortadas = sorted(set(gp[gp['pasajeros'] >= 1000].index) - set(g[g['pasajeros'] >= 200].index))
        cn, cc = st.columns(2)
        with cn:
            st.markdown(f"**Rutas nuevas de {aer}** ({len(nuevas)})")
            st.write(" · ".join(nuevas) if nuevas else "Ninguna frente al mismo período del año anterior.")
        with cc:
            st.markdown(f"**Rutas que dejó de volar** ({len(cortadas)})")
            st.write(" · ".join(cortadas) if cortadas else "Ninguna frente al mismo período del año anterior.")
        st.caption("Solo rutas con al menos 1.000 pasajeros en el período en que operan (se dejan afuera vuelos ocasionales).")

    if vs != aer:
        st.markdown(f"#### Cara a cara: {aer} vs. {vs}")
        gb = _por(actual[actual['aerolinea'] == vs], rc)
        comunes = sorted(set(g.index) & set(gb[gb['vuelos'] > 0].index), key=lambda x: -tot_ruta['pasajeros'].get(x, 0))
        if not comunes:
            st.info(f"{aer} y {vs} no comparten rutas en el período elegido.")
        else:
            def _oc(tabla, x):
                return round(tabla['pasajeros'][x] / tabla['asientos'][x] * 100, 1) if tabla['asientos'][x] else np.nan
            cara = pd.DataFrame({
                'Ruta': comunes,
                f'Frec. {aer}': [round(_frecuencia(g['vuelos'][x], dias), 1) for x in comunes],
                f'Frec. {vs}': [round(_frecuencia(gb['vuelos'][x], dias), 1) for x in comunes],
                f'Cuota {aer}': [round(g['pasajeros'][x] / tot_ruta['pasajeros'][x] * 100, 1) for x in comunes],
                f'Cuota {vs}': [round(gb['pasajeros'][x] / tot_ruta['pasajeros'][x] * 100, 1) for x in comunes],
                f'Ocupación {aer}': [_oc(g, x) for x in comunes],
                f'Ocupación {vs}': [_oc(gb, x) for x in comunes],
            })
            _tabla(h, cara, porcentajes=tuple(c for c in cara.columns if c.startswith(('Cuota', 'Ocupación'))), alto_max=12)
            st.caption(f"{len(comunes)} rutas que operan las dos aerolíneas, ordenadas por tamaño del mercado.")

    st.markdown(f"#### Red de {aer} desde Argentina")
    rutas_red, nodos_red, _ = _rutas_mapa(a, h, 0, dias)
    n_r = len(rutas_red)
    n_c = 0 if nodos_red is None else int(nodos_red.index.str.contains('|', regex=False).sum())
    if nodos_red is not None:
        h.graficar(mapas.mapa_rutas(rutas_red, nodos_red, True, None, 'Sudamérica', alto=520), mapa=True)
        st.caption(f"{n_rutas} rutas a {n_c} ciudades de América en el período elegido. El mapa dibuja una línea por "
                   "aeropuerto argentino" + (f" ({n_r} en total)." if n_r != n_rutas else "."))
    st.markdown("---")

    st.markdown("#### Participación de mercado, mes a mes")
    top8 = actual.groupby('aerolinea', observed=True)['pasajeros'].sum().nlargest(8).index
    s = actual[['periodo_orden', 'periodo_mes_es', 'aerolinea', 'pasajeros']].copy()
    s['aerolinea'] = s['aerolinea'].astype(str).where(s['aerolinea'].isin(top8), 'Otras aerolíneas')
    s = s.groupby(['periodo_orden', 'periodo_mes_es', 'aerolinea'], observed=True)['pasajeros'].sum().reset_index()
    s['periodo_orden'], s['periodo_mes_es'] = s['periodo_orden'].astype(str), s['periodo_mes_es'].astype(str)
    s = s.sort_values('periodo_orden')
    fig = px.bar(s, x='periodo_mes_es', y='pasajeros', color='aerolinea',
                 category_orders={'periodo_mes_es': s.drop_duplicates('periodo_orden')['periodo_mes_es'].tolist()},
                 labels={'periodo_mes_es': 'Período', 'pasajeros': 'Participación', 'aerolinea': ''})
    fig.update_layout(barmode='stack', barnorm='percent', yaxis_ticksuffix='%', xaxis_tickangle=-45, height=440)
    h.graficar(fig, leyenda_abajo=True)
    st.markdown("---")


def _capacidad(h, actual, previo, rc, hay_prev, dias):
    st.subheader("Capacidad y ocupación por ruta")
    g = _por(actual, rc)
    g = g[g['vuelos'] > 0]
    gp = _por(previo, rc) if hay_prev and not previo.empty else None
    t = pd.DataFrame({'Ruta': g.index, 'Asientos': g['asientos'].values, 'Pasajeros': g['pasajeros'].values,
                      'Frecuencias semanales': _frecuencia(g['vuelos'].values, dias).round(1),
                      'Ocupación': np.where(g['asientos'] > 0, g['pasajeros'] / g['asientos'].clip(lower=1) * 100, np.nan).round(1)})
    if gp is not None:
        asi_ant = np.array([gp['asientos'].get(x, 0) for x in g.index], dtype=float)
        pax_ant = np.array([gp['pasajeros'].get(x, 0) for x in g.index], dtype=float)
        t['Asientos año ant.'] = asi_ant.astype(int)
        t['Var. % asientos'] = [_txt_var(a, b) for a, b in zip(g['asientos'], asi_ant)]
        t['Ocupación año ant.'] = np.where(asi_ant > 0, pax_ant / np.clip(asi_ant, 1, None) * 100, np.nan).round(1)
        t['Δ ocupación'] = (t['Ocupación'] - t['Ocupación año ant.']).round(1)
        t['_var_asi'] = np.where(asi_ant >= 1000, (g['asientos'].values - asi_ant) / np.clip(asi_ant, 1, None) * 100, np.nan)
    t = t.sort_values('Pasajeros', ascending=False)
    relevantes = t[(t['Pasajeros'] >= 5000) & (t['Frecuencias semanales'] >= 1)]

    if gp is not None and relevantes['_var_asi'].notna().any():
        st.markdown("#### Mapa de capacidad: ocupación vs. crecimiento de la oferta")
        v = relevantes.dropna(subset=['_var_asi'])
        v = v[v['_var_asi'].between(-100, 300)]
        fig = px.scatter(v, x='Ocupación', y='_var_asi', size='Pasajeros', hover_name='Ruta', size_max=40,
                         labels={'_var_asi': 'Variación de asientos vs. año anterior (%)', 'Ocupación': 'Ocupación (%)'})
        fig.add_vline(x=85, line_dash='dot', line_color='#94a3b8')
        fig.add_hline(y=0, line_dash='dot', line_color='#94a3b8')
        fig.add_annotation(x=v['Ocupación'].max(), y=v['_var_asi'].min(), text="Llenas y sin más oferta", showarrow=False,
                           xanchor='right', yanchor='bottom', font=dict(color='#15803d'))
        fig.add_annotation(x=v['Ocupación'].min(), y=v['_var_asi'].max(), text="Más oferta y poca ocupación", showarrow=False,
                           xanchor='left', yanchor='top', font=dict(color='#b91c1c'))
        fig.update_traces(marker=dict(color=h.PALETA[0], opacity=0.6, line=dict(width=1, color='white')))
        fig.update_layout(height=480, xaxis=dict(ticksuffix='%'), yaxis=dict(ticksuffix='%'))
        h.graficar(fig)
        st.caption("Cada círculo es una ruta con al menos 5.000 pasajeros y una frecuencia semanal (tamaño = pasajeros). Abajo a la derecha: rutas muy llenas "
                   "donde nadie agregó asientos (posible demanda insatisfecha). Arriba a la izquierda: más oferta y poca ocupación.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Rutas más llenas")
        _tabla(h, relevantes[relevantes['Ocupación'] >= 88][['Ruta', 'Ocupación', 'Frecuencias semanales', 'Pasajeros']].head(15),
               porcentajes=('Ocupación',), alto_max=15)
    with c2:
        st.markdown("#### Rutas con ocupación baja")
        _tabla(h, relevantes[relevantes['Ocupación'] <= 72][['Ruta', 'Ocupación', 'Frecuencias semanales', 'Pasajeros']]
               .sort_values('Ocupación').head(15), porcentajes=('Ocupación',), alto_max=15)
    st.caption("Rutas con al menos 5.000 pasajeros y una frecuencia semanal en el período. Llenas: 88% o más; baja: 72% o menos.")

    st.markdown("#### Todas las rutas")
    _tabla(h, t.drop(columns=[c for c in t.columns if c.startswith('_')]), porcentajes=('Ocupación', 'Ocupación año ant.'), alto_max=12)
    st.markdown("---")

    st.subheader("Quién agregó o sacó capacidad")
    if not (hay_prev and not previo.empty):
        st.info("La base no tiene el mismo período del año anterior para comparar la capacidad.")
        return
    a, ap = _por(actual, 'aerolinea'), _por(previo, 'aerolinea')
    aers = sorted(set(a.index) | set(ap.index), key=lambda x: -(a['asientos'].get(x, 0)))
    c = pd.DataFrame({'Aerolínea': aers,
                      'Asientos año ant.': [int(ap['asientos'].get(x, 0)) for x in aers],
                      'Asientos': [int(a['asientos'].get(x, 0)) for x in aers]})
    c['Diferencia de asientos'] = c['Asientos'] - c['Asientos año ant.']
    c['Var. %'] = [_txt_var(x, y) for x, y in zip(c['Asientos'], c['Asientos año ant.'])]
    c['Cuota de asientos'] = (c['Asientos'] / max(c['Asientos'].sum(), 1) * 100).round(1)
    c['Cambio de cuota de asientos'] = (c['Cuota de asientos'] - c['Asientos año ant.'] / max(c['Asientos año ant.'].sum(), 1) * 100).round(1)
    c = c[(c['Asientos'] + c['Asientos año ant.']) > 0]
    top = c.reindex(c['Diferencia de asientos'].abs().sort_values(ascending=False).index).head(12).sort_values('Diferencia de asientos')
    fig = go.Figure(go.Bar(x=top['Diferencia de asientos'], y=top['Aerolínea'], orientation='h',
                           marker_color=['#10b981' if v >= 0 else '#ef4444' for v in top['Diferencia de asientos']],
                           text=[("+" if v >= 0 else "") + h.fmt_entero(v) for v in top['Diferencia de asientos']],
                           textposition='outside', cliponaxis=False))
    fig.update_layout(height=max(260, 34 * len(top) + 100), showlegend=False, xaxis_title='Asientos agregados o quitados',
                      yaxis_title=None, margin=dict(l=20, r=90))
    h.graficar(fig)
    _tabla(h, c.sort_values('Asientos', ascending=False), porcentajes=('Cuota de asientos',), alto_max=12)
    st.caption("Asientos ofrecidos en el período contra el mismo período del año anterior.")


def _oportunidades(h, actual, previo, rc, hay_prev, dias):
    tr = _ranking(actual, previo, rc, hay_prev, dias).rename(columns={'clave': 'Ruta'})
    tr['Aerolíneas'] = tr['Ruta'].map(_lista_aerolineas(actual, rc))

    st.subheader("Rutas sin aerolíneas argentinas")
    sin = tr[(tr['Cuota argentina'].fillna(0) == 0) & (tr['Pasajeros'] >= 1000)]
    if sin.empty:
        st.info("En el período elegido, todas las rutas con movimiento relevante tienen alguna aerolínea argentina.")
    else:
        cols = [c for c in ['Ruta', 'Pasajeros', 'Var. %', 'Frecuencias semanales', 'Ocupación', 'Aerolíneas'] if c in sin.columns]
        _tabla(h, sin[cols], porcentajes=('Ocupación',), alto_max=15)
        st.caption("Rutas con al menos 1.000 pasajeros donde no vuela ninguna aerolínea argentina "
                   "(JetSMART Argentina cuenta como argentina; JetSMART Chile, como extranjera).")
    st.markdown("---")

    st.subheader("Destinos que solo tienen vuelo directo desde Buenos Aires")
    dest = actual[actual['vuelos'] > 0].groupby('destino', observed=True).agg(
        pasajeros=('pasajeros', 'sum'), ciudades_arg=('ciudad_arg', lambda x: sorted(set(map(str, x)))))
    dest.index = dest.index.astype(str)
    solo_ba = dest[dest['ciudades_arg'].map(lambda c: c == ['Buenos Aires']) & (dest['pasajeros'] >= 5000)]
    con_interior = dest[dest['ciudades_arg'].map(lambda c: any(x != 'Buenos Aires' for x in c))]
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Solo desde Buenos Aires**")
        t1 = solo_ba.sort_values('pasajeros', ascending=False).reset_index().rename(columns={'destino': 'Destino', 'pasajeros': 'Pasajeros'})
        _tabla(h, t1[['Destino', 'Pasajeros']], alto_max=15)
    with c2:
        st.markdown("**Con vuelo directo desde el interior**")
        t2 = con_interior.sort_values('pasajeros', ascending=False).reset_index()
        t2['Desde el interior'] = t2['ciudades_arg'].map(lambda c: ", ".join(x for x in c if x != 'Buenos Aires'))
        t2 = t2.rename(columns={'destino': 'Destino', 'pasajeros': 'Pasajeros'})
        _tabla(h, t2[['Destino', 'Pasajeros', 'Desde el interior']], alto_max=15)
    st.caption("Destinos de América con al menos 5.000 pasajeros en el período a los que hoy solo se llega en vuelo directo desde "
               "Buenos Aires: los pasajeros del interior tienen que conectar.")

    if not (hay_prev and 'Var. %' in tr.columns):
        return
    st.markdown("---")
    st.subheader("Rutas que más crecen y más caen")
    base = tr[tr['Pasajeros año ant.'] >= 10000].copy()
    base['_v'] = (base['Pasajeros'] - base['Pasajeros año ant.']) / base['Pasajeros año ant.'] * 100
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Crecen**")
        _tabla(h, base.nlargest(12, '_v')[['Ruta', 'Pasajeros', 'Var. %', 'Aerolíneas']], alto_max=12)
    with c2:
        st.markdown("**Caen**")
        _tabla(h, base.nsmallest(12, '_v')[['Ruta', 'Pasajeros', 'Var. %', 'Aerolíneas']], alto_max=12)
    st.caption("Rutas con al menos 10.000 pasajeros el año anterior, para evitar porcentajes engañosos.")
    st.markdown("---")

    st.subheader("Rutas nuevas y rutas cortadas")
    p = _por(previo, rc)
    nuevas = tr[(tr['Pasajeros año ant.'] < (tr['Pasajeros'] * 0.05).clip(lower=500)) & (tr['Pasajeros'] >= 1000)]
    actuales = set(tr['Ruta'])
    cortadas = p[(p['pasajeros'] >= 1000) & ~p.index.isin(actuales)].sort_values('pasajeros', ascending=False).reset_index()
    cortadas = cortadas.rename(columns={rc: 'Ruta', 'pasajeros': 'Pasajeros año ant.'})
    cortadas['Volaban'] = cortadas['Ruta'].map(_lista_aerolineas(previo, rc))
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**Nuevas o reanudadas** ({len(nuevas)})")
        _tabla(h, nuevas[['Ruta', 'Pasajeros', 'Aerolíneas']], alto_max=12)
    with c2:
        st.markdown(f"**Cortadas** ({len(cortadas)})")
        _tabla(h, cortadas[['Ruta', 'Pasajeros año ant.', 'Volaban']], alto_max=12)
    st.caption("Frente al mismo período del año anterior, con al menos 1.000 pasajeros.")


def _destinos(h, actual, previo, hay_prev, dias):
    for col, titulo, nombre in (("pais", "países", "País"), ("destino", "ciudades", "Ciudad")):
        st.subheader(f"Ranking de {titulo}")
        t = _ranking(actual, previo, col, hay_prev, dias).rename(columns={'clave': nombre})
        _tabla(h, t, porcentajes=('Participación', 'Cuota argentina', 'Ocupación'))
        if col == "pais":
            top = actual.groupby(['pais', 'grupo'], observed=True)['pasajeros'].sum().reset_index()
            orden = actual.groupby('pais', observed=True)['pasajeros'].sum().sort_values(ascending=False).head(12)
            top = top[top['pais'].isin(orden.index)]
            top['pais'], top['grupo'] = top['pais'].astype(str), top['grupo'].astype(str)
            fig = px.bar(top, y='pais', x='pasajeros', color='grupo', orientation='h', color_discrete_map=COLORES_GRUPO,
                         category_orders={'pais': [str(p) for p in orden.index], 'grupo': GRUPOS},
                         labels={'pais': '', 'pasajeros': 'Pasajeros', 'grupo': ''})
            fig.update_layout(height=max(320, 34 * len(orden) + 120))
            h.graficar(fig, leyenda_abajo=True)
        st.caption("Var. % compara con el mismo período del año anterior. Cuota argentina = parte de los pasajeros llevada por "
                   "aerolíneas argentinas (incluye JetSMART Argentina). Podés ordenar por cualquier columna.")
        st.markdown("---")


def _escalas(h, actual, dias):
    st.subheader("Vuelos con escala o de quinta libertad")
    st.markdown("Cuando una aerolínea vuela entre Argentina y **un país que no es el suyo**, ese tramo suele ser la continuación "
                "de un vuelo con escala. Por ejemplo, Emirates (Dubái → **Río de Janeiro** → Buenos Aires) o Air Canada "
                "(Toronto → **San Pablo** → Buenos Aires). También incluye vuelos de **quinta libertad**: una aerolínea que opera "
                "entre dos países que no son el suyo (por ejemplo, LATAM entre Buenos Aires y Miami). En esta base aparece el tramo "
                "entre esa ciudad y Argentina.")
    esc = actual[actual['escala']]
    if esc.empty:
        st.info("No hay vuelos con escala ni de quinta libertad con los filtros elegidos.")
    else:
        ge = esc.groupby(['aerolinea', 'destino'], observed=True).agg(
            Pasajeros=('pasajeros', 'sum'), Vuelos=('vuelos', 'sum'), Asientos=('asientos', 'sum')).reset_index()
        # solo escalas regulares: al menos 1.000 pasajeros y un vuelo cada dos semanas por sentido (se descartan desvíos)
        ge = ge[(ge['Pasajeros'] >= 1000) & (_frecuencia(ge['Vuelos'], dias) >= 0.5)]
        if ge.empty:
            st.info("En el período elegido no hay escalas regulares (solo vuelos ocasionales o desvíos).")
        else:
            ge['aerolinea'], ge['destino'] = ge['aerolinea'].astype(str), ge['destino'].astype(str)
            ge['Frecuencias semanales'] = _frecuencia(ge['Vuelos'], dias).round(1)
            ge['Ocupación'] = np.where(ge['Asientos'] > 0, ge['Pasajeros'] / ge['Asientos'].clip(lower=1) * 100, np.nan).round(1)
            ge = ge.sort_values('Pasajeros', ascending=False).rename(columns={'aerolinea': 'Aerolínea', 'destino': 'Ciudad de escala u origen'})
            fig = px.bar(ge.iloc[::-1], x='Pasajeros', y='Aerolínea', color='Ciudad de escala u origen', orientation='h', labels={'Aerolínea': ''})
            fig.update_layout(height=max(280, 36 * ge['Aerolínea'].nunique() + 140))
            h.graficar(fig, leyenda_abajo=True)
            _tabla(h, ge[['Aerolínea', 'Ciudad de escala u origen', 'Pasajeros', 'Frecuencias semanales', 'Ocupación']], porcentajes=('Ocupación',))
            st.caption("Solo combinaciones regulares (al menos 1.000 pasajeros y un vuelo cada dos semanas por sentido), para dejar "
                       "afuera desvíos y vuelos ocasionales. "
                       "Pasajeros = los que vuelan entre la ciudad de escala y Argentina.")
    with st.expander("¿Y las escalas de las aerolíneas argentinas?"):
        st.markdown("La fuente oficial (SINTA/ANAC) registra solo los tramos que tocan un aeropuerto argentino y no informa el "
                    "número de vuelo. Por eso, si un vuelo de una aerolínea argentina sigue desde una ciudad de América hacia "
                    "otra (por ejemplo, Punta Cana → Miami), ese tramo no aparece acá. Para reconstruirlo haría falta otra "
                    "fuente, como el seguimiento de los aviones por radar (ADS-B).")


def _datos(actual, f_min, f_max):
    st.subheader("Descarga de datos filtrados")
    st.markdown("Descargá los datos del filtro aplicado para analizarlos en Excel o Python.")

    def _csv(d=actual):
        return d.drop(columns=['ciudad_clave']).to_csv(index=False, sep=';').encode('utf-8-sig')

    st.download_button("📥 Descargar datos filtrados (CSV)", data=_csv,
                       file_name=f"internacional_america_{date.today().strftime('%Y%m%d')}.csv", mime="text/csv")
    with st.expander("ℹ️ Metodología de esta sección"):
        st.markdown(f"""
**Fuente.** Tablero de conectividad aérea de SINTA (Ministerio de Turismo) con registros de ANAC, clasificación
"Internacional". Se incluyen todos los vuelos entre un aeropuerto argentino y otra ciudad de América. Datos del
**{f_min.strftime('%d/%m/%Y')}** al **{f_max.strftime('%d/%m/%Y')}**; se actualizan automáticamente cada mes.

**Rutas.** Se pueden ver como aeropuerto argentino ⇄ ciudad, ciudad ⇄ ciudad (mercado: por ejemplo, Buenos Aires suma
Aeroparque, Ezeiza, El Palomar, Morón y San Fernando) o aeropuerto ⇄ aeropuerto. Siempre suman ambos sentidos.

**Indicadores**
- **Frecuencias semanales:** vuelos por semana en cada sentido (un vuelo diario = 7).
- **Ocupación:** pasajeros ÷ asientos. **Asientos por vuelo:** tamaño promedio del avión.
- **Cuota de pasajeros vs. cuota de asientos:** si una aerolínea tiene más cuota de pasajeros que de asientos, vende mejor que su oferta.
- **Asientos-km y pasajeros-km:** asientos o pasajeros por la distancia en línea recta entre el aeropuerto argentino y la ciudad extranjera (aproximada: no es la distancia exacta que vuela cada avión).
- **HHI:** concentración del mercado de la ruta (0 a 10.000; más de 2.500 = concentrado).
- **Variaciones:** contra el mismo período del año anterior. «Nueva o reanudada» = casi sin tráfico el año anterior.

**Tipos de aerolínea**
- **Argentinas:** Aerolíneas Argentinas, Flybondi, JetSMART Argentina, Andes, LADE, American Jet y Flyest.
- **JetSMART Argentina y JetSMART Chile:** SINTA informa a JetSMART con un solo nombre. Para separarlas se usan los
  aterrizajes y despegues de ANAC (datos.gob.ar), que identifican a la empresa que operó cada vuelo
  (JetSMART Airlines S.A. = Argentina; JetSMART Airlines SpA = Chile). Con esos datos se reparte, para cada mes,
  aeropuerto argentino y ciudad extranjera, la misma proporción de vuelos que informa ANAC. Antes de 2019 todos sus
  vuelos se asignan a JetSMART Chile.
- **Extranjeras de América** y **extranjeras de fuera de América**.

**Escalas y quinta libertad.** Un tramo se considera continuación de un vuelo con escala (o de quinta libertad) cuando la
aerolínea vuela entre Argentina y un país que no es el suyo (por ejemplo, Air Canada desde San Pablo). JetSMART queda
afuera: su filial chilena opera algunas rutas desde Perú o Brasil con su propio certificado.

**Lo que la fuente no tiene:** tarifas, número de vuelo, tipo de avión, origen y destino real del pasajero (conexiones) ni la
programación futura de vuelos.
""")


def _rutas_mapa(df, h, vuelos_semana_min, dias):
    """Rutas aeropuerto argentino ⇄ ciudad extranjera y sus extremos, listas para mapas.mapa_rutas."""
    g = df.groupby(['aeropuerto_arg', 'ciudad_clave', 'destino', 'region'], observed=True)[
        ['pasajeros', 'vuelos', 'asientos']].sum().reset_index()
    for c in ('aeropuerto_arg', 'ciudad_clave', 'destino', 'region'):
        g[c] = g[c].astype(str)
    g = g[(g['vuelos'] > 0) & (g['vuelos'] / max(dias, 1) * 7 >= vuelos_semana_min)].copy()
    coord_arg = {**h.COORDENADAS, **COORD_ARG_EXTRA}
    g['a'] = g['aeropuerto_arg'].str[:3]
    g['b'] = g['ciudad_clave']
    faltan = set(g.loc[~g['b'].isin(COORD_CIUDADES), 'destino']) | set(g.loc[~g['a'].isin(coord_arg), 'aeropuerto_arg'])
    g = g[g['b'].isin(COORD_CIUDADES) & g['a'].isin(coord_arg)]
    if g.empty:
        return g, None, faltan
    g['ruta'] = g['aeropuerto_arg'] + ' ⇄ ' + g['destino']
    g['frec'] = _frecuencia(g['vuelos'], dias)
    nombres = dict(zip(g['a'], g['aeropuerto_arg'])) | dict(zip(g['b'], g['destino']))
    colores = dict(zip(g['b'], g['region'].map(COLORES_REGION).fillna('#64748b')))
    nodos = mapas.nodos_desde_rutas(g, {**coord_arg, **COORD_CIUDADES}, nombres, colores)
    return g, nodos, faltan
