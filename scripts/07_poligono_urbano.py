"""
07 — Sustituye el rectangulo por el poligono urbano de INEGI (AGEB urbanas).

QUE HACE
--------
Construye, para cada ciudad, el poligono de su mancha urbana disolviendo las
AGEB urbanas del Marco Geoestadistico 2020, y clasifica cada registro de las
tres fuentes en dos estratos:

  URBANO      dentro del poligono de AGEB de ese municipio
  PERIURBANO  el municipio lo reporta, pero cae fuera del poligono

Despues compara ese recorte contra el rectangulo que se venia usando, para
saber cuanto cambia y si el cambio afecta parejo a las tres fuentes.

COMO CORRER
-----------
1) Instalar dependencias (una sola vez):
       pip install geopandas shapely pandas
   En Windows/PowerShell, si 'pip' no responde:  python -m pip install geopandas shapely pandas
   (geopandas jala GDAL solo; si truena en Windows, la via facil es
    conda install -c conda-forge geopandas)

2) Necesita:
       mg/28a.shp  mg/19a.shp   (+ sus .dbf .shx .prj, salen de extraer_ageb.ps1)
       entrega/datos/*.csv      (las tres bases limpias)

3) Correrlo desde la carpeta que contiene mg/ y entrega/ :
   - VS Code: abrir el archivo y presionar F5 (o Run Python File).
   - Terminal / PowerShell:
         python 07_poligono_urbano.py

4) Salidas:
       poligonos_urbanos.gpkg        el poligono por ciudad, para QGIS
       comparacion_recortes.csv      rectangulo vs AGEB, por ciudad y fuente
       estratos_<fuente>.csv         cada registro con su estrato asignado
"""
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

# CVE_MUN de INEGI (verificadas contra el catalogo entidad_municipio_localidad)
CIU = {'TAMPICO': ('28', '038'), 'CIUDAD MADERO': ('28', '009'),
       'REYNOSA': ('28', '032'), 'VICTORIA': ('28', '041'),
       'NUEVO LAREDO': ('28', '027'), 'MATAMOROS': ('28', '022')}

BB = {'TAMPICO': (22.15, 22.35, -98.00, -97.75), 'CIUDAD MADERO': (22.20, 22.35, -97.95, -97.75),
      'REYNOSA': (25.95, 26.20, -98.45, -98.20), 'VICTORIA': (23.65, 23.83, -99.25, -98.98),
      'NUEVO LAREDO': (27.40, 27.62, -99.62, -99.42), 'MATAMOROS': (25.75, 25.95, -97.60, -97.40)}

# holgura alrededor de la AGEB, en metros. Las AGEB terminan en el eje de la
# vialidad perimetral, asi que un choque sobre esa vialidad puede caer justo
# afuera. 150 m cubre el ancho de una avenida y su camellon sin meter carretera.
HOLGURA_M = 150


def poligonos():
    g = gpd.read_file('mg/28a.shp')
    g = g[g.CVE_MUN.isin([m for _, m in CIU.values()])]
    g = g.to_crs('EPSG:6372')                      # metros, Mexico ITRF2008 LCC
    out = {}
    for ciudad, (ent, mun) in CIU.items():
        s = g[g.CVE_MUN == mun]
        if len(s) == 0:
            print(f'  AVISO: sin AGEB para {ciudad}')
            continue
        poly = s.geometry.union_all().buffer(HOLGURA_M)
        out[ciudad] = poly
        print(f'  {ciudad:14s} {len(s):4d} AGEB  {poly.area/1e6:7.1f} km2')
    return out, g.crs


def carga():
    A = pd.read_csv('entrega/datos/axa_tamaulipas_6c_2019_2023.csv', encoding='utf-8-sig')
    A = A.dropna(subset=['lat', 'lon']); A = A[(A.lat.abs() > 1) & (A.lon.abs() > 1)]
    T = pd.read_csv('entrega/datos/atus_tamaulipas_6c_2019_2023.csv', encoding='utf-8-sig',
                    low_memory=False).dropna(subset=['LATITUD', 'LONGITUD'])
    F = pd.read_csv('entrega/datos/fiscalia_tamaulipas_limpio.csv', encoding='utf-8-sig')
    F = F[(F.geo_ok == True) & (F['AÑO'].between(2019, 2023))].dropna(subset=['lat', 'lon'])
    return (('AXA', A, 'CIUDAD', 'lat', 'lon'),
            ('ATUS', T, 'CIUDAD', 'LATITUD', 'LONGITUD'),
            ('Fiscalia', F, 'MUNICIPIO_HECHO', 'lat', 'lon'))


def main():
    print('Construyendo poligonos urbanos (AGEB 2020 disueltas, holgura '
          f'{HOLGURA_M} m):')
    polys, crs = poligonos()
    gpd.GeoDataFrame({'ciudad': list(polys)}, geometry=list(polys.values()),
                     crs=crs).to_file('poligonos_urbanos.gpkg', driver='GPKG')

    filas = []
    for nombre, df, colciu, la, lo in carga():
        marcado = []
        for ciudad, poly in polys.items():
            d = df[df[colciu] == ciudad].copy()
            if len(d) == 0:
                continue
            pts = gpd.GeoSeries([Point(x, y) for x, y in zip(d[lo], d[la])],
                                crs='EPSG:4326').to_crs(crs)
            d['urbano'] = pts.within(poly).values
            s, n, w, e = BB[ciudad]
            d['en_rect'] = ((d[la] >= s) & (d[la] <= n) & (d[lo] >= w) & (d[lo] <= e)).values
            d['ciudad_std'] = ciudad
            marcado.append(d)
            filas.append({'fuente': nombre, 'ciudad': ciudad, 'total_municipio': len(d),
                          'urbano_AGEB': int(d.urbano.sum()),
                          'periurbano': int((~d.urbano).sum()),
                          'en_rectangulo': int(d.en_rect.sum()),
                          'pct_fuera_AGEB': round(100 * (~d.urbano).mean(), 1),
                          'pct_fuera_rect': round(100 * (~d.en_rect).mean(), 1)})
        pd.concat(marcado).to_csv(f'estratos_{nombre.lower()}.csv', index=False)

    C = pd.DataFrame(filas)
    C.to_csv('comparacion_recortes.csv', index=False)
    print('\n=== QUE DEJA FUERA CADA RECORTE (% de los registros del municipio) ===')
    piv = C.pivot(index='ciudad', columns='fuente',
                  values=['pct_fuera_AGEB', 'pct_fuera_rect'])
    print(piv.to_string())
    print('\n=== CONTEOS DENTRO DEL POLIGONO URBANO ===')
    print(C.pivot(index='ciudad', columns='fuente', values='urbano_AGEB').to_string())
    print('\nOK -> poligonos_urbanos.gpkg / comparacion_recortes.csv / estratos_*.csv')


if __name__ == '__main__':
    main()
