"""
05 — Matriz de cuatro corridas.
Cruza dos CAPAS AUDITADAS (la que un municipio usaria para priorizar) contra
dos OBJETIVOS DE POLITICA (lo que se quiere evitar):

  1. AXA-frecuencia   -> homicidios Fiscalia   (la corrida original)
  2. ATUS-frecuencia  -> homicidios Fiscalia   (el registro oficial, auditado igual)
  3. AXA-frecuencia   -> victimas VRU de ATUS  (objetivo peaton + ciclista)
  4. ATUS-frecuencia  -> victimas VRU de ATUS  (CIRCULAR: mismo registro contra si mismo,
                                                se reporta como referencia superior)

Para cada corrida y cada ciudad calcula:
  - cobertura observada y techo alcanzable con 5/10/15/20% de las celdas
  - ABC: area entre la curva observada y la optima, normalizada por el area
         hasta la diagonal aleatoria. 0 = iguala al optimo, 1 = da lo mismo que el azar
  - Spearman entre la capa auditada y el objetivo (solo celdas con algun evento)

COMO CORRER
-----------
1) Instalar dependencias (una sola vez), en la terminal:
       pip install pandas numpy h3 scipy
   En Windows/PowerShell, si 'pip' no responde:  python -m pip install pandas numpy h3 scipy

2) Colocar este archivo junto a la carpeta  entrega\\datos\\  (las tres bases limpias).

3) Correrlo:
   - VS Code: abrir el archivo y presionar F5 (o el boton Run Python File).
   - Terminal / PowerShell, parado en la carpeta del script:
         python 05_matriz_cuatro_corridas.py

4) Salidas en la misma carpeta:
       matriz_cuatro_corridas.csv   (una fila por ciudad x resolucion x corrida)
       matriz_cuatro_corridas.json  (lo mismo, para armar el HTML)
"""
import json
import numpy as np
import pandas as pd
import h3
from scipy.stats import spearmanr

BB = {'TAMPICO': (22.15, 22.35, -98.00, -97.75), 'CIUDAD MADERO': (22.20, 22.35, -97.95, -97.75),
      'REYNOSA': (25.95, 26.20, -98.45, -98.20), 'VICTORIA': (23.65, 23.83, -99.25, -98.98),
      'NUEVO LAREDO': (27.40, 27.62, -99.62, -99.42), 'MATAMOROS': (25.75, 25.95, -97.60, -97.40)}

BUDGETS = [0.05, 0.10, 0.15, 0.20]
RES = [9, 10]

CORRIDAS = [('AXA',  'fis_hom',  'AXA-frecuencia -> homicidios Fiscalia'),
            ('ATUS', 'fis_hom',  'ATUS-frecuencia -> homicidios Fiscalia'),
            ('AXA',  'atus_vru', 'AXA-frecuencia -> victimas VRU (ATUS)'),
            ('ATUS', 'atus_vru', 'ATUS-frecuencia -> victimas VRU (ATUS) [CIRCULAR]')]

trapz = getattr(np, 'trapezoid', None) or np.trapz


def cargar():
    A = pd.read_csv('entrega/datos/axa_tamaulipas_6c_2019_2023.csv', encoding='utf-8-sig')
    A = A.dropna(subset=['lat', 'lon'])
    A = A[(A.lat.abs() > 1) & (A.lon.abs() > 1)]
    T = pd.read_csv('entrega/datos/atus_tamaulipas_6c_2019_2023.csv',
                    encoding='utf-8-sig', low_memory=False).dropna(subset=['LATITUD', 'LONGITUD'])
    F = pd.read_csv('entrega/datos/fiscalia_tamaulipas_limpio.csv', encoding='utf-8-sig')
    F = F[(F.geo_ok == True) & (F['AÑO'].between(2019, 2023))].dropna(subset=['lat', 'lon'])
    # victimas VRU de ATUS: peatones y ciclistas muertos o heridos en el hecho
    for c in ['PEATMUERTO', 'PEATHERIDO', 'CICLMUERTO', 'CICLHERIDO']:
        T[c] = pd.to_numeric(T[c], errors='coerce').fillna(0)
    T['vru_vict'] = T.PEATMUERTO + T.PEATHERIDO + T.CICLMUERTO + T.CICLHERIDO
    return A, T, F


def recorta(d, la, lo, bb):
    s, n, w, e = bb
    return d[(d[la] >= s) & (d[la] <= n) & (d[lo] >= w) & (d[lo] <= e)]


def grid(A, T, F, city, bb, res):
    a = recorta(A[A.CIUDAD == city], 'lat', 'lon', bb)
    t = recorta(T[T.CIUDAD == city], 'LATITUD', 'LONGITUD', bb)
    f = recorta(F[F.MUNICIPIO_HECHO == city], 'lat', 'lon', bb)
    cell = lambda la, lo: h3.latlng_to_cell(la, lo, res)
    ka = [cell(x, y) for x, y in zip(a.lat, a.lon)]
    kt = [cell(x, y) for x, y in zip(t.LATITUD, t.LONGITUD)]
    kf = [cell(x, y) for x, y in zip(f.lat, f.lon)]
    g = pd.DataFrame({'AXA': pd.Series(ka).value_counts()}).join(
        pd.DataFrame({'ATUS': pd.Series(kt).value_counts()}), how='outer').join(
        pd.DataFrame({'fis_hom': pd.Series([k for k, d in zip(kf, f.DELITO)
                                            if str(d).upper().startswith('HOMICIDIO')]).value_counts()}),
        how='outer').join(
        pd.DataFrame({'atus_vru': t.assign(k=kt).groupby('k').vru_vict.sum()}), how='outer')
    return g.fillna(0)


def curva(g, freq, outcome):
    """Curvas de cobertura: fraccion de celdas (x) vs fraccion del objetivo capturada (y).

    OJO — el desempate NO es un detalle. La mayoria de las celdas comparten el mismo
    valor de frecuencia (1 o 2 siniestros), asi que el orden dentro de esos bloques
    decide el resultado. Si se desempata a favor del objetivo, la curva sale
    artificialmente buena; si se desempata en contra, artificialmente mala.
    Aqui se usa la ESPERANZA bajo desempate aleatorio, que es exacta y no depende
    del orden en que vengan las filas: dentro de un bloque de m celdas empatadas
    que suman S del objetivo, tomar j celdas captura en promedio (j/m)*S.
    Se devuelven ademas las cotas pesimista y optimista para poder reportar el rango.
    """
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
        m = j - i
        blq = ov[i:j]
        S = blq.sum()
        k = np.arange(1, m + 1)
        esp[i:j] = acc + S * k / m
        pes[i:j] = acc + np.cumsum(np.sort(blq))            # lo peor primero
        opti[i:j] = acc + np.cumsum(np.sort(blq)[::-1])     # lo mejor primero
        acc += S
        i = j
    opt = np.cumsum(np.sort(ov)[::-1])
    z = lambda v: np.concatenate([[0], v / tot])
    x0 = np.concatenate([[0], np.arange(1, n + 1) / n])
    return x0, z(esp), z(opt), z(pes), z(opti)


def abc(x0, obs, opt):
    """Area entre la curva optima y la observada, normalizada por el area
    entre la optima y la diagonal aleatoria. 0 = optimo, 1 = como el azar."""
    num = trapz(opt - obs, x0)
    den = trapz(opt - x0, x0)
    return float(num / den) if den > 0 else np.nan


def main():
    A, T, F = cargar()
    filas = []
    for res in RES:
        for city, bb in BB.items():
            g = grid(A, T, F, city, bb, res)
            for freq, outcome, etiq in CORRIDAS:
                c = curva(g, freq, outcome)
                if c is None:
                    continue
                x0, obs, opt, pes, opti = c
                n = len(g)
                empates = 1 - g[freq].nunique() / n
                fila = {'ciudad': city, 'res': res, 'capa': freq, 'objetivo': outcome,
                        'corrida': etiq, 'celdas': n,
                        'total_objetivo': float(g[outcome].sum()),
                        'empates': round(float(empates), 3),
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
                    fila['rho'] = round(float(rho), 3)
                    fila['p'] = float(p)
                filas.append(fila)
                print(f"res{res} {city:14s} {etiq:52s} ABC {fila['abc']:.3f}  "
                      f"cob10 {fila['cob_10']:5.1f} / techo {fila['techo_10']:5.1f}")
    df = pd.DataFrame(filas)
    df.to_csv('matriz_cuatro_corridas.csv', index=False)
    json.dump(filas, open('matriz_cuatro_corridas.json', 'w'), separators=(',', ':'))
    print('\nOK -> matriz_cuatro_corridas.csv / .json')


if __name__ == '__main__':
    main()
