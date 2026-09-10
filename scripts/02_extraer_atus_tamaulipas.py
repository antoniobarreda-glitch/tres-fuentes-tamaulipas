"""
02_extraer_atus_tamaulipas.py
Filtra la ATUS georreferenciada del INEGI (2019-2023) a las seis ciudades de
Tamaulipas y arma las capas de desenlace.

OJO con las claves de municipio (aqui se equivoca facil):
  38 Tampico | 09 Ciudad Madero | 32 REYNOSA (no Madero) | 41 Victoria
  27 Nuevo Laredo | 22 Matamoros | 03 Altamira (fuera del top-100)

Salida -> ../datos/atus_tamaulipas_6c_2019_2023.csv
"""
import pandas as pd, glob
from pathlib import Path

# AJUSTAR ESTA RUTA
RUTA = Path(r"C:\Users\arq_b\Documents\Urbanismo\POSDOC\POSDOC\2025\DATOS\INEGI\ATUS_georreferenciado_2019_2024")
SAL  = Path(__file__).resolve().parent.parent / "datos" / "atus_tamaulipas_6c_2019_2023.csv"

MPIO = {38:'TAMPICO', 9:'CIUDAD MADERO', 32:'REYNOSA', 41:'VICTORIA',
        27:'NUEVO LAREDO', 22:'MATAMOROS'}

partes = []
for anio in range(2019, 2024):
    f = glob.glob(str(RUTA / f'*{anio}.csv'))[0]
    df = pd.read_csv(f, low_memory=False, encoding='latin1')
    df.columns = [c.strip().upper() for c in df.columns]
    d = df[(df.EDO == 28) & (df.MPIO.isin(MPIO))].copy()
    partes.append(d)
    print(anio, len(d), d.MPIO.map(MPIO).value_counts().to_dict())

z = pd.concat(partes, ignore_index=True)
z['CIUDAD'] = z.MPIO.map(MPIO)
z['vru'] = z.PEATMUERTO + z.PEATHERIDO + z.CICLMUERTO + z.CICLHERIDO   # victimas peaton + ciclista
z['ksi'] = z.TOTMUERTOS + z.TOTHERIDOS                                  # victimas totales del evento
# Motociclistas: la ATUS marca si hubo moto en el siniestro (MOTOCICLET) pero cuenta a las
# personas como conductora/pasajera SIN decir de que vehiculo. Se define la capa como
# victimas ocupantes en siniestros con moto, excluyendo peaton y ciclista para no
# duplicarlos con la capa VRU. Sobreestima si tambien se lesiono quien iba en el auto:
# declararlo como limitacion.
z['moto_ev']  = (z.MOTOCICLET > 0).astype(int)
z['moto_vic'] = (z.CONDMUERTO + z.CONDHERIDO + z.PASAMUERTO + z.PASAHERIDO).where(z.MOTOCICLET > 0, 0)

SAL.parent.mkdir(parents=True, exist_ok=True)
z.to_csv(SAL, index=False, encoding='utf-8-sig')
print(f"\ntotal {len(z)} eventos | muertos {z.TOTMUERTOS.sum()} | heridos {z.TOTHERIDOS.sum()}")
print(z.groupby('CIUDAD')[['TOTMUERTOS','TOTHERIDOS','vru','moto_ev','moto_vic']].sum())
print(f"\nGuardado en: {SAL}")
