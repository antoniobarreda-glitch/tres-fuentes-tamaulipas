"""
Genera resultados_cuatro_corridas.html a partir de la matriz de 05.

COMO CORRER
-----------
  pip install pandas numpy h3 scipy
  python 05_matriz_cuatro_corridas.py      # primero, produce el CSV/JSON
  python gen_matriz_html.py                # despues, arma el HTML
"""
import json
import numpy as np
import pandas as pd

import importlib.util
spec = importlib.util.spec_from_file_location('m5', '05_matriz_cuatro_corridas.py')
m5 = importlib.util.module_from_spec(spec); spec.loader.exec_module(m5)

FOCO = ['TAMPICO', 'REYNOSA']
A, T, F = m5.cargar()

# ---- curvas para las dos ciudades foco, res 9 ----
curvas = {}
for city in FOCO:
    g = m5.grid(A, T, F, city, m5.BB[city], 9)
    d = {}
    for freq, outcome, _ in m5.CORRIDAS:
        c = m5.curva(g, freq, outcome)
        if c is None:
            continue
        x0, obs, opt, pes, opti = c
        idx = np.unique(np.linspace(0, len(x0) - 1, 240).astype(int))
        d[f'{freq}|{outcome}'] = {'x': [round(float(v), 4) for v in x0[idx]],
                                  'obs': [round(float(v), 4) for v in obs[idx]],
                                  'opt': [round(float(v), 4) for v in opt[idx]]}
    curvas[city] = {'n': len(g), 'c': d,
                    'tot_hom': float(g.fis_hom.sum()), 'tot_vru': float(g.atus_vru.sum())}

df = pd.read_csv('matriz_cuatro_corridas.csv')
payload = {'curvas': curvas, 'matriz': df.to_dict('records')}
json.dump(payload, open('matriz_payload.json', 'w'), separators=(',', ':'))

r9 = df[df.res == 9]
CITIES = ['TAMPICO', 'REYNOSA', 'CIUDAD MADERO', 'VICTORIA', 'NUEVO LAREDO', 'MATAMOROS']


def abcv(city, capa, obj, col='abc'):
    s = r9[(r9.ciudad == city) & (r9.capa == capa) & (r9.objetivo == obj)]
    return float(s[col].iloc[0]) if len(s) else float('nan')


def med(capa, obj):
    return float(r9[(r9.capa == capa) & (r9.objetivo == obj)].abc.median())


# ---------- SVG: dumbbell ABC ----------
def dumbbell(obj, titulo):
    W, H = 470, 230
    L, R, TP, B = 108, 46, 26, 34
    pw, ph = W - L - R, H - TP - B
    xs = lambda v: L + pw * min(max(v, 0), 1.2) / 1.2
    step = ph / len(CITIES)
    p = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{titulo}">']
    p.append(f'<text x="0" y="12" class="ct">{titulo}</text>')
    for gv in [0, .25, .5, .75, 1.0]:
        x = xs(gv)
        p.append(f'<line x1="{x:.1f}" y1="{TP}" x2="{x:.1f}" y2="{TP+ph:.1f}" class="grid"/>')
        p.append(f'<text x="{x:.1f}" y="{TP+ph+15:.0f}" class="tick mid">{gv:.2f}</text>')
    x1 = xs(1.0)
    p.append(f'<line x1="{x1:.1f}" y1="{TP}" x2="{x1:.1f}" y2="{TP+ph:.1f}" class="azar"/>')
    for i, c in enumerate(CITIES):
        y = TP + step * (i + .5)
        a, t = abcv(c, 'AXA', obj), abcv(c, 'ATUS', obj)
        p.append(f'<text x="{L-10}" y="{y+4:.1f}" class="tick end{" foco" if c in FOCO else ""}">{c.title()}</text>')
        p.append(f'<line x1="{xs(min(a,t)):.1f}" y1="{y:.1f}" x2="{xs(max(a,t)):.1f}" y2="{y:.1f}" class="conn"/>')
        for v, cl, nm in [(a, 's1', 'AXA'), (t, 's2', 'ATUS')]:
            p.append(f'<circle cx="{xs(v):.1f}" cy="{y:.1f}" r="5.5" class="dot {cl}">'
                     f'<title>{c.title()} — {nm}: ABC {v:.3f}</title></circle>')
    p.append(f'<text x="{x1:.1f}" y="{TP-6}" class="tick mid" text-anchor="middle">azar = 1.00</text>')
    p.append('</svg>')
    return ''.join(p)


# ---------- SVG: curvas de cobertura ----------
def curvas_svg(city, obj, titulo):
    W, H = 470, 300
    L, R, TP, B = 46, 16, 26, 40
    pw, ph = W - L - R, H - TP - B
    X = lambda v: L + pw * v
    Y = lambda v: TP + ph * (1 - v)
    d = curvas[city]['c']
    p = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{titulo}" class="cv" data-city="{city}" data-obj="{obj}">']
    p.append(f'<text x="0" y="12" class="ct">{titulo}</text>')
    p.append(f'<rect x="{X(.05):.1f}" y="{TP}" width="{X(.20)-X(.05):.1f}" height="{ph}" class="band"/>')
    p.append(f'<text x="{X(.125):.1f}" y="{TP+ph-6:.1f}" class="tick mid" text-anchor="middle">5–20%</text>')
    for gv in [0, .25, .5, .75, 1]:
        p.append(f'<line x1="{L}" y1="{Y(gv):.1f}" x2="{L+pw}" y2="{Y(gv):.1f}" class="grid"/>')
        p.append(f'<text x="{L-7}" y="{Y(gv)+4:.1f}" class="tick end">{int(gv*100)}%</text>')
        p.append(f'<text x="{X(gv):.1f}" y="{TP+ph+16:.0f}" class="tick mid">{int(gv*100)}%</text>')
    p.append(f'<line x1="{L}" y1="{Y(0):.1f}" x2="{L+pw}" y2="{Y(1):.1f}" class="azar"/>')
    k_axa, k_atus = f'AXA|{obj}', f'ATUS|{obj}'
    s = d[k_axa]
    p.append('<polyline points="' + ' '.join(f'{X(x):.1f},{Y(y):.1f}' for x, y in zip(s['x'], s['opt'])) + '" class="ln opt"/>')
    for k, cls in [(k_axa, 's1'), (k_atus, 's2')]:
        s = d[k]
        p.append('<polyline points="' + ' '.join(f'{X(x):.1f},{Y(y):.1f}' for x, y in zip(s['x'], s['obs'])) + f'" class="ln {cls}"/>')
    p.append(f'<text x="{L+pw/2:.1f}" y="{TP+ph+33}" class="tick mid">% de celdas intervenidas (presupuesto)</text>')
    p.append('</svg>')
    return ''.join(p)


def tabla(obj):
    h = ['<table><thead><tr><th>Ciudad</th><th>ABC AXA</th><th>ABC ATUS</th>'
         '<th>Cob. 10% AXA</th><th>Cob. 10% ATUS</th><th>Techo 10%</th><th>Empates</th></tr></thead><tbody>']
    for c in CITIES:
        ra = r9[(r9.ciudad == c) & (r9.capa == 'AXA') & (r9.objetivo == obj)].iloc[0]
        rt = r9[(r9.ciudad == c) & (r9.capa == 'ATUS') & (r9.objetivo == obj)].iloc[0]
        fo = ' class="foco"' if c in FOCO else ''
        h.append(f'<tr{fo}><td>{c.title()}</td><td>{ra.abc:.3f}</td><td>{rt.abc:.3f}</td>'
                 f'<td>{ra.cob_10:.1f}%</td><td>{rt.cob_10:.1f}%</td><td>{ra.techo_10:.1f}%</td>'
                 f'<td class="mut">{ra.empates:.0%}</td></tr>')
    h.append(f'<tr class="tot"><td>Mediana</td><td>{med("AXA",obj):.3f}</td><td>{med("ATUS",obj):.3f}</td>'
             f'<td colspan="4"></td></tr></tbody></table>')
    return ''.join(h)


tpl = open('matriz_tpl.html').read()
out = (tpl.replace('__DUMB_HOM__', dumbbell('fis_hom', 'Objetivo: muertes (homicidios culposos, Fiscalía)'))
          .replace('__DUMB_VRU__', dumbbell('atus_vru', 'Objetivo: víctimas peatón + ciclista (ATUS)'))
          .replace('__CV_TAM__', curvas_svg('TAMPICO', 'fis_hom', 'Tampico — objetivo muertes'))
          .replace('__CV_REY__', curvas_svg('REYNOSA', 'fis_hom', 'Reynosa — objetivo muertes'))
          .replace('__TBL_HOM__', tabla('fis_hom'))
          .replace('__TBL_VRU__', tabla('atus_vru'))
          .replace('__MED_AXA_HOM__', f'{med("AXA","fis_hom"):.3f}')
          .replace('__MED_ATUS_HOM__', f'{med("ATUS","fis_hom"):.3f}')
          .replace('__MED_AXA_VRU__', f'{med("AXA","atus_vru"):.3f}')
          .replace('__MED_ATUS_VRU__', f'{med("ATUS","atus_vru"):.3f}'))
open('resultados_cuatro_corridas.html', 'w').write(out)
print('OK -> resultados_cuatro_corridas.html')
