"""
06 — Validacion de los conteos de fiscalia contra mortalidad INEGI (EDR).

QUE HACE
--------
Las fiscalias de Tamaulipas y Nuevo Leon dicen cuantas carpetas por homicidio
culposo en hechos de transito abrieron. Este script cuenta, en una cadena
institucional COMPLETAMENTE distinta (acta de defuncion -> registro civil ->
INEGI), cuantas muertes por accidente de transporte ocurrieron en los mismos
municipios y los mismos anios. Si los numeros se parecen, la capa de fiscalia
queda validada; si no, la diferencia es en si misma un resultado.

DOS CAUTELAS QUE NO SE PUEDEN SALTAR
------------------------------------
1. mun_ocurr del EDR es donde ocurrio LA MUERTE, que muchas veces es el hospital
   y no el lugar del choque. Por eso el contraste se hace por GRUPO METROPOLITANO
   (Tampico+Madero juntos; los seis de Nuevo Leon juntos) y solo municipio por
   municipio en las cuatro ciudades aisladas.
2. Una muerte de 2023 puede registrarse en 2024. Por eso se agrupan los archivos
   2019-2024 y se filtra por anio de OCURRENCIA, no de registro.

COMO CORRER
-----------
1) Instalar dependencias (una sola vez), en la terminal:
       pip install pandas numpy
   En Windows/PowerShell, si 'pip' no responde:  python -m pip install pandas numpy

2) Descomprimir cada zip del EDR en una subcarpeta con el nombre del anio:
       edr/2019/  edr/2020/  edr/2021/  edr/2022/  edr/2023/  edr/2024/
   Dentro de cada una debe quedar la carpeta conjunto_de_datos/ tal cual viene.

3) Correrlo desde la carpeta que contiene edr/ :
   - VS Code: abrir el archivo y presionar F5 (o el boton Run Python File).
   - Terminal / PowerShell:
         python 06_validacion_inegi.py
   Tarda unos minutos: son ~1.3 GB de CSV leidos por bloques.

4) Salidas en la misma carpeta:
       validacion_inegi_fiscalia.csv     tabla de contraste
       inegi_muertes_transporte.csv      el detalle anual por municipio
"""
import glob
import os
import pandas as pd

ANIOS_ARCHIVO = [2019, 2020, 2021, 2022, 2023, 2024]   # archivos a leer
ANIOS_OCURR = [2019, 2020, 2021, 2022, 2023]           # anios de interes

MUN = {  # clave INEGI verificada contra el catalogo entidad_municipio_localidad
    ('28', '038'): 'TAMPICO',      ('28', '009'): 'CIUDAD MADERO',
    ('28', '032'): 'REYNOSA',      ('28', '041'): 'VICTORIA',
    ('28', '027'): 'NUEVO LAREDO', ('28', '022'): 'MATAMOROS',
    ('19', '039'): 'MONTERREY',    ('19', '046'): 'SAN NICOLAS',
    ('19', '006'): 'APODACA',      ('19', '021'): 'ESCOBEDO',
    ('19', '048'): 'SANTA CATARINA', ('19', '018'): 'GARCIA',
    ('19', '026'): 'GUADALUPE',    ('19', '019'): 'SAN PEDRO',  # aun no solicitados
}
GRUPOS = {
    'Zona metropolitana Tampico (Tampico + Cd. Madero)': ['TAMPICO', 'CIUDAD MADERO'],
    'Reynosa': ['REYNOSA'], 'Victoria': ['VICTORIA'],
    'Nuevo Laredo': ['NUEVO LAREDO'], 'Matamoros': ['MATAMOROS'],
    'Zona metropolitana Monterrey (6 municipios solicitados)':
        ['MONTERREY', 'SAN NICOLAS', 'APODACA', 'ESCOBEDO', 'SANTA CATARINA', 'GARCIA'],
}
# carpetas por homicidio culposo en hechos de transito, 2019-2023 (respuestas de transparencia)
FISCALIA = {'Zona metropolitana Tampico (Tampico + Cd. Madero)': None,  # se llena abajo
            'Zona metropolitana Monterrey (6 municipios solicitados)': 1228}


def localiza(anio):
    pat = f'edr/{anio}/conjunto_de_datos/*.[cC][sS][vV]'
    c = [f for f in glob.glob(pat) if os.path.getsize(f) > 50_000_000]
    if not c:
        raise FileNotFoundError(f'No encontre el CSV grande de {anio} en edr/{anio}/conjunto_de_datos/')
    return c[0]


def lee(anio):
    f = localiza(anio)
    out = []
    for ch in pd.read_csv(f, dtype=str, chunksize=400_000, low_memory=False,
                          encoding='latin-1', on_bad_lines='skip'):
        ch.columns = [c.strip().lower() for c in ch.columns]
        ch = ch[['ent_ocurr', 'mun_ocurr', 'anio_ocur', 'causa_def', 'sexo']].copy()
        # TRAMPA: en el archivo de 2019 las claves traen un TABULADOR pegado
        # ('28\t'), asi que sin este strip ese anio devuelve cero filas en silencio.
        for c in ['ent_ocurr', 'mun_ocurr', 'anio_ocur', 'causa_def', 'sexo']:
            ch[c] = ch[c].astype(str).str.strip()
        ch = ch[ch.ent_ocurr.isin(['28', '19'])]
        ch = ch[ch.causa_def.str.match(r'^V([0-7]\d|8[0-9])', na=False)]
        out.append(ch)
    d = pd.concat(out) if out else pd.DataFrame()
    print(f'  {anio}: {len(d):,} defunciones V01-V89 en ENT 28/19')
    return d


def main():
    print('Leyendo archivos EDR (esto tarda unos minutos)...')
    D = pd.concat([lee(a) for a in ANIOS_ARCHIVO])
    D['mun_ocurr'] = D.mun_ocurr.str.zfill(3)
    D['ciudad'] = [MUN.get((e, m)) for e, m in zip(D.ent_ocurr, D.mun_ocurr)]
    D = D[D.ciudad.notna()]
    D['anio'] = pd.to_numeric(D.anio_ocur, errors='coerce')
    D = D[D.anio.isin(ANIOS_OCURR)]
    D['v0179'] = D.causa_def.str.match(r'^V[0-7]\d', na=False)
    D['grupo_cod'] = D.causa_def.str[:3]

    det = (D.groupby(['ciudad', 'anio'])
             .agg(V01_V89=('causa_def', 'size'), V01_V79=('v0179', 'sum'))
             .reset_index())
    det.to_csv('inegi_muertes_transporte.csv', index=False)

    filas = []
    for g, ciudades in GRUPOS.items():
        s = D[D.ciudad.isin(ciudades)]
        filas.append({'grupo': g, 'municipios': len(ciudades),
                      'INEGI_V01_V89': len(s), 'INEGI_V01_V79': int(s.v0179.sum())})
    T = pd.DataFrame(filas)
    T.to_csv('validacion_inegi_fiscalia.csv', index=False)

    print('\n=== MUERTES POR ACCIDENTE DE TRANSPORTE, INEGI EDR, 2019-2023 ===')
    print(T.to_string(index=False))
    print('\n=== DETALLE ANUAL ===')
    print(det.pivot(index='ciudad', columns='anio', values='V01_V89').fillna(0).astype(int).to_string())
    print('\n=== CODIGOS MAS USADOS (revisa si domina V89 = tipo no especificado) ===')
    for ent, nom in [('28', 'Tamaulipas'), ('19', 'Nuevo Leon')]:
        t = D[D.ent_ocurr == ent].grupo_cod.value_counts().head(6)
        print(f'  {nom}: ' + ', '.join(f'{k} {v}' for k, v in t.items()))
    extra = D[D.ciudad.isin(['GUADALUPE', 'SAN PEDRO'])]
    if len(extra):
        print('\nMunicipios aun NO solicitados a la Fiscalia de Nuevo Leon '
              '(para dimensionar la solicitud complementaria):')
        print(extra.groupby('ciudad').size().to_string())
    print('\nOK -> validacion_inegi_fiscalia.csv / inegi_muertes_transporte.csv')


if __name__ == '__main__':
    main()
