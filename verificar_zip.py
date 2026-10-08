"""
Chequeo liviano (solo librería estándar, sin navegador) para saber si hace falta actualizar el zip.

Regla: durante el mes M, el zip tiene que llegar hasta el último día del mes M-1.
Si ya llega, el mes está "resuelto" y el agente no hace nada hasta el mes siguiente.

Escribe pendiente=true/false en GITHUB_OUTPUT (y lo imprime).
Uso: python verificar_zip.py [--hoy AAAA-MM-DD]   (--hoy es solo para pruebas)
"""
import argparse
import calendar
import csv
import io
import os
import zipfile
from datetime import date

ZIP_PATH = "conectividad_aerea.zip"
MESES = {"Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, "Mayo": 5, "Junio": 6, "Julio": 7,
         "Agosto": 8, "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12}


def ultima_fecha_zip(path):
    if not os.path.exists(path):
        return None
    with zipfile.ZipFile(path) as z:
        nombre = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        with z.open(nombre) as f:
            lector = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8"))
            maximo = (0, 0, 0)
            for fila in lector:
                clave = (int(fila["Año"]), MESES[fila["Mes"]], int(fila["Dia"]))
                if clave > maximo:
                    maximo = clave
    return date(*maximo)


def fin_mes_anterior(hoy):
    anio, mes = (hoy.year, hoy.month - 1) if hoy.month > 1 else (hoy.year - 1, 12)
    return date(anio, mes, calendar.monthrange(anio, mes)[1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hoy", default=None)
    args = ap.parse_args()
    hoy = date.fromisoformat(args.hoy) if args.hoy else date.today()

    esperada = fin_mes_anterior(hoy)
    actual = ultima_fecha_zip(ZIP_PATH)
    pendiente = actual is None or actual < esperada
    print(f"Hoy: {hoy} | el zip debería llegar al {esperada} | llega al {actual} -> "
          f"{'FALTA actualizar' if pendiente else 'ya está actualizado este mes'}")

    ruta = os.environ.get("GITHUB_OUTPUT")
    if ruta:
        with open(ruta, "a", encoding="utf-8") as f:
            f.write(f"pendiente={'true' if pendiente else 'false'}\n")


if __name__ == "__main__":
    main()
