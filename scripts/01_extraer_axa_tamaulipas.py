"""
01_extraer_axa_tamaulipas.py
Recorre los CSV crudos de AXA (I2DS) 2019-2023 y extrae los registros de las
seis ciudades de Tamaulipas del top-100 de Mision Cero.

Maneja las tres variantes de archivo que trae la entrega de AXA:
  - con encabezado y 43 columnas (2019, la primera columna va sin nombre)
  - con encabezado y 44 columnas (2020, 2021)
  - SIN encabezado, 44 columnas (varios meses de 2022 y 2023)
Por eso se lee siempre con header=None y se detecta si la fila 0 es encabezado
mirando la columna 17, que en el layout de AXA es siempre ESTADO.

Solo se conservan las columnas estables en los tres layouts (indices 0-18).
NO se intenta leer severidad de AXA: en las seis ciudades el campo FALLECIDO
no tiene un solo 'si' y NIVEL LESIONADO no tiene ningun 'alto' ni 'medio'.

Salida -> ../datos/axa_tamaulipas_6c_2019_2023.csv
"""
import pandas as pd, glob, unicodedata, os
from pathlib import Path

# AJUSTAR ESTA RUTA a la carpeta donde estan los CSV crudos de AXA
RAIZ = Path(r"C:\Users\arq_b\Documents\Urbanismo\POSDOC\POSDOC\2025\DATOS\AXA\DATOS I2S ACCIDENTES 2015-2024")
SAL  = Path(__file__).resolve().parent.parent / "datos" / "axa_tamaulipas_6c_2019_2023.csv"

CIUDADES = ['TAMPICO','CIUDAD MADERO','REYNOSA','VICTORIA','NUEVO LAREDO','MATAMOROS']
IDX = {'SINIESTRO':0,'LAT':1,'LON':2,'TIPOVEH':7,'ANIO':12,'MES':13,'HORA':16,'ESTADO':17,'CIUDAD':18}

def norm(s):
    return unicodedata.normalize('NFKD', str(s)).encode('ascii','ignore').decode().strip().upper()

archivos  = [str(RAIZ / 'incidentes_viales_2019_axa.csv')]
archivos += sorted(glob.glob(str(RAIZ / '2020' / '*.csv')))
archivos += sorted(glob.glob(str(RAIZ / 'incidentes_viales_2021_axa' / 'incidentes_viales_2021_axa' / '*.csv')))
archivos += sorted(glob.glob(str(RAIZ / 'incidentes_viales_2022_axa' / 'incidentes_viales_2022_axa' / '*.csv')))
archivos += sorted(glob.glob(str(RAIZ / 'incidentes_viales_2023_axa' / '*.csv')))
print(f"{len(archivos)} archivos de AXA por procesar")

partes = []
for f in archivos:
    df = pd.read_csv(f, low_memory=False, encoding='latin1', header=None, dtype=str)
    if norm(df.iloc[0, 17]) == 'ESTADO':          # la fila 0 era encabezado
        df = df.iloc[1:]
    d = pd.DataFrame({k: df.iloc[:, v].values for k, v in IDX.items()})
    d['ESTADO'] = d.ESTADO.map(norm)
    d = d[d.ESTADO == 'TAMAULIPAS'].copy()
    d['CIUDAD'] = d.CIUDAD.map(norm)
    d = d[d.CIUDAD.isin(CIUDADES)]
    d['_archivo'] = os.path.basename(f)
    partes.append(d)
    print(f"  {os.path.basename(f):55s} -> {len(d)}")

z = pd.concat(partes, ignore_index=True)
z['lat']  = pd.to_numeric(z.LAT,  errors='coerce')
z['lon']  = pd.to_numeric(z.LON,  errors='coerce')
z['ANIO'] = pd.to_numeric(z.ANIO, errors='coerce')
z = z[z.ANIO.between(2019, 2023)]
print(f"\nregistros vehiculo: {len(z)}  |  sin coordenada: {z.lat.isna().sum()} ({100*z.lat.isna().mean():.1f}%)")

z = z.dropna(subset=['lat','lon'])

# Marca de motocicleta. Se usa TIPO VEHICULO (indice 7), NO las columnas de bandera
# MOTOCICLETA/BICICLETA del final: en los archivos de 44 columnas esas banderas quedan
# corridas un lugar respecto a los de 43 y dan conteos falsos.
z['tipoveh'] = z.TIPOVEH.map(norm)
z['moto'] = z.tipoveh.str.contains('MOTOCICL', na=False)

# un renglon = un vehiculo; deduplicar a siniestro conservando si algun vehiculo era moto
moto_por_sin = z.groupby('SINIESTRO')['moto'].max()
z = z.drop_duplicates(subset=['SINIESTRO'])
z['moto'] = z.SINIESTRO.map(moto_por_sin)
SAL.parent.mkdir(parents=True, exist_ok=True)
z.to_csv(SAL, index=False, encoding='utf-8-sig')
print(f"siniestros unicos georreferenciados: {len(z)}")
print(f"con motocicleta involucrada: {int(z.moto.sum())} ({100*z.moto.mean():.2f}%)")
print(z.groupby('CIUDAD')['moto'].agg(['sum','count']))
print(f"\nGuardado en: {SAL}")
