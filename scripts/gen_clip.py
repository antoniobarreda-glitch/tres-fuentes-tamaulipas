"""
Genera clip_data.json: puntos crudos de las tres fuentes + hexagonos res 9
+ el rectangulo (bounding box) usado hoy para recortar cada ciudad.
Sirve para revisar A OJO si el recorte mete carretera o corta borde urbano.

COMO CORRER:
  pip install pandas numpy h3
  python gen_clip.py
"""
import json, pandas as pd, numpy as np, h3

BB = {'TAMPICO':(22.15,22.35,-98.00,-97.75), 'CIUDAD MADERO':(22.20,22.35,-97.95,-97.75),
      'REYNOSA':(25.95,26.20,-98.45,-98.20), 'VICTORIA':(23.65,23.83,-99.25,-98.98),
      'NUEVO LAREDO':(27.40,27.62,-99.62,-99.42), 'MATAMOROS':(25.75,25.95,-97.60,-97.40)}

A0 = pd.read_csv('entrega/datos/axa_tamaulipas_6c_2019_2023.csv', encoding='utf-8-sig')
T0 = pd.read_csv('entrega/datos/atus_tamaulipas_6c_2019_2023.csv', encoding='utf-8-sig', low_memory=False)
F0 = pd.read_csv('entrega/datos/fiscalia_tamaulipas_limpio.csv', encoding='utf-8-sig')
F0 = F0[(F0.geo_ok == True) & (F0['AÑO'].between(2019, 2023))]

print('URBANA valores:', T0.URBANA.value_counts().to_dict())

def inside(lat, lon, bb):
    s, n, w, e = bb
    return (lat >= s) & (lat <= n) & (lon >= w) & (lon <= e)

def pack(df, latc, lonc, bb, extra=None, cap=14000):
    d = df[[latc, lonc] + (extra or [])].dropna(subset=[latc, lonc]).copy()
    # margen de +-0.10 grados alrededor del rectangulo: lo de afuera es lo que hoy se descarta
    s, n, w, e = bb
    m = 0.10
    d = d[(d[latc] > s - m) & (d[latc] < n + m) & (d[lonc] > w - m) & (d[lonc] < e + m)]
    d['_in'] = inside(d[latc], d[lonc], bb).astype(int)
    if len(d) > cap:
        # nunca submuestrear lo de AFUERA: es justo lo que se quiere ver
        out = d[d._in == 0]
        ins = d[d._in == 1]
        k = max(cap - len(out), 500)
        if len(ins) > k:
            ins = ins.sample(k, random_state=7)
        d = pd.concat([ins, out])
    rows = []
    for _, r in d.iterrows():
        row = [round(float(r[latc]), 5), round(float(r[lonc]), 5), int(r['_in'])]
        for c in (extra or []):
            v = r[c]
            row.append(int(v) if pd.notna(v) else 0)
        rows.append(row)
    return rows, int(d['_in'].sum()), int((1 - d['_in']).sum())

out = {}
for city, bb in BB.items():
    s, n, w, e = bb
    A = A0[A0.CIUDAD == city]
    T = T0[T0.CIUDAD == city].copy()
    F = F0[F0.MUNICIPIO_HECHO == city]
    # marca ATUS: 1 = el registro NO es urbano (suburbano o con carretera nombrada)
    T['nourb'] = ((T.URBANA != 1) | (T.CARRETERA.notna())).astype(int)
    T['esmoto'] = T.moto_ev.fillna(0).astype(int)
    T['esksi'] = T.ksi.fillna(0).astype(int)

    pa, ain, aout = pack(A, 'lat', 'lon', bb)
    pt, tin, tout = pack(T, 'LATITUD', 'LONGITUD', bb, extra=['nourb', 'esksi', 'esmoto'])
    pf, fin, fout = pack(F, 'lat', 'lon', bb)

    key = city.lower().replace(' ', '_')
    ret = pd.read_csv(f'entrega/datos/reticula_{key}_res9.csv', index_col=0)
    hexes = []
    for hid, r in ret.iterrows():
        try:
            bnd = h3.cell_to_boundary(hid)
        except Exception:
            continue
        hexes.append([[[round(la, 5), round(lo, 5)] for la, lo in bnd],
                      int(r.axa), int(r.fis_hom), int(r.atus_ksi)])

    # conteos REALES (sin margen): cuantos registros del municipio caen dentro del rectangulo
    Ag = A.dropna(subset=['lat', 'lon']); Tg = T.dropna(subset=['LATITUD', 'LONGITUD'])
    Fg = F.dropna(subset=['lat', 'lon'])
    Tmask = inside(Tg.LATITUD, Tg.LONGITUD, bb)
    out[city] = {'bbox': [s, n, w, e], 'hex': hexes,
                 'axa': pa, 'atus': pt, 'fis': pf,
                 'n': {'axa_in': ain, 'axa_out': aout, 'atus_in': tin, 'atus_out': tout,
                       'fis_in': fin, 'fis_out': fout,
                       'axa_in_full': int(inside(Ag.lat, Ag.lon, bb).sum()),
                       'atus_in_full': int(Tmask.sum()),
                       'fis_in_full': int(inside(Fg.lat, Fg.lon, bb).sum()),
                       'atus_nourb_in': int(Tg[Tmask].nourb.sum()),
                       'atus_tot': int(len(Tg)), 'axa_tot': int(len(Ag)), 'fis_tot': int(len(Fg))}}
    print(f'{city:16s} AXA {ain:6d} dentro / {aout:5d} fuera | ATUS {tin:6d}/{tout:5d} '
          f'| FIS {fin:5d}/{fout:4d} | hex {len(hexes)}')

json.dump(out, open('clip_data.json', 'w'), separators=(',', ':'))
print('OK -> clip_data.json')
