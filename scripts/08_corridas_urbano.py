"""
08 — Las cuatro corridas, recalculadas sobre el POLIGONO URBANO (AGEB), no el rectangulo.

Sustituye a 05_matriz_cuatro_corridas.py. La unica diferencia es el recorte:
antes cada ciudad era un rectangulo de coordenadas dibujado a mano, ahora es la
mancha urbana de INEGI (AGEB 2020 disueltas, holgura 150 m), y los registros que
caen fuera no se tiran: quedan en el estrato PERIURBANO y se reportan aparte.

Todo lo demas es identico, incluida la regla de desempate por esperanza.

COMO CORRER
-----------
1) Instalar dependencias (una sola vez):
       pip install pandas numpy h3 scipy
   En Windows/PowerShell, si 'pip' no responde:  python -m pip install pandas numpy h3 scipy

2) Necesita que ya se haya corrido 07_poligono_urbano.py, que produce
       estratos_axa.csv  estratos_atus.csv  estratos_fiscalia.csv

3) Correrlo:
   - VS Code: abrir el archivo y presionar F5 (o Run Python File).
   - Terminal / PowerShell:  python 08_corridas_urbano.py

4) Salidas:
       matriz_urbano.csv        una fila por ciudad x resolucion x corrida
       periurbano_resumen.csv   el estrato que queda fuera del poligono
       curvas_urbano.json       curvas de cobertura para las figuras
"""
import json
import numpy as np
import pandas as pd
import h3
from scipy.stats import spearmanr

BUDGETS = [0.05, 0.10, 0.15, 0.20]
RES = [9, 10]
CORRIDAS = [('AXA', 'fis_hom', 'AXA-frecuencia -> homicidios Fiscalia'),
            ('ATUS', 'fis_hom', 'ATUS-frecuencia -> homicidios Fiscalia'),
            ('AXA', 'atus_vru', 'AXA-frecuencia -> victimas VRU (ATUS)'),
            ('ATUS', 'atus_vru', 'ATUS-frecuencia -> victimas VRU (ATUS) [CIRCULAR]')]
FOCO = ['TAMPICO', 'REYNOSA']
trapz = getattr(np, 'trapezoid', None) or np.trapz


def cargar():
    A = pd.read_csv('estratos_axa.csv', low_memory=False)
    T = pd.read_csv('estratos_atus.csv', low_memory=False)
    F = pd.read_csv('estratos_fiscalia.csv', low_memory=False)
    for c in ['PEATMUERTO', 'PEATHERIDO', 'CICLMUERTO', 'CICLHERIDO', 'TOTMUERTOS']:
        T[c] = pd.to_numeric(T[c], errors='coerce').fillna(0)
    T['vru_vict'] = T.PEATMUERTO + T.PEATHERIDO + T.CICLMUERTO + T.CICLHERIDO
    F['hom'] = F.DELITO.astype(str).str.upper().str.startswith('HOMICIDIO')
    return A, T, F


def grid(A, T, F, city, res, urbano=True):
    a = A[(A.ciudad_std == city) & (A.urbano == urbano)]
    t = T[(T.ciudad_std == city) & (T.urbano == urbano)]
    f = F[(F.ciudad_std == city) & (F.urbano == urbano)]
    cell = lambda la, lo: h3.latlng_to_cell(la, lo, res)
    ka = [cell(x, y) for x, y in zip(a.lat, a.lon)]
    kt = [cell(x, y) for x, y in zip(t.LATITUD, t.LONGITUD)]
    kf = [cell(x, y) for x, y in zip(f.lat, f.lon)]
    g = pd.DataFrame({'AXA': pd.Series(ka).value_counts()}).join(
        pd.DataFrame({'ATUS': pd.Series(kt).value_counts()}), how='outer').join(
        pd.DataFrame({'fis_hom': pd.Series([k for k, h in zip(kf, f.hom) if h]).value_counts()}),
        how='outer').join(
        pd.DataFrame({'atus_vru': t.assign(k=kt).groupby('k').vru_vict.sum()}), how='outer')
    return g.fillna(0)


def curva(g, freq, outcome):
    """Esperanza bajo desempate aleatorio — ver nota larga en 05."""
    tot = g[outcome].sum()
    if tot <= 0:
        return None
    n = len(g)
    d = g.sort_values(freq, ascending=False)
    fv, ov = d[freq].values, d[outcome].values
    esp = np.empty(n); pes = np.empty(n); opti = np.empty(n)
    acc = 0.0; i = 0
    while i < n:
        j = i
        while j < n and fv[j] == fv[i]:
            j += 1
        m = j - i; blq = ov[i:j]; S = blq.sum(); k = np.arange(1, m + 1)
        esp[i:j] = acc + S * k / m
        pes[i:j] = acc + np.cumsum(np.sort(blq))
        opti[i:j] = acc + np.cumsum(np.sort(blq)[::-1])
        acc += S; i = j
    opt = np.cumsum(np.sort(ov)[::-1])
    z = lambda v: np.concatenate([[0], v / tot])
    x0 = np.concatenate([[0], np.arange(1, n + 1) / n])
    return x0, z(esp), z(opt), z(pes), z(opti)


def abc(x0, obs, opt):
    num = trapz(opt - obs, x0); den = trapz(opt - x0, x0)
    return float(num / den) if den > 0 else np.nan


def main():
    A, T, F = cargar()
    CITIES = sorted(A.ciudad_std.unique())
    filas, curvas = [], {}

    for res in RES:
        for city in CITIES:
            g = grid(A, T, F, city, res)
            for freq, outcome, etiq in CORRIDAS:
                c = curva(g, freq, outcome)
                if c is None:
                    continue
                x0, obs, opt, pes, opti = c
                n = len(g)
                fila = {'ciudad': city, 'res': res, 'capa': freq, 'objetivo': outcome,
                        'corrida': etiq, 'celdas': n,
                        'total_objetivo': float(g[outcome].sum()),
                        'empates': round(1 - g[freq].nunique() / n, 3),
                        'abc': round(abc(x0, obs, opt), 4),
                        'abc_pes': round(abc(x0, pes, opt), 4),
                        'abc_opt': round(abc(x0, opti, opt), 4)}
                for b in BUDGETS:
                    k = max(1, int(round(b * n)))
                    fila[f'cob_{int(b*100)}'] = round(100 * obs[k], 1)
                    fila[f'techo_{int(b*100)}'] = round(100 * opt[k], 1)
                m = (g[freq] > 0) | (g[outcome] > 0)
                if m.sum() > 5:
                    rho, p = spearmanr(g.loc[m, freq], g.loc[m, outcome])
                    fila['rho'] = round(float(rho), 3); fila['p'] = float(p)
                filas.append(fila)
                if res == 9 and city in FOCO:
                    idx = np.unique(np.linspace(0, len(x0) - 1, 240).astype(int))
                    curvas.setdefault(city, {})[f'{freq}|{outcome}'] = {
                        'x': [round(float(v), 4) for v in x0[idx]],
                        'obs': [round(float(v), 4) for v in obs[idx]],
                        'opt': [round(float(v), 4) for v in opt[idx]]}

    d = pd.DataFrame(filas)
    d.to_csv('matriz_urbano.csv', index=False)
    json.dump(curvas, open('curvas_urbano.json', 'w'), separators=(',', ':'))

    # --- estrato periurbano ---
    per = []
    for city in CITIES:
        a = A[(A.ciudad_std == city) & (~A.urbano)]
        t = T[(T.ciudad_std == city) & (~T.urbano)]
        f = F[(F.ciudad_std == city) & (~F.urbano) & F.hom]
        per.append({'ciudad': city, 'AXA': len(a), 'ATUS_eventos': len(t),
                    'ATUS_muertes': int(t.TOTMUERTOS.sum()), 'FIS_homicidios': len(f)})
    P = pd.DataFrame(per)
    P.loc[len(P)] = ['TOTAL', P.AXA.sum(), P.ATUS_eventos.sum(),
                     P.ATUS_muertes.sum(), P.FIS_homicidios.sum()]
    P.to_csv('periurbano_resumen.csv', index=False)

    r9 = d[d.res == 9]
    print('=== ABC, res 9, estrato URBANO (AGEB) ===')
    for obj, lab in [('fis_hom', 'objetivo muertes'), ('atus_vru', 'objetivo VRU')]:
        s = r9[r9.objetivo == obj].pivot(index='ciudad', columns='capa', values='abc')
        print(f'\n--- {lab} ---'); print(s.to_string())
        print(f'  MEDIANA  AXA {s.AXA.median():.3f}   ATUS {s.ATUS.median():.3f}')
    print('\n=== ESTRATO PERIURBANO ===')
    print(P.to_string(index=False))
    print('\nOK -> matriz_urbano.csv / periurbano_resumen.csv / curvas_urbano.json')


if __name__ == '__main__':
    main()
