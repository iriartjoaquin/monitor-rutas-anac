"""
Mapa de rutas que usan las dos secciones.

Es un mapa de calles (como Google Maps): se mueve arrastrando y se acerca con la rueda del mouse o con dos dedos.
Cada ruta es una línea con grosor según pasajeros o vuelos; al pasar el mouse por el medio de la línea se ve su detalle.
Si se elige un aeropuerto o ciudad, sus rutas se pintan de naranja y el resto queda en gris claro.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go

# Encuadres del mapa: centro (lat, lon) y zoom
VISTAS = {
    'Argentina': ((-39.5, -64.0), 2.8),
    'Sudamérica': ((-26.0, -62.0), 1.9),
    'Toda América': ((5.0, -75.0), 1.3),
}
AZUL, NARANJA, GRIS = 'rgba(29,78,216,0.55)', 'rgba(234,88,12,0.85)', 'rgba(148,163,184,0.25)'


def _num(x):
    return f"{int(round(x)):,}".replace(",", ".")


def mapa_rutas(rutas, nodos, por_pasajeros=True, foco=None, vista='Argentina', alto=620):
    """Arma el mapa.

    rutas: DataFrame con a, b (ids de los extremos), ruta (nombre), pasajeros, vuelos, frec (frecuencias semanales).
    nodos: DataFrame indexado por id con lat, lon, nombre, color, pasajeros, vuelos, rutas.
    foco: id de un nodo para destacar sus rutas (o None).
    """
    col = 'pasajeros' if por_pasajeros else 'vuelos'
    vmax = max(float(rutas[col].max()), 1.0)
    rutas = rutas.assign(nivel=np.clip((np.sqrt(rutas[col] / vmax) * 5).astype(int), 0, 4))
    if foco is not None:
        rutas = rutas.assign(destacada=(rutas['a'] == foco) | (rutas['b'] == foco))
    else:
        rutas = rutas.assign(destacada=False)
    fig = go.Figure()
    # líneas: un trazo por grosor y por color (las destacadas, arriba)
    for destacada in (False, True):
        for nivel in range(5):
            sub = rutas[(rutas['nivel'] == nivel) & (rutas['destacada'] == destacada)]
            if sub.empty:
                continue
            lats, lons = [], []
            for a, b in zip(sub['a'], sub['b']):
                lats += [nodos.at[a, 'lat'], nodos.at[b, 'lat'], None]
                lons += [nodos.at[a, 'lon'], nodos.at[b, 'lon'], None]
            color = NARANJA if destacada else (GRIS if foco is not None else AZUL)
            fig.add_trace(go.Scattermap(lat=lats, lon=lons, mode='lines', hoverinfo='skip', showlegend=False,
                                        line=dict(width=1 + nivel * 1.8, color=color)))
    # punto invisible en el medio de cada ruta, para ver su detalle al pasar el mouse
    visibles = rutas[rutas['destacada']] if foco is not None else rutas
    fig.add_trace(go.Scattermap(
        lat=[(nodos.at[a, 'lat'] + nodos.at[b, 'lat']) / 2 for a, b in zip(visibles['a'], visibles['b'])],
        lon=[(nodos.at[a, 'lon'] + nodos.at[b, 'lon']) / 2 for a, b in zip(visibles['a'], visibles['b'])],
        mode='markers', marker=dict(size=14, opacity=0), showlegend=False,
        hovertext=[f"<b>{r}</b><br>{_num(p)} pasajeros<br>{_num(v)} vuelos · "
                   f"{f'{f:.1f}'.replace('.', ',')} frecuencias semanales"
                   for r, p, v, f in zip(visibles['ruta'], visibles['pasajeros'], visibles['vuelos'], visibles['frec'])],
        hovertemplate='%{hovertext}<extra></extra>'))
    # aeropuertos y ciudades: tamaño según movimiento
    usados = nodos.loc[sorted(set(rutas['a']) | set(rutas['b']))]
    nmax = max(float(usados[col].max()), 1.0)
    tam = 8 + 26 * np.sqrt(usados[col] / nmax)
    colores = usados['color'].copy()
    if foco is not None:
        vecinos = set(rutas.loc[rutas['destacada'], 'a']) | set(rutas.loc[rutas['destacada'], 'b'])
        colores = colores.where(usados.index.isin(vecinos), '#cbd5e1')
    fig.add_trace(go.Scattermap(
        lat=usados['lat'], lon=usados['lon'], mode='markers', showlegend=False,
        marker=dict(size=tam, color=colores, opacity=0.9),
        hovertext=[f"<b>{n}</b><br>{int(r)} rutas<br>{_num(p)} pasajeros<br>{_num(v)} vuelos"
                   for n, r, p, v in zip(usados['nombre'], usados['rutas'], usados['pasajeros'], usados['vuelos'])],
        hovertemplate='%{hovertext}<extra></extra>'))
    if foco is not None and foco in nodos.index:
        fig.add_trace(go.Scattermap(lat=[nodos.at[foco, 'lat']], lon=[nodos.at[foco, 'lon']], mode='markers',
                                    marker=dict(size=float(tam.get(foco, 20)) + 8, color='#ea580c'), hoverinfo='skip',
                                    showlegend=False))
    (lat, lon), zoom = VISTAS.get(vista, VISTAS['Argentina'])
    fig.update_layout(map=dict(style='carto-positron', center=dict(lat=lat, lon=lon), zoom=zoom),
                      height=alto, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor='rgba(0,0,0,0)')
    return fig


def nodos_desde_rutas(rutas, coords, nombres, colores):
    """Totales por aeropuerto o ciudad a partir de las rutas (pasajeros, vuelos y cantidad de rutas)."""
    filas = []
    for extremo in ('a', 'b'):
        filas.append(rutas[[extremo, 'pasajeros', 'vuelos']].rename(columns={extremo: 'id'}))
    t = pd.concat(filas).groupby('id').agg(pasajeros=('pasajeros', 'sum'), vuelos=('vuelos', 'sum'), rutas=('id', 'size'))
    t['lat'] = [coords[i][0] for i in t.index]
    t['lon'] = [coords[i][1] for i in t.index]
    t['nombre'] = [nombres.get(i, i) for i in t.index]
    t['color'] = [colores.get(i, '#475569') for i in t.index]
    return t
