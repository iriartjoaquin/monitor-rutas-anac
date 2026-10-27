"""
Separa los vuelos internacionales de JetSMART entre su filial argentina y la chilena.

SINTA informa a JetSMART con un solo nombre, pero el dataset "Aterrizajes y despegues procesados por la ANAC"
(datos.gob.ar) trae el nombre legal de la empresa en cada movimiento:
  - JETSMART AIRLINES S.A.  -> JetSMART Argentina
  - JETSMART AIRLINES SPA   -> JetSMART Chile
Este script cuenta, para cada mes, aeropuerto argentino y ciudad extranjera, cuántos vuelos hizo cada filial,
y guarda el resultado en jetsmart_operador.csv (un archivo chico que usa la sección internacional).

Uso:
    python actualizar_jetsmart.py              # descarga de ANAC los años que falten y actualiza la referencia
    python actualizar_jetsmart.py --todo       # recalcula todos los años (2019 en adelante)
    python actualizar_jetsmart.py --verificar  # chequeo liviano: ¿la referencia está atrasada respecto de la base internacional?
"""
import argparse
import csv
import io
import json
import os
import sys
import urllib.request
import zipfile
from datetime import date

SALIDA = "jetsmart_operador.csv"
ZIP_INTERNACIONAL = "internacional_america.zip"
PAQUETE = "aterrizajes-y-despegues-procesados-por-la-administracion-nacional-de-aviacion-civil-anac"
API = f"https://datos.gob.ar/api/3/action/package_show?id={PAQUETE}"
PRIMER_ANIO = 2019
EMPRESAS = {"JETSMART AIRLINES S.A.": "ar", "JETSMART AIRLINES SPA": "cl"}
MESES = {"Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, "Mayo": 5, "Junio": 6, "Julio": 7,
         "Agosto": 8, "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12}

# Códigos de aeropuertos argentinos que usa ANAC -> sigla IATA que usa la página
AEROPUERTOS_ANAC = {
    'AER': 'AEP', 'EZE': 'EZE', 'PAL': 'EPA', 'CBA': 'COR', 'DOZ': 'MDZ', 'ROS': 'ROS', 'SAL': 'SLA', 'BAR': 'BRC',
    'IGU': 'IGR', 'NEU': 'NQN', 'SIS': 'RES', 'CRV': 'CRD', 'GAL': 'RGL', 'TUC': 'TUC', 'USU': 'USH', 'ECA': 'FTE',
    'JUJ': 'JUJ', 'SJU': 'UAQ', 'MDP': 'MDQ', 'TRE': 'REL', 'POS': 'PSS', 'COR': 'CNQ',
}
# Aeropuertos extranjeros (código OACI) -> ciudad tal como la nombra SINTA
CIUDADES_OACI = {
    'SBGL': 'Río de Janeiro', 'SBRJ': 'Río de Janeiro', 'SCEL': 'Santiago', 'SGAS': 'Asunción', 'SBFL': 'Florianópolis',
    'SBRF': 'Recife', 'SBSG': 'Natal', 'SBNT': 'Parnamirim', 'SPJC': 'Lima', 'SPIM': 'Lima', 'SUMU': 'Montevideo',
    'SUAA': 'Montevideo', 'SBGR': 'São Paulo', 'SBKP': 'São Paulo', 'SBSP': 'São Paulo', 'SCDA': 'Iquique',
    'SBBR': 'Brasilia', 'SCNT': 'Puerto Natales', 'SBPA': 'Porto Alegre', 'SBSV': 'Salvador', 'SBFI': 'Foz Do Iguaçu',
    'SCTE': 'Puerto Montt', 'SCFA': 'Antofagasta', 'SCIE': 'Concepcion', 'SCSE': 'La Serena', 'SPZO': 'Cusco',
    'SBCT': 'Curitiba', 'SBFZ': 'Fortaleza', 'SBMO': 'Maceió', 'SBPS': 'Porto Seguro', 'SBCF': 'Belo Horizonte',
    'SCCI': 'Punta Arenas', 'SCAR': 'Arica', 'SCCF': 'Calama', 'SKBO': 'Bogotá', 'SKRG': 'Medellín', 'SEQM': 'Quito',
    'SLVR': 'Santa Cruz de la Sierra', 'MPTO': 'Panamá', 'SBJP': 'João Pessoa', 'SBNF': 'Navegantes',
    'SULS': 'Punta del Este', 'KMIA': 'Miami', 'MROC': 'Alajuela', 'SEGU': 'Guayaquil',
}


def marcar_salida(**kv):
    ruta = os.environ.get("GITHUB_OUTPUT")
    if ruta:
        with open(ruta, "a", encoding="utf-8") as f:
            for k, v in kv.items():
                f.write(f"{k}={v}\n")


def ultimo_mes_internacional():
    """Último (año, mes) de la base internacional de SINTA, sin pandas."""
    if not os.path.exists(ZIP_INTERNACIONAL):
        return None
    with zipfile.ZipFile(ZIP_INTERNACIONAL) as z:
        nombre = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        with z.open(nombre) as f:
            maximo = (0, 0)
            for fila in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8")):
                maximo = max(maximo, (int(fila["Año"]), MESES[fila["Mes"]]))
    return maximo


def ultimo_mes_referencia():
    if not os.path.exists(SALIDA):
        return None
    with open(SALIDA, encoding="utf-8") as f:
        meses = [(int(r["anio"]), int(r["mes"])) for r in csv.DictReader(f)]
    return max(meses) if meses else None


def recursos_por_anio():
    req = urllib.request.Request(API, headers={"User-Agent": "monitor-rutas-anac"})
    with urllib.request.urlopen(req, timeout=60) as r:
        datos = json.load(r)
    salida = {}
    for rec in datos["result"]["resources"]:
        nombre = rec.get("name", "")
        for anio in range(PRIMER_ANIO, date.today().year + 1):
            if str(anio) in nombre:
                salida[anio] = rec["url"]
    return salida


def contar_anio(url):
    """Cuenta los vuelos internacionales de cada filial de JetSMART por mes, aeropuerto argentino y ciudad."""
    import pandas as pd
    req = urllib.request.Request(url, headers={"User-Agent": "monitor-rutas-anac"})
    with urllib.request.urlopen(req, timeout=600) as r:
        contenido = r.read()
    d = pd.read_csv(io.BytesIO(contenido), sep=';', dtype=str, on_bad_lines='skip')
    d.columns = [c.strip() for c in d.columns]
    col_clas = next(c for c in d.columns if c.startswith('Clasific'))
    d = d[d['Aerolinea Nombre'].isin(EMPRESAS) & d[col_clas].str.startswith('Inter', na=False)]
    fecha = pd.to_datetime(d['Fecha UTC'], format='%d/%m/%Y', errors='coerce')
    t = pd.DataFrame({
        'anio': fecha.dt.year, 'mes': fecha.dt.month,
        'sigla_arg': d['Aeropuerto'].map(AEROPUERTOS_ANAC),
        'ciudad': d['Origen / Destino'].map(CIUDADES_OACI),
        'filial': d['Aerolinea Nombre'].map(EMPRESAS),
    }).dropna()
    t = t.groupby(['anio', 'mes', 'sigla_arg', 'ciudad', 'filial']).size().unstack('filial', fill_value=0)
    for col in ('ar', 'cl'):
        if col not in t.columns:
            t[col] = 0
    t = t.rename(columns={'ar': 'vuelos_ar', 'cl': 'vuelos_cl'})[['vuelos_ar', 'vuelos_cl']].reset_index()
    t[['anio', 'mes']] = t[['anio', 'mes']].astype(int)
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--todo", action="store_true")
    ap.add_argument("--verificar", action="store_true")
    args = ap.parse_args()

    ref, inter = ultimo_mes_referencia(), ultimo_mes_internacional()
    pendiente = ref is None or (inter is not None and ref < inter)
    print(f"Referencia JetSMART hasta {ref} | base internacional hasta {inter} -> {'FALTA actualizar' if pendiente else 'al día'}")
    if args.verificar:
        marcar_salida(pendiente_js='true' if pendiente else 'false')
        return 0
    if not pendiente and not args.todo:
        marcar_salida(changed='false')
        return 0

    import pandas as pd
    recursos = recursos_por_anio()
    if args.todo or ref is None:
        anios = sorted(recursos)
    else:  # el año de la referencia y los siguientes (ANAC corrige datos del año en curso)
        anios = sorted(a for a in recursos if a >= ref[0])
    print("Años a procesar:", anios)
    previa = pd.read_csv(SALIDA) if os.path.exists(SALIDA) else None
    nuevos = []
    for anio in anios:
        t = contar_anio(recursos[anio])
        print(f"  {anio}: {len(t)} combinaciones mes/aeropuerto/ciudad, vuelos AR {t['vuelos_ar'].sum()}, CL {t['vuelos_cl'].sum()}")
        nuevos.append(t)
    nuevo = pd.concat(nuevos, ignore_index=True)
    if previa is not None:
        nuevo = pd.concat([previa[~previa['anio'].isin(anios)], nuevo], ignore_index=True)
    nuevo = nuevo.sort_values(['anio', 'mes', 'sigla_arg', 'ciudad']).reset_index(drop=True)
    if nuevo.empty or (nuevo['vuelos_ar'] + nuevo['vuelos_cl']).sum() == 0:
        print("NO se actualizó: la descarga de ANAC no trajo vuelos de JetSMART.")
        marcar_salida(changed='false')
        return 1
    cambio = previa is None or not previa.reset_index(drop=True).equals(nuevo)
    nuevo.to_csv(SALIDA, index=False)
    ult = nuevo.iloc[-1]
    print(f"Referencia escrita: {SALIDA} ({len(nuevo)} filas, hasta {int(ult['anio'])}-{int(ult['mes']):02d}). Cambios: {cambio}")
    marcar_salida(changed='true' if cambio else 'false')
    return 0


if __name__ == "__main__":
    sys.exit(main())
