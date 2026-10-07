import pandas as pd
import requests

def actualizar_base():
    print("Buscando última base oficial de conectividad en SINTA...")
    # Conexión directa al catálogo de Datos Abiertos de Turismo (SINTA)
    url_catalogo = "https://datos.yvera.gob.ar/api/3/action/package_show?id=conectividad-aerea"
    
    try:
        r = requests.get(url_catalogo, timeout=30).json()
        recursos = r['result']['resources']
        
        # Encontrar el enlace del archivo CSV de frecuencias aéreas
        csv_url = None
        for rec in recursos:
            if 'csv' in rec.get('format', '').lower() and 'frecuencias' in rec.get('name', '').lower():
                csv_url = rec['url']
                break
        
        # Si no encontró el de frecuencias, toma el principal CSV
        if not csv_url:
            for rec in recursos:
                if 'csv' in rec.get('format', '').lower():
                    csv_url = rec['url']
                    break
        
        print(f"Descargando automáticamente desde: {csv_url}")
        df = pd.read_csv(csv_url, sep=None, engine='python', dtype=str)
        
        # Guardar la base limpia para la aplicación web
        df.to_csv("datos_actualizados.csv", index=False)
        print("¡Base datos_actualizados.csv actualizada con éxito!")
        
    except Exception as e:
        print(f"Error en la descarga automática: {e}")

if __name__ == '__main__':
    actualizar_base()
