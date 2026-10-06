import pandas as pd
import requests

def actualizar():
    print("Consultando dataset oficial de ANAC en Datos Abiertos...")
    # API pública de la Secretaría de Transporte para encontrar el último archivo
    api_url = "https://datos.transporte.gob.ar/api/3/action/package_show?id=aterrizajes-y-despegues-procesados-por-la-administracion-nacional-de-aviacion-civil-anac"
    res = requests.get(api_url).json()

    # Buscar el recurso CSV más reciente
    resources = res['result']['resources']
    csv_url = None
    for r in sorted(resources, key=lambda x: x.get('created', ''), reverse=True):
        if 'csv' in r.get('format', '').lower():
            csv_url = r['url']
            break

    if not csv_url:
        print("No se encontró recurso CSV.")
        return

    print(f"Descargando desde: {csv_url}")
    df = pd.read_csv(csv_url, sep=';', low_memory=False)
    df.columns = df.columns.str.strip().str.lower()

    # Filtros de negocio (Cabotaje y Despegue)
    df = df[
        df['clase de vuelo'].astype(str).str.lower().str.contains('cabotaje', na=False) &
        (df['tipo de movimiento'].astype(str).str.lower() == 'despegue')
    ].copy()

    # Guardar archivo limpio en el repositorio
    df.to_csv("datos_actualizados.csv", index=False)
    print("Archivo datos_actualizados.csv generado con éxito.")

if __name__ == '__main__':
    actualizar()
