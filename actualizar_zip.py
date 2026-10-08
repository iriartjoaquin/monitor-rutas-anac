"""
Actualiza conectividad_aerea.zip desde el tablero de SINTA (https://tableros.yvera.tur.ar/conectividad/).

Hace lo mismo que hacés a mano: en la sección "Conectividad" elige Cabotaje, todas las clases de vuelo,
todo el período disponible y el desglose Año / Mes / Día / Empresa agrupada / Ruta / Origen / Destino,
y descarga el CSV. Antes de reemplazar el zip valida que el archivo nuevo sea consistente.

Uso:
    python actualizar_zip.py                 # solo actualiza si el tablero tiene datos más nuevos
    python actualizar_zip.py --forzar        # descarga y reemplaza aunque no haya datos más nuevos
    python actualizar_zip.py --salida X.zip  # escribe en otro archivo (para pruebas)
"""
import argparse
import io
import os
import sys
import tempfile
import zipfile
from datetime import date

import pandas as pd
from playwright.sync_api import sync_playwright

URL = "https://tableros.yvera.tur.ar/conectividad/"
ZIP_PATH = "conectividad_aerea.zip"
CSV_EN_ZIP = "conectividad_aerea.csv"
DESGLOSE = ["Año", "Mes", "Dia", "Empresa agrupada", "Ruta", "Origen aeropuerto", "Destino aeropuerto"]
COLUMNAS = DESGLOSE + ["Vuelos", "Pasajeros", "Asientos"]
MESES = {"Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, "Mayo": 5, "Junio": 6, "Julio": 7,
         "Agosto": 8, "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12}


def leer_zip(path):
    with zipfile.ZipFile(path) as z:
        nombre = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        with z.open(nombre) as f:
            return pd.read_csv(f)


def ultima_fecha(df):
    mes = df["Mes"].map(MESES)
    fechas = pd.to_datetime(dict(year=df["Año"], month=mes, day=df["Dia"]), errors="coerce")
    return fechas.max().date()


def marcar_salida(**kv):
    """Deja valores para los pasos siguientes del workflow de GitHub Actions."""
    ruta = os.environ.get("GITHUB_OUTPUT")
    if ruta:
        with open(ruta, "a", encoding="utf-8") as f:
            for k, v in kv.items():
                f.write(f"{k}={v}\n")


def validar(df_nuevo, df_actual, max_tablero):
    problemas = []
    if list(df_nuevo.columns) != COLUMNAS:
        problemas.append(f"Columnas distintas a las esperadas: {list(df_nuevo.columns)}")
        return problemas
    if df_nuevo[["Vuelos", "Pasajeros", "Asientos"]].isna().any().any():
        problemas.append("Hay valores vacíos en Vuelos/Pasajeros/Asientos.")
    if (df_nuevo[["Vuelos", "Pasajeros", "Asientos"]] < 0).any().any():
        problemas.append("Hay valores negativos en Vuelos/Pasajeros/Asientos.")
    if df_actual is not None and len(df_nuevo) < 0.95 * len(df_actual):
        problemas.append(f"El archivo nuevo tiene {len(df_nuevo):,} filas y el actual {len(df_actual):,} (caída > 5%).")
    if df_actual is not None and df_nuevo["Año"].min() > df_actual["Año"].min():
        problemas.append("El archivo nuevo empieza en un año posterior al actual (faltan años).")
    f_max = ultima_fecha(df_nuevo)
    if f_max < max_tablero.replace(day=1):
        problemas.append(f"La última fecha descargada ({f_max}) es anterior a la que informa el tablero ({max_tablero}).")
    return problemas


def descargar(destino):
    """Abre el tablero, aplica los filtros y descarga el CSV. Devuelve la fecha máxima disponible."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(accept_downloads=True, locale="es-AR")
        page = ctx.new_page()
        page.set_default_timeout(120_000)
        page.goto(URL, wait_until="domcontentloaded")
        page.wait_for_function("window.Shiny && Shiny.shinyapp && Shiny.shinyapp.config && Shiny.shinyapp.config.sessionId")
        page.evaluate("[...document.querySelectorAll('.nav a')].find(a => /CONECTIVIDAD$/i.test(a.innerText.trim())).click()")
        page.wait_for_function("document.querySelector('#fecha_conec') && jQuery('#agrup3')[0] && jQuery('#agrup3')[0].selectize")

        max_txt = page.evaluate("document.querySelector('#fecha_conec input').dataset.maxDate")
        min_txt = page.evaluate("document.querySelector('#fecha_conec input').dataset.minDate")
        max_tablero = date.fromisoformat(max_txt)
        min_tablero = date.fromisoformat(min_txt)
        print(f"Tablero: datos disponibles de {min_tablero} a {max_tablero}")

        if destino is None:  # solo consulta
            browser.close()
            return max_tablero, None

        page.evaluate("""([cols]) => {
            jQuery('#clasificacion')[0].selectize.setValue('Cabotaje');
            jQuery('#claseVuelo')[0].selectize.setValue('Todos');
            jQuery('#agrup3')[0].selectize.setValue(cols);
        }""", [DESGLOSE])
        page.evaluate("""([a, b]) => {
            const inp = jQuery('#fecha_conec input');
            inp.eq(0).bsDatepicker('setDate', new Date(a[0], a[1], a[2]));
            inp.eq(1).bsDatepicker('setDate', new Date(b[0], b[1], b[2]));
        }""", [[min_tablero.year, min_tablero.month - 1, min_tablero.day],
               [max_tablero.year, max_tablero.month - 1, max_tablero.day]])
        page.wait_for_timeout(5000)  # el servidor recalcula los filtros

        with page.expect_download(timeout=300_000) as d:
            page.click("#downloadCSVConec")
        d.value.save_as(destino)
        browser.close()
        return max_tablero, destino


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--forzar", action="store_true")
    ap.add_argument("--salida", default=ZIP_PATH)
    args = ap.parse_args()

    df_actual, f_actual = None, None
    if os.path.exists(ZIP_PATH):
        df_actual = leer_zip(ZIP_PATH)
        f_actual = ultima_fecha(df_actual)
        print(f"Zip actual: {len(df_actual):,} filas, última fecha {f_actual}")

    max_tablero, _ = descargar(None)
    if not args.forzar and f_actual is not None and max_tablero <= f_actual:
        print("Sin novedades: el tablero no tiene datos más nuevos que el zip.")
        marcar_salida(changed="false")
        return 0

    with tempfile.TemporaryDirectory() as tmp:
        csv_tmp = os.path.join(tmp, "descarga.csv")
        max_tablero, _ = descargar(csv_tmp)
        df_nuevo = pd.read_csv(csv_tmp)
        print(f"Descargado: {len(df_nuevo):,} filas, última fecha {ultima_fecha(df_nuevo)}")

        problemas = validar(df_nuevo, df_actual, max_tablero)
        if problemas:
            print("NO se reemplazó el zip. Problemas detectados:")
            for pr in problemas:
                print(" -", pr)
            marcar_salida(changed="false")
            return 1

        buf = io.StringIO()
        df_nuevo.to_csv(buf, index=False)
        with zipfile.ZipFile(args.salida, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            z.writestr(CSV_EN_ZIP, buf.getvalue())

    print(f"Zip actualizado: {args.salida}")
    marcar_salida(changed="true", ultima_fecha=ultima_fecha(df_nuevo).isoformat(), filas=len(df_nuevo))
    return 0


if __name__ == "__main__":
    sys.exit(main())
