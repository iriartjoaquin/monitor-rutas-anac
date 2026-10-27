"""
Sección "Internacional – América": vuelos entre Argentina y el resto de América.

Fuente: tablero de conectividad aérea de SINTA (Ministerio de Turismo) con datos de ANAC, clasificación
"Internacional", filtrado a vuelos cuyo otro extremo está en América. Lo descarga y actualiza el agente
mensual (actualizar_zip.py --tipo internacional) en internacional_america.zip.

La función principal es mostrar(h), donde h trae las utilidades compartidas con la sección de cabotaje
(gráficos, formatos, coordenadas de aeropuertos argentinos, etc.).
"""
import calendar
import os
from datetime import date

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ZIP_INTERNACIONAL = "internacional_america.zip"
MESES_NOMBRE = {"Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, "Mayo": 5, "Junio": 6, "Julio": 7,
                "Agosto": 8, "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12}

# Aerolíneas con certificado argentino. JetSMART va aparte: SINTA agrupa en un solo nombre sus filiales
# de Argentina, Chile y Perú, así que no se puede saber qué parte de sus vuelos es argentina.
ARGENTINAS = {'Aerolíneas Argentinas', 'Flybondi', 'Andes Líneas Aéreas', 'LADE - Líneas Aéreas Del Estado',
              'American Jet', 'Flyest'}
JETSMART = {'JetSMART Airlines'}
# Aerolíneas de fuera de América: sus vuelos a Argentina en esta base son el tramo final de un viaje
# que hace escala en otra ciudad de América (por ejemplo, Dubái → Río de Janeiro → Buenos Aires).
FUERA_DE_AMERICA = {'Turkish Airlines', 'KLM', 'Emirates Airline', 'Ethiopian Airlines', 'British Airways',
                    'Qatar Airways', 'Swiss International Air Lines', 'Air Europa', 'Lufthansa', 'Iberia Airlines',
                    'ITA Airways', 'Air France', 'Air New Zealand', 'Plus Ultra', 'Icelandair', 'ASL Airlines France'}
GRUPOS = ['Argentinas', 'JetSMART (grupo regional)', 'Extranjeras de América', 'Extranjeras de fuera de América']
COLORES_GRUPO = {'Argentinas': '#1d4ed8', 'JetSMART (grupo regional)': '#e11d48',
                 'Extranjeras de América': '#94a3b8', 'Extranjeras de fuera de América': '#f59e0b'}
COLORES_REGION = {'América del Sur': '#1d4ed8', 'América Central y Caribe': '#10b981', 'América del Norte': '#f59e0b'}

# Coordenadas (latitud, longitud) de las ciudades de América conectadas con Argentina, para el mapa
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
}
COORD_CIUDADES.update({
    'Oranjestad|Aruba': (12.50, -70.02), 'Santo Domingo|República Dominicana': (18.43, -69.67),
    'Puerto España|Trinidad y Tobago': (10.60, -61.34), 'Antofagasta|Chile': (-23.44, -70.45), 'Holguín|Cuba': (20.79, -76.32),
    'Boa Vista|Brasil': (2.84, -60.69), 'Washington|Estados Unidos': (38.95, -77.45), 'Mérida|México': (20.94, -89.66),
    'Cusco|Perú': (-13.54, -71.94), 'Arequipa|Perú': (-16.34, -71.58), 'Iquitos|Perú': (-3.78, -73.31),
    'Fernando de Noronha|Brasil': (-3.85, -32.42), 'Minera Escondida|Chile': (-24.29, -69.17),
    'São José dos Campos|Brasil': (-23.23, -45.86), 'Campos dos Goytacazes|Brasil': (-21.70, -41.30),
    'San José del Guaviare|Colombia': (2.57, -72.64),
})
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


def _combinar(a, b, armar):
    """Arma etiquetas a partir de dos columnas, una vez por combinación distinta (rápido y liviano)."""
    cod, unicos = pd.factorize(pd.MultiIndex.from_arrays([np.asarray(a, dtype=object), np.asarray(b, dtype=object)]))
    etiquetas = np.array([armar(x, y) for x, y in unicos], dtype=object)
    return pd.Categorical(etiquetas[cod])


def _grupo(aerolinea):
    if aerolinea in ARGENTINAS:
        return 'Argentinas'
    if aerolinea in JETSMART:
        return 'JetSMART (grupo regional)'
    if aerolinea in FUERA_DE_AMERICA:
        return 'Extranjeras de fuera de América'
    return 'Extranjeras de América'


@st.cache_resource(show_spinner="Cargando la base internacional…")
def cargar_internacional(ruta, modificado, _etiqueta_aeropuerto, _limpiar_texto):
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
    out['periodo_orden'] = _combinar(out['ano_num'], out['mes_num'], lambda y, m: f"{y}-{m:02d}")
    out['periodo_mes_es'] = _combinar(out['ano_num'], out['mes_num'],
                                      lambda y, m: f"{['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'][m - 1]}-{str(y)[2:]}")
    aer = df['Empresa agrupada'].astype(object)
    nombres = {a: _limpiar_texto(a) for a in aer.unique()}
    out['aerolinea'] = pd.Categorical(aer.map(nombres))
    out['grupo'] = pd.Categorical(out['aerolinea'].astype(object).map(_grupo), categories=GRUPOS)

    aero_arg = lado('Origen aeropuerto', 'Destino aeropuerto', extranjero=False)
    etiquetas_arg = {a: _etiqueta_aeropuerto(a) for a in pd.unique(aero_arg)}
    out['aeropuerto_arg'] = pd.Categorical([etiquetas_arg[a] for a in aero_arg])
    pais = lado('Origen país', 'Destino país', extranjero=True)
    aero_ext = lado('Origen aeropuerto', 'Destino aeropuerto', extranjero=True)
    loc_ext = lado('Origen localidad', 'Destino localidad', extranjero=True)
    ciudad = np.asarray(_combinar(loc_ext, aero_ext, _ciudad), dtype=object)
    region = lado('Origen continente', 'Destino continente', extranjero=True)
    out['pais'] = pd.Categorical(pais)
    out['region'] = pd.Categorical(region)
    out['ciudad_clave'] = _combinar(ciudad, pais, lambda c, p: f"{c}|{p}")
    out['destino'] = _combinar(ciudad, pais, lambda c, p: f"{c} ({p})")
    out['ruta'] = _combinar(out['aeropuerto_arg'].astype(object), out['destino'].astype(object), lambda a, b: f"{a} ⇄ {b}")
    out['sentido'] = pd.Categorical(np.where(sale, 'Sale de Argentina', 'Llega a Argentina'))
    for c in ['vuelos', 'pasajeros', 'asientos']:
        out[c] = pd.to_numeric(df[c.capitalize()], errors='coerce').fillna(0).astype(np.int32)
    return out[out['fecha'].notna()].reset_index(drop=True)


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


def _txt_var(v):
    return "Nueva" if pd.isna(v) else f"{v:+.1f}%".replace(".", ",")


def mostrar(h):
    df = cargar_internacional(ZIP_INTERNACIONAL, os.path.getmtime(ZIP_INTERNACIONAL) if os.path.exists(ZIP_INTERNACIONAL) else 0,
                              h.construir_etiqueta_aeropuerto, h.limpiar_mojibake_texto)
    if df is None or df.empty:
        st.info("Todavía no está cargada la base internacional (internacional_america.zip).")
        return

    f_min, f_max = df['fecha'].min().date(), df['fecha'].max().date()
    st.markdown(
        '<div class="chips" style="margin:-.4rem 0 1.2rem 0;">'
        '<span class="chip" style="background:#e0f2fe;color:#0c4a6e;border-color:#bae6fd;">📡 Fuente: SINTA (Turismo) con datos de ANAC</span>'
        f'<span class="chip" style="background:#e0f2fe;color:#0c4a6e;border-color:#bae6fd;">📅 Datos del {f_min.strftime("%d/%m/%Y")} al {f_max.strftime("%d/%m/%Y")}</span>'
        '<span class="chip" style="background:#e0f2fe;color:#0c4a6e;border-color:#bae6fd;">🌎 Vuelos entre Argentina y el resto de América</span>'
        '</div>', unsafe_allow_html=True)

    # ---------------------------------------------------------------- filtros
    def_desde = date(f_max.year, 1, 1) if date(f_max.year, 1, 1) >= f_min else f_min
    st.session_state.setdefault('int_desde', def_desde)
    st.session_state.setdefault('int_hasta', f_max)
    st.session_state['int_desde'] = h.sanitizar_fecha(st.session_state['int_desde'], def_desde, f_min, f_max)
    st.session_state['int_hasta'] = h.sanitizar_fecha(st.session_state['int_hasta'], f_max, f_min, f_max)

    def _restablecer():
        for k in ('int_regiones', 'int_paises', 'int_aerolineas', 'int_grupos', 'int_aeropuertos'):
            st.session_state[k] = []
        st.session_state['int_desde'], st.session_state['int_hasta'] = def_desde, f_max

    with st.container(border=True):
        st.markdown("#### 🔍 Filtros")
        c1, c2, c3 = st.columns(3)
        regiones = c1.multiselect("Región", sorted(df['region'].astype(str).unique()), key='int_regiones', placeholder="Toda América")
        base_paises = df[df['region'].isin(regiones)] if regiones else df
        paises = c2.multiselect("País", sorted(base_paises['pais'].astype(str).unique()), key='int_paises', placeholder="Todos")
        grupos = c3.multiselect("Tipo de aerolínea", GRUPOS, key='int_grupos', placeholder="Todas",
                                help="Argentinas: con certificado argentino. JetSMART va aparte porque la fuente no separa sus filiales "
                                     "de Argentina, Chile y Perú. Las de fuera de América llegan con escala en otra ciudad de América.")
        c4, c5, c6, c7, c8 = st.columns([3, 3, 2, 2, 2], vertical_alignment="bottom")
        aerolineas = c4.multiselect("Aerolínea", sorted(df['aerolinea'].astype(str).unique()), key='int_aerolineas', placeholder="Todas")
        aeropuertos = c5.multiselect("Aeropuerto argentino", sorted(df['aeropuerto_arg'].astype(str).unique()), key='int_aeropuertos',
                                     placeholder="Todos")
        desde = c6.date_input("📅 Desde", key='int_desde', min_value=f_min, max_value=f_max, format="DD/MM/YYYY")
        hasta = c7.date_input("📅 Hasta", key='int_hasta', min_value=f_min, max_value=f_max, format="DD/MM/YYYY")
        c8.button("↺ Restablecer", on_click=_restablecer, use_container_width=True, key='int_reset')
        if desde > hasta:
            st.warning("La fecha inicial es posterior a la final: ajustá el período.")

    filtros = {'regiones': regiones, 'paises': paises, 'aerolineas': aerolineas, 'grupos': grupos, 'aeropuertos': aeropuertos}
    actual = _filtrar(df, desde, hasta, filtros)
    hay_prev = h.restar_ano(desde) >= f_min
    previo = _filtrar(df, h.restar_ano(desde), h.restar_ano(hasta), filtros) if hay_prev else actual.iloc[0:0]
    if actual.empty:
        st.warning("No hay vuelos para los filtros elegidos. Probá ampliar el período o quitar algún filtro.")
        return

    # ---------------------------------------------------------------- indicadores
    pax, vue, asi = int(actual['pasajeros'].sum()), int(actual['vuelos'].sum()), int(actual['asientos'].sum())
    st.subheader("📌 Resumen del período")
    k = st.columns(6)
    k[0].metric("Pasajeros", h.fmt_entero(pax))
    k[1].metric("Vuelos", h.fmt_entero(vue))
    k[2].metric("Asientos", h.fmt_entero(asi))
    k[3].metric("Ocupación", h.fmt_porcentaje(pax / asi * 100 if asi else np.nan))
    k[4].metric("Ciudades conectadas", h.fmt_entero(actual['destino'].nunique()))
    k[5].metric("Cuota argentina", h.fmt_porcentaje(_cuota_arg(actual)),
                help="Porcentaje de los pasajeros transportados por aerolíneas argentinas (sin contar JetSMART).")

    tabs = st.tabs(["📊 Panorama", "🏙️ Destinos", "⚖️ Aerolíneas", "🗺️ Rutas", "🔁 Escalas", "📋 Datos"])

    # ================================================================ PANORAMA
    with tabs[0]:
        ini_u = date(f_max.year, f_max.month, 1)
        filtros_sin_fecha = dict(filtros)
        u = _filtrar(df, ini_u, f_max, filtros_sin_fecha)
        up = _filtrar(df, h.restar_ano(ini_u), h.restar_ano(f_max), filtros_sin_fecha) if h.restar_ano(ini_u) >= f_min else u.iloc[0:0]
        st.subheader(f"Último mes publicado: {h.meses_es[f_max.month]} {f_max.year}")
        if u.empty:
            st.info("Los filtros elegidos no tienen vuelos en el último mes publicado.")
        else:
            def _d(a, b):
                return None if up.empty or not b else f"{_var(a, b):+.1f}%".replace(".", ",")
            uc = st.columns(4)
            uc[0].metric("Vuelos", h.fmt_entero(u['vuelos'].sum()), delta=_d(u['vuelos'].sum(), up['vuelos'].sum()))
            uc[1].metric("Pasajeros", h.fmt_entero(u['pasajeros'].sum()), delta=_d(u['pasajeros'].sum(), up['pasajeros'].sum()))
            uc[2].metric("Asientos", h.fmt_entero(u['asientos'].sum()), delta=_d(u['asientos'].sum(), up['asientos'].sum()))
            ca, cp = _cuota_arg(u), _cuota_arg(up) if not up.empty else np.nan
            uc[3].metric("Cuota argentina", h.fmt_porcentaje(ca),
                         delta=None if pd.isna(cp) else f"{ca - cp:+.1f} pp".replace(".", ","))
            st.caption(f"Del {ini_u.strftime('%d/%m/%Y')} al {f_max.strftime('%d/%m/%Y')}, comparado con el mismo período de {f_max.year - 1}. "
                       "Respeta los filtros, salvo las fechas.")
        st.markdown("---")

        st.subheader("Mapa de conexiones")
        mc1, mc2 = st.columns(2)
        grosor = mc1.radio("Grosor de las líneas según", ["Pasajeros", "Vuelos"], horizontal=True, key="int_mapa_metrica")
        sem_min = mc2.slider("Frecuencia mínima por ruta (vuelos por semana)", 0, 30, 1, key="int_mapa_sem",
                             help="Muestra solo las rutas con al menos esta cantidad de vuelos semanales promedio en el período.")
        fig_mapa, n_r, n_c, faltan = _mapa(actual, h, grosor == "Pasajeros", sem_min, (hasta - desde).days + 1)
        if fig_mapa is None:
            st.info("No hay rutas para mostrar con esa frecuencia mínima. Probá bajarla.")
        else:
            h.graficar(fig_mapa, mapa=True)
            st.caption(f"{n_r} rutas y {n_c} ciudades de América. Líneas más gruesas = más {grosor.lower()}; los círculos de colores son "
                       "las ciudades extranjeras (azul: Sudamérica, verde: Centroamérica y Caribe, naranja: Norteamérica) y los grises, "
                       "los aeropuertos argentinos. Pasá el mouse para ver el detalle.")
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
        base_a = _filtrar(df, f_min, f_max, filtros_sin_fecha)
        if modo != opc[0]:
            base_a = base_a[base_a['mes_num'] <= f_max.month]
        ga = base_a.groupby(['ano_num', 'grupo'], observed=True)['pasajeros'].sum().reset_index()
        ga['ano_num'] = ga['ano_num'].astype(str)
        ga['grupo'] = ga['grupo'].astype(str)
        fig = px.bar(ga, x='ano_num', y='pasajeros', color='grupo', color_discrete_map=COLORES_GRUPO,
                     category_orders={'grupo': GRUPOS}, labels={'ano_num': 'Año', 'pasajeros': 'Pasajeros', 'grupo': ''})
        fig.update_layout(height=420, xaxis=dict(type='category'))
        h.graficar(fig, leyenda_abajo=True)
        nota = f" {f_max.year} está incompleto (hasta el {f_max.strftime('%d/%m/%Y')})." if modo == opc[0] and f_max.month < 12 else ""
        st.caption("Respeta los filtros, salvo las fechas: muestra todos los años de la base." + nota)

    # ================================================================ DESTINOS
    with tabs[1]:
        for nivel, col, titulo in (("pais", "pais", "Países"), ("destino", "destino", "Ciudades")):
            st.subheader(f"Ranking de {titulo.lower()}")
            t = _ranking(actual, previo, col, hay_prev, h)
            t = t.rename(columns={'clave': 'País' if nivel == 'pais' else 'Ciudad'})
            cfg = h.config_numerica(t, porcentajes=('Participación', 'Cuota argentina', 'Ocupación'))
            st.dataframe(t, use_container_width=True, hide_index=True, column_config=cfg,
                         height=int(min(len(t), 20) * 35 + 38))
            if nivel == "pais":
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
                       "aerolíneas argentinas (sin JetSMART). Podés ordenar por cualquier columna.")
            st.markdown("---")

    # ================================================================ AEROLÍNEAS
    with tabs[2]:
        st.subheader("Ranking de aerolíneas")
        ta = _ranking(actual, previo, 'aerolinea', hay_prev, h, con_grupo=True)
        ta = ta.rename(columns={'clave': 'Aerolínea'}).drop(columns=['Cuota argentina'])
        cfg = h.config_numerica(ta, porcentajes=('Participación', 'Ocupación'))
        if 'Cambio de cuota' in ta.columns:
            cfg['Cambio de cuota'] = st.column_config.NumberColumn('Cambio de cuota', format="%+.1f pp")
        st.dataframe(ta, use_container_width=True, hide_index=True, column_config=cfg, height=int(min(len(ta), 20) * 35 + 38))
        st.caption("Participación = parte de los pasajeros del período. Cambio de cuota = puntos porcentuales ganados o perdidos "
                   "frente al mismo período del año anterior.")
        if hay_prev and 'Cambio de cuota' in ta.columns:
            cambios = ta[ta['Cambio de cuota'].abs() >= 0.3].sort_values('Cambio de cuota')
            if not cambios.empty:
                st.markdown("#### Quién ganó y quién perdió cuota")
                fig = go.Figure(go.Bar(
                    x=cambios['Cambio de cuota'], y=cambios['Aerolínea'], orientation='h',
                    marker_color=['#10b981' if v >= 0 else '#ef4444' for v in cambios['Cambio de cuota']],
                    text=[f"{v:+.1f} pp".replace(".", ",") for v in cambios['Cambio de cuota']], textposition='outside', cliponaxis=False))
                fig.update_layout(height=max(240, 34 * len(cambios) + 100), showlegend=False,
                                  xaxis_title='Cambio de cuota (puntos porcentuales)', yaxis_title=None)
                h.graficar(fig)
                st.caption("Solo aerolíneas que movieron al menos 0,3 puntos porcentuales.")
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

    # ================================================================ RUTAS
    with tabs[3]:
        st.subheader("Ranking de rutas")
        dias = max((hasta - desde).days + 1, 1)
        tr = _ranking(actual, previo, 'ruta', hay_prev, h)
        ops = actual[actual['pasajeros'] > 0].groupby('ruta', observed=True)['aerolinea'].agg(
            lambda x: ", ".join(sorted(set(map(str, x)))))
        ops.index = ops.index.astype(str)
        vuelos_ruta = actual.groupby('ruta', observed=True)['vuelos'].sum()
        vuelos_ruta.index = vuelos_ruta.index.astype(str)
        tr.insert(2, 'Vuelos por semana', (tr['clave'].map(vuelos_ruta) / dias * 7).round(1))  # ida y vuelta
        tr['Aerolíneas'] = tr['clave'].map(ops)
        tr = tr.rename(columns={'clave': 'Ruta'})
        st.dataframe(tr, use_container_width=True, hide_index=True,
                     column_config=h.config_numerica(tr, porcentajes=('Participación', 'Cuota argentina', 'Ocupación')),
                     height=int(min(len(tr), 20) * 35 + 38))
        st.caption("Cada ruta une un aeropuerto argentino con una ciudad de América, sumando ambos sentidos. Vuelos por semana cuenta idas y vueltas (un vuelo diario en cada sentido = 14 por semana).")
        st.markdown("---")

        st.subheader("Rutas sin aerolíneas argentinas")
        sin = tr[(tr['Cuota argentina'].fillna(0) == 0)].copy()
        sin = sin[sin['Pasajeros'] >= max(1000, sin['Pasajeros'].quantile(0.25) if len(sin) else 0)]
        if sin.empty:
            st.info("En el período elegido, todas las rutas con movimiento relevante tienen alguna aerolínea argentina.")
        else:
            cols = ['Ruta', 'Pasajeros', 'Vuelos por semana', 'Var. %', 'Aerolíneas'] if 'Var. %' in sin.columns else \
                ['Ruta', 'Pasajeros', 'Vuelos por semana', 'Aerolíneas']
            st.dataframe(sin[cols], use_container_width=True, hide_index=True,
                         column_config=h.config_numerica(sin[cols]), height=int(min(len(sin), 15) * 35 + 38))
            st.caption("Rutas con al menos 1.000 pasajeros en el período donde no vuela ninguna aerolínea argentina "
                       "(JetSMART se cuenta aparte). Muestran mercados atendidos solo por compañías extranjeras.")

    # ================================================================ ESCALAS
    with tabs[4]:
        st.subheader("Vuelos que llegan con escala en América")
        st.markdown("Algunas aerolíneas de **Europa, Medio Oriente y África** llegan a Argentina haciendo **escala en otra ciudad "
                    "de América** (por ejemplo, Dubái → Río de Janeiro → Buenos Aires). En esta base aparece el último tramo, "
                    "entre la ciudad de escala y Argentina.")
        esc = actual[actual['grupo'] == 'Extranjeras de fuera de América']
        if esc.empty:
            st.info("No hay vuelos de aerolíneas de fuera de América con los filtros elegidos.")
        else:
            ge = esc.groupby(['aerolinea', 'destino'], observed=True).agg(
                Pasajeros=('pasajeros', 'sum'), Vuelos=('vuelos', 'sum'), Asientos=('asientos', 'sum')).reset_index()
            ge = ge[ge['Pasajeros'] >= 500]  # se descartan desvíos y vuelos ocasionales
            if ge.empty:
                st.info("En el período elegido no hay escalas regulares (solo vuelos ocasionales o desvíos).")
            else:
                ge['aerolinea'], ge['destino'] = ge['aerolinea'].astype(str), ge['destino'].astype(str)
                ge['Vuelos por semana'] = (ge['Vuelos'] / max((hasta - desde).days + 1, 1) * 7).round(1)
                ge['Ocupación'] = np.where(ge['Asientos'] > 0, ge['Pasajeros'] / ge['Asientos'] * 100, np.nan).round(1)
                ge = ge.sort_values('Pasajeros', ascending=False).rename(columns={'aerolinea': 'Aerolínea', 'destino': 'Ciudad de escala'})
                fig = px.bar(ge.iloc[::-1], x='Pasajeros', y='Aerolínea', color='Ciudad de escala', orientation='h',
                             labels={'Aerolínea': ''})
                fig.update_layout(height=max(280, 36 * ge['Aerolínea'].nunique() + 140))
                h.graficar(fig, leyenda_abajo=True)
                vista = ge[['Aerolínea', 'Ciudad de escala', 'Pasajeros', 'Vuelos', 'Vuelos por semana', 'Ocupación']]
                st.dataframe(vista, use_container_width=True, hide_index=True,
                             column_config=h.config_numerica(vista, porcentajes=('Ocupación',)))
                st.caption("Solo se muestran combinaciones con al menos 500 pasajeros en el período, para dejar afuera desvíos "
                           "y vuelos ocasionales. Pasajeros = los que vuelan entre la ciudad de escala y Argentina. "
                           "Vuelos por semana cuenta idas y vueltas (14 = un vuelo diario).")
        with st.expander("¿Y las escalas de las aerolíneas argentinas?"):
            st.markdown("La fuente oficial (SINTA/ANAC) registra solo los tramos que tocan un aeropuerto argentino y no informa el "
                        "número de vuelo. Por eso, si un vuelo de una aerolínea argentina sigue desde una ciudad de América hacia "
                        "otra (por ejemplo, Punta Cana → Miami), ese tramo no aparece acá. Para reconstruirlo haría falta otra "
                        "fuente, como el seguimiento de los aviones por radar (ADS-B).")

    # ================================================================ DATOS
    with tabs[5]:
        st.subheader("Descarga de datos filtrados")
        st.markdown("Descargá los datos del filtro aplicado para analizarlos en Excel o Python.")

        def _csv(d=actual):
            return d.drop(columns=['ciudad_clave']).to_csv(index=False, sep=';').encode('utf-8-sig')

        st.download_button("📥 Descargar datos filtrados (CSV)", data=_csv,
                           file_name=f"internacional_america_{date.today().strftime('%Y%m%d')}.csv", mime="text/csv")
        with st.expander("ℹ️ Metodología de esta sección"):
            st.markdown(f"""
**Fuente.** Tablero de conectividad aérea de SINTA (Ministerio de Turismo) con registros de ANAC, clasificación
"Internacional". Se incluyen solo los vuelos cuyo otro extremo está en América. Datos del **{f_min.strftime('%d/%m/%Y')}**
al **{f_max.strftime('%d/%m/%Y')}**; se actualizan automáticamente cada mes.

**Tipos de aerolínea**
- **Argentinas:** Aerolíneas Argentinas, Flybondi, Andes, LADE, American Jet y Flyest.
- **JetSMART (grupo regional):** la fuente agrupa sus filiales de Argentina, Chile y Perú en un solo nombre, así que no
  se puede separar la parte argentina.
- **Extranjeras de América** y **extranjeras de fuera de América** (estas últimas llegan con escala en otra ciudad de América).

**Indicadores.** Cuota argentina = pasajeros de aerolíneas argentinas ÷ pasajeros totales. Las rutas suman ambos sentidos.
Var. % compara contra el mismo período del año anterior. Vuelos por semana = vuelos del período ÷ días × 7.
""")


def _ranking(actual, previo, col, hay_prev, h, con_grupo=False):
    """Tabla de ranking por país, ciudad, ruta o aerolínea, con variación interanual y cuota argentina."""
    g = actual.groupby(col, observed=True).agg(Pasajeros=('pasajeros', 'sum'), Vuelos=('vuelos', 'sum'),
                                                Asientos=('asientos', 'sum')).reset_index()
    g = g[g['Vuelos'] > 0].rename(columns={col: 'clave'})
    g['clave'] = g['clave'].astype(str)
    total = max(g['Pasajeros'].sum(), 1)
    g['Participación'] = (g['Pasajeros'] / total * 100).round(1)
    g['Ocupación'] = np.where(g['Asientos'] > 0, g['Pasajeros'] / g['Asientos'] * 100, np.nan).round(1)
    arg = actual[actual['grupo'] == 'Argentinas'].groupby(col, observed=True)['pasajeros'].sum()
    arg.index = arg.index.astype(str)
    g['Cuota argentina'] = (g['clave'].map(arg).fillna(0) / g['Pasajeros'].replace(0, np.nan) * 100).round(1)
    if con_grupo:
        gr = actual.groupby(col, observed=True)['grupo'].first()
        gr.index = gr.index.astype(str)
        g.insert(1, 'Tipo', g['clave'].map(gr).astype(str))
    if hay_prev and not previo.empty:
        p = previo.groupby(col, observed=True)['pasajeros'].sum()
        p.index = p.index.astype(str)
        ant = g['clave'].map(p).fillna(0)
        g.insert(2 if not con_grupo else 3, 'Pasajeros año ant.', ant.astype(int))
        g.insert(3 if not con_grupo else 4, 'Var. %', [_txt_var(_var(a, b)) for a, b in zip(g['Pasajeros'], ant)])
        if con_grupo:
            tot_ant = max(p.sum(), 1)
            g['Cambio de cuota'] = (g['Participación'] - ant / tot_ant * 100).round(1)
    g = g.drop(columns=['Asientos']).sort_values('Pasajeros', ascending=False).reset_index(drop=True)
    return g


def _mapa(df, h, por_pasajeros, vuelos_semana_min, dias):
    """Mapa de rutas entre aeropuertos argentinos y ciudades de América."""
    g = df.groupby(['aeropuerto_arg', 'ciudad_clave', 'destino', 'region'], observed=True)[['pasajeros', 'vuelos']].sum().reset_index()
    for c in ('aeropuerto_arg', 'ciudad_clave', 'destino', 'region'):
        g[c] = g[c].astype(str)
    g = g[g['vuelos'] > 0]
    g['sem'] = g['vuelos'] / max(dias, 1) * 7
    g = g[g['sem'] >= vuelos_semana_min]
    if g.empty:
        return None, 0, 0, set()
    coord_arg = {**h.COORDENADAS, **COORD_ARG_EXTRA}
    g['sigla'] = g['aeropuerto_arg'].str[:3]
    faltan = set(g.loc[~g['ciudad_clave'].isin(COORD_CIUDADES), 'destino']) | set(g.loc[~g['sigla'].isin(coord_arg), 'aeropuerto_arg'])
    g = g[g['ciudad_clave'].isin(COORD_CIUDADES) & g['sigla'].isin(coord_arg)]
    if g.empty:
        return None, 0, 0, faltan
    col = 'pasajeros' if por_pasajeros else 'vuelos'
    vmax = max(float(g[col].max()), 1.0)
    g['nivel'] = np.clip((np.sqrt(g[col] / vmax) * 5).astype(int), 0, 4)
    fig = go.Figure()
    for nivel in range(5):
        sub = g[g['nivel'] == nivel]
        if sub.empty:
            continue
        lats, lons = [], []
        for s, c in zip(sub['sigla'], sub['ciudad_clave']):
            lats += [coord_arg[s][0], COORD_CIUDADES[c][0], None]
            lons += [coord_arg[s][1], COORD_CIUDADES[c][1], None]
        fig.add_trace(go.Scattergeo(lat=lats, lon=lons, mode='lines', hoverinfo='skip', showlegend=False,
                                    line=dict(width=0.8 + nivel * 1.6, color='rgba(29,78,216,0.40)')))
    # ciudades extranjeras
    ciu = g.groupby(['ciudad_clave', 'destino', 'region'])[['pasajeros', 'vuelos']].sum().reset_index()
    cmax = max(float(ciu[col].max()), 1.0)
    fig.add_trace(go.Scattergeo(
        lat=[COORD_CIUDADES[c][0] for c in ciu['ciudad_clave']], lon=[COORD_CIUDADES[c][1] for c in ciu['ciudad_clave']],
        mode='markers', showlegend=False,
        marker=dict(size=[6 + 22 * np.sqrt(v / cmax) for v in ciu[col]], color=[COLORES_REGION.get(r, '#64748b') for r in ciu['region']],
                    line=dict(width=1.2, color='white')),
        text=[f"<b>{d}</b><br>{int(p):,} pasajeros<br>{int(v):,} vuelos".replace(",", ".")
              for d, p, v in zip(ciu['destino'], ciu['pasajeros'], ciu['vuelos'])],
        hovertemplate='%{text}<extra></extra>'))
    # aeropuertos argentinos
    arg = g.groupby('sigla')[['pasajeros', 'vuelos']].sum().reset_index()
    amax = max(float(arg[col].max()), 1.0)
    fig.add_trace(go.Scattergeo(
        lat=[coord_arg[s][0] for s in arg['sigla']], lon=[coord_arg[s][1] for s in arg['sigla']],
        mode='markers+text', showlegend=False, text=list(arg['sigla']), textposition='middle left',
        textfont=dict(size=10, color='#0f172a'),
        marker=dict(size=[6 + 18 * np.sqrt(v / amax) for v in arg[col]], color='#475569', line=dict(width=1.2, color='white')),
        hovertext=[f"<b>{s}</b><br>{int(p):,} pasajeros internacionales".replace(",", ".") for s, p in zip(arg['sigla'], arg['pasajeros'])],
        hovertemplate='%{hovertext}<extra></extra>'))
    fig.update_geos(projection_type='mercator', lonaxis_range=[-125, -30], lataxis_range=[-56, 50],
                    showland=True, landcolor='#f1f5f9', showocean=True, oceancolor='#e0f2fe', showcountries=True,
                    countrycolor='#cbd5e1', showcoastlines=True, coastlinecolor='#94a3b8', resolution=110)
    fig.update_layout(height=640, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor='rgba(0,0,0,0)')
    return fig, len(g), ciu['ciudad_clave'].nunique(), faltan
