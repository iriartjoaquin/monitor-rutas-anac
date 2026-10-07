import pandas as pd
import requests

def actualizar():
    print("Buscando base histórica completa de SINTA (2019 a hoy)...")
    url_catalogo = "https://datos.yvera.gob.ar/api/3/action/package_show?id=conectividad-aerea"
    
    try:
        r = requests.get(url_catalogo, timeout=30).json()
        recursos = r['result']['resources']
        
        csv_url = None
        for rec in recursos:
            nombre = rec.get('name', '').lower()
            fmt = rec.get('format', '').lower()
            if 'csv' in fmt and ('frecuencia' in nombre or 'base agregada' in nombre or 'vuelo' in nombre):
                csv_url = rec['url']
                break
        
        if not csv_url:
            for rec in recursos:
                if 'csv' in rec.get('format', '').lower():
                    csv_url = rec['url']
                    break
        
        print(f"Descargando base completa desde: {csv_url}")
        df = pd.read_csv(csv_url, sep=None, engine='python', dtype=str)
        
        # Guardar en formato comprimido (.csv.gz) para que pese solo ~4 MB con toda la historia completa desde 2019
        df.to_csv("datos_actualizados.csv.gz", index=False, compression='gzip')
        print("¡Base histórica completa (datos_actualizados.csv.gz) generada con éxito!")
        
    except Exception as e:
        print(f"Error al actualizar: {e}")

if __name__ == '__main__':
    actualizar()
