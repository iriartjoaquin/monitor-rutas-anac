"""
Qué cambió en el último mes publicado (sin Streamlit).

Lo calcula el agente mensual (generar_novedades.py) y lo guarda en novedades.json; la página lo muestra arriba de
cada sección y el mismo texto se manda por mail.
"""
import pandas as pd

MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre',
         'noviembre', 'diciembre']
MIN_VUELOS = 4               # una aerolínea "vuela" una ruta en el mes si hizo al menos 4 vuelos (criterio de SINTA)
MIN_CUOTA_PP = 0.5           # cambios de cuota más chicos no se destacan
MIN_PAX_RUTA = 5000          # rutas con menos pasajeros el año anterior no entran en "más crecieron / más cayeron"


def _num(x):
    return f"{int(round(x)):,}".replace(",", ".")


def _pct(x, signo=True):
    return f"{x:{'+' if signo else ''}.1f}%".replace(".", ",")


def _pp(x):
    return f"{x:+.1f} pp".replace(".", ",")


def _mes_txt(p):
    return f"{MESES[p.month - 1]} {p.year}"


def ultimo_mes_completo(df):
    """Último mes con datos completos (si la base es diaria y el mes está a medias, el anterior)."""
    per = df['fecha'].dt.to_period('M')
    ult = per.max()
    fechas = df.loc[per == ult, 'fecha']
    if fechas.nunique() > 1 and fechas.max().day < ult.days_in_month:
        ult -= 1
    return ult


def calcular(df, col_ruta, cuota_argentina=False):
    """Resumen del último mes contra el mismo mes del año anterior (volumen y cuotas) y contra el mes anterior
    (quién empezó o dejó de volar cada ruta). df: fecha, aerolinea, pasajeros, asientos, vuelos y la columna de ruta."""
    per = df['fecha'].dt.to_period('M')
    mes = ultimo_mes_completo(df)
    u, ly, ma = df[per == mes], df[per == mes - 12], df[per == mes - 1]
    res = {'mes': str(mes), 'mes_txt': _mes_txt(mes), 'ly_txt': _mes_txt(mes - 12), 'ant_txt': _mes_txt(mes - 1),
           'kpis': [], 'destacados': [], 'altas': [], 'bajas': []}

    # 1) totales del mes contra el mismo mes del año anterior
    def tot(d):
        return d['pasajeros'].sum(), d['asientos'].sum(), d['vuelos'].sum()
    (p, a, v), (p0, a0, v0) = tot(u), tot(ly)
    res['kpis'] = [
        {'nombre': 'Pasajeros', 'valor': _num(p), 'delta': _pct((p / p0 - 1) * 100) if p0 else None},
        {'nombre': 'Asientos', 'valor': _num(a), 'delta': _pct((a / a0 - 1) * 100) if a0 else None},
        {'nombre': 'Vuelos', 'valor': _num(v), 'delta': _pct((v / v0 - 1) * 100) if v0 else None},
        {'nombre': 'Ocupación', 'valor': _pct(p / a * 100, False) if a else 's/d',
         'delta': _pp(p / a * 100 - p0 / a0 * 100) if a and a0 else None},
    ]
    if cuota_argentina:
        def cuota(d):
            t = d['pasajeros'].sum()
            return d.loc[d['grupo'] == 'Argentinas', 'pasajeros'].sum() / t * 100 if t else None
        c, c0 = cuota(u), cuota(ly)
        res['kpis'].append({'nombre': 'Cuota argentina', 'valor': _pct(c, False) if c is not None else 's/d',
                            'delta': _pp(c - c0) if c is not None and c0 is not None else None})

    # 2) aerolíneas que más ganaron o perdieron cuota de pasajeros
    if p0:
        cu = u.groupby('aerolinea', observed=True)['pasajeros'].sum()
        c0 = ly.groupby('aerolinea', observed=True)['pasajeros'].sum()
        t = pd.concat([cu.rename('p'), c0.rename('p0')], axis=1).fillna(0)
        t['d'] = t['p'] / p * 100 - t['p0'] / p0 * 100
        t = t[t['d'].abs() >= MIN_CUOTA_PP].sort_values('d', key=abs, ascending=False).head(4)
        for aero, f in t.iterrows():
            var = (" (no volaba)" if not f['p0'] else " (dejó de volar)" if not f['p']
                   else f" (pasajeros {_pct((f['p'] / f['p0'] - 1) * 100)})")
            verbo = "ganó" if f['d'] > 0 else "perdió"
            res['destacados'].append(f"**{aero}** {verbo} {abs(f['d']):.1f} pp de cuota{var}.".replace('.', ',', 1))

        # 3) rutas que más crecieron y más cayeron en pasajeros
        ru = u.groupby(col_ruta, observed=True)['pasajeros'].sum()
        r0 = ly.groupby(col_ruta, observed=True)['pasajeros'].sum()
        r = pd.concat([ru.rename('p'), r0.rename('p0')], axis=1).fillna(0)
        r = r[r['p0'] >= MIN_PAX_RUTA]
        r['d'] = r['p'] - r['p0']
        for nombre, f in r.nlargest(2, 'd').iterrows():
            if f['d'] > 0:
                res['destacados'].append(f"**{nombre}** fue de las que más crecieron: {_num(f['p'])} pasajeros "
                                         f"({_pct((f['p'] / f['p0'] - 1) * 100)}).")
        for nombre, f in r.nsmallest(2, 'd').iterrows():
            if f['d'] < 0:
                res['destacados'].append(f"**{nombre}** fue de las que más cayeron: {_num(f['p'])} pasajeros "
                                         f"({_pct((f['p'] / f['p0'] - 1) * 100)}).")

    # 4) quién empezó o dejó de volar cada ruta, contra el mes anterior
    if not ma.empty:
        g = [col_ruta, 'aerolinea']
        ahora = u.groupby(g, observed=True)[['vuelos', 'pasajeros']].sum()
        antes = ma.groupby(g, observed=True)[['vuelos', 'pasajeros']].sum()
        m = ahora.join(antes, rsuffix='_ant', how='outer').fillna(0).reset_index()
        altas = m[(m['vuelos'] >= MIN_VUELOS) & (m['vuelos_ant'] == 0)].sort_values('pasajeros', ascending=False)
        bajas = m[(m['vuelos_ant'] >= MIN_VUELOS) & (m['vuelos'] == 0)].sort_values('pasajeros_ant', ascending=False)
        res['altas'] = [{'ruta': str(f[col_ruta]), 'aerolinea': str(f['aerolinea']), 'vuelos': int(f['vuelos']),
                         'pasajeros': int(f['pasajeros'])} for _, f in altas.iterrows()]
        res['bajas'] = [{'ruta': str(f[col_ruta]), 'aerolinea': str(f['aerolinea']), 'vuelos': int(f['vuelos_ant']),
                         'pasajeros': int(f['pasajeros_ant'])} for _, f in bajas.iterrows()]
    return res


def markdown(titulo, n, max_rutas=8):
    """El resumen como texto (para el mail)."""
    lin = [f"### {titulo}: {n['mes_txt']}", "",
           f"Comparado con {n['ly_txt']} (mismo mes del año anterior):", ""]
    lin += [f"- **{k['nombre']}:** {k['valor']}" + (f" ({k['delta']})" if k['delta'] else "") for k in n['kpis']]
    if n['destacados']:
        lin += ["", "**Lo que más se movió**", ""] + [f"- {d}" for d in n['destacados']]
    for clave, txt in (('altas', 'Empezaron a volar'), ('bajas', 'Dejaron de volar')):
        filas = n[clave]
        lin += ["", f"**{txt} frente a {n['ant_txt']} ({len(filas)})**", ""]
        if not filas:
            lin.append("- Ninguna.")
        for f in filas[:max_rutas]:
            lin.append(f"- {f['aerolinea']}: {f['ruta']} ({_num(f['vuelos'])} vuelos)")
        if len(filas) > max_rutas:
            lin.append(f"- … y {len(filas) - max_rutas} más (ver la página).")
    return "\n".join(lin)
