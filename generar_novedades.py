"""
Agente mensual: calcula qué cambió en el último mes publicado y lo guarda en novedades.json (lo muestra la página)
y en novedades_mail.md (el texto del aviso que se manda por mail).

Uso: python generar_novedades.py
"""
import json
import os
from datetime import datetime, timezone

import datos
import internacional
import novedades

URL_PAGINA = "https://monitor-rutas-anac-aqkgos7zqbvy7utelsx7mx.streamlit.app/"


def main():
    cab, err = datos.cargar_cabotaje('conectividad_aerea.zip')
    if err:
        raise SystemExit(f"No se pudo leer la base de cabotaje: {err}")
    ruta_js = internacional.REFERENCIA_JETSMART
    inter = internacional.cargar_internacional(
        internacional.ZIP_INTERNACIONAL, os.path.getmtime(internacional.ZIP_INTERNACIONAL),
        datos.construir_etiqueta_aeropuerto, datos.limpiar_mojibake_texto,
        os.path.getmtime(ruta_js) if os.path.exists(ruta_js) else 0,
        {**datos.COORDENADAS, **internacional.COORD_ARG_EXTRA})

    salida = {'generado': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
              'cabotaje': novedades.calcular(cab, 'ruta_label')}
    if inter is not None:
        salida['internacional'] = novedades.calcular(inter, 'ruta_mercado', cuota_argentina=True)
    with open('novedades.json', 'w', encoding='utf-8') as f:
        json.dump(salida, f, ensure_ascii=False, indent=1)

    partes = [f"Hola, ya están los datos de **{salida['cabotaje']['mes_txt']}** en el "
              f"[Monitor de Rutas Aéreas]({URL_PAGINA}). Esto es lo que cambió.",
              novedades.markdown("✈️ Cabotaje", salida['cabotaje'])]
    if 'internacional' in salida:
        partes.append(novedades.markdown("🌎 Internacional – América", salida['internacional']))
    partes.append("_Fuente: SINTA (Turismo) con datos de ANAC. Rutas de cabotaje por aeropuerto; internacionales por "
                  "ciudad. Una aerolínea \"vuela\" una ruta si hizo al menos 4 vuelos en el mes._")
    with open('novedades_mail.md', 'w', encoding='utf-8') as f:
        f.write("\n\n".join(partes) + "\n")
    print(f"Novedades de {salida['cabotaje']['mes_txt']} listas.")


if __name__ == '__main__':
    main()
