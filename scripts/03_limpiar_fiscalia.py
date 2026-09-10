"""
03_limpiar_fiscalia.py
Limpia el ANEXO.xlsx de la Fiscalia General de Justicia de Tamaulipas
(oficio FGJ/DGAJDH/IP/12551/2026, folio 811197026000256).

Estructura entregada: 8 columnas. UNIDAD, FECHA DE INICIO, ANO, DELITO,
MODALIDAD, MUNICIPIO_HECHO, LATITUD, LONGITUD. NO trae hora del hecho, ni
numero de victimas por evento, ni tipo de vehiculo, ni causa.

Dos arreglos obligatorios:
 1) 766 registros traen la longitud SIN el signo negativo -> se voltea.
 2) 358 registros traen coordenadas invalidas (ceros, 111, texto) -> se marcan.

Salida -> ../datos/fiscalia_tamaulipas_limpio.csv
"""
import pandas as pd
from pathlib import Path

# AJUSTAR ESTA RUTA
ENT = Path(r"C:\Users\arq_b\Documents\Urbanismo\POSDOC\POSDOC\2025\SEMESTRES\SEMESTRE 3\TRANSPARENCIA\TAMAULIPAS\FISCALIAS\26000256\ANEXO.xlsx")
SAL = Path(__file__).resolve().parent.parent / "datos" / "fiscalia_tamaulipas_limpio.csv"

df = pd.read_excel(ENT)
df.columns = [c.strip() for c in df.columns]
for c in ['UNIDAD','DELITO','MODALIDAD','MUNICIPIO_HECHO']:
    df[c] = df[c].astype(str).str.strip()

df['lat'] = pd.to_numeric(df['LATITUD'],  errors='coerce')
df['lon'] = pd.to_numeric(df['LONGITUD'], errors='coerce')

n_signo = (df.lon > 0).sum()
df.loc[df.lon > 0, 'lon'] = -df.loc[df.lon > 0, 'lon']          # arreglo 1

valido = df.lat.between(22, 28) & df.lon.between(-100, -97)      # arreglo 2
df['geo_ok'] = valido

print(f"registros: {len(df)}")
print(f"longitud con signo invertido (corregida): {n_signo}")
print(f"geolocalizables: {valido.sum()} ({100*valido.mean():.1f}%)")
print(df.groupby(['MUNICIPIO_HECHO','DELITO']).size().unstack(fill_value=0))

SAL.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(SAL, index=False, encoding='utf-8-sig')
print(f"\nGuardado en: {SAL}")
