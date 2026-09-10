"""
04_reticula_contraste.py
Retícula H3 y contraste de observabilidad entre las tres fuentes, ciudad por
ciudad, en dos escalas.

Que calcula, en lenguaje llano:
  - rho (Spearman): si los lugares se ordenan igual en dos listas. El hexagono
    con mas reportes AXA, ¿es tambien el que mas muertes tiene? 1 = mismo orden,
    0 = el orden de una lista no dice nada de la otra.
  - cobertura: se toma el 10% de celdas que un instrumento de FRECUENCIA
    marcaria como prioritarias y se cuenta que fraccion de todas las muertes de
    la ciudad cae dentro.
  - techo: lo mismo, con el mismo numero de celdas, pero escogidas buscando
    muertes. Es lo alcanzable con el mismo presupuesto de intervencion.

Salida -> ../datos/resumen_observabilidad_6ciudades.csv
          ../datos/reticula_<ciudad>_res<N>.csv
"""
import pandas as pd, h3
from scipy.stats import spearmanr
from pathlib import Path

D   = Path(__file__).resolve().parent.parent / "datos"
CIU = ['TAMPICO','CIUDAD MADERO','REYNOSA','VICTORIA','NUEVO LAREDO','MATAMOROS']
# recorte urbano por ciudad (lat_min, lat_max, lon_min, lon_max)
BB = {'TAMPICO':(22.15,22.35,-98.00,-97.75), 'CIUDAD MADERO':(22.20,22.35,-97.95,-97.75),
      'REYNOSA':(25.95,26.20,-98.45,-98.20), 'VICTORIA':(23.65,23.83,-99.25,-98.98),
      'NUEVO LAREDO':(27.40,27.62,-99.62,-99.42), 'MATAMOROS':(25.75,25.95,-97.60,-97.40)}
RESOL = {9: '~0.12 km2 (cuadra)', 10: '~0.017 km2 (esquina)'}

axa = pd.read_csv(D/'axa_tamaulipas_6c_2019_2023.csv', low_memory=False)
at  = pd.read_csv(D/'atus_tamaulipas_6c_2019_2023.csv', low_memory=False)
at  = at.rename(columns={'LATITUD':'lat','LONGITUD':'lon'})
fi  = pd.read_csv(D/'fiscalia_tamaulipas_limpio.csv', low_memory=False)
fi  = fi[fi.geo_ok & fi.MUNICIPIO_HECHO.isin(CIU) & fi['AÑO'].between(2019, 2023)]
fi['CIUDAD'] = fi.MUNICIPIO_HECHO

def recorte(d, c):
    a, b, x, y = BB[c]
    return d[d.lat.between(a, b) & d.lon.between(x, y)]

filas = []
for c in CIU:
    A  = recorte(axa[axa.CIUDAD == c], c)
    T  = recorte(at[at.CIUDAD == c],  c)
    Fz = recorte(fi[fi.CIUDAD == c],  c)
    Fh = Fz[Fz.DELITO == 'HOMICIDIO']
    fila = {'ciudad':c, 'axa_siniestros':len(A), 'axa_muertes':0,
            'atus_eventos':len(T), 'atus_muertos':int(T.TOTMUERTOS.sum()),
            'atus_heridos':int(T.TOTHERIDOS.sum()), 'atus_vru':int(T.vru.sum()),
            'fis_carpetas':len(Fz), 'fis_homicidios':len(Fh),
            'fis_lesiones':int((Fz.DELITO=='LESIONES').sum()),
            'axa_moto':int(A.moto.sum()) if 'moto' in A.columns else 0,
            'atus_moto_ev':int(T.moto_ev.sum()), 'atus_moto_vic':int(T.moto_vic.sum())}
    for RES in RESOL:
        H = lambda la, lo: [h3.latlng_to_cell(a, b, RES) for a, b in zip(la, lo)]
        Am = A[A.moto] if 'moto' in A.columns else A.iloc[0:0]
        d = pd.DataFrame({
            'axa'      : pd.Series(H(A.lat, A.lon)).value_counts(),
            'axa_moto' : pd.Series(H(Am.lat, Am.lon)).value_counts(),
            'atus_ksi' : T.assign(h=H(T.lat, T.lon)).groupby('h')['ksi'].sum(),
            'atus_vru' : T.assign(h=H(T.lat, T.lon)).groupby('h')['vru'].sum(),
            'atus_moto': T.assign(h=H(T.lat, T.lon)).groupby('h')['moto_vic'].sum(),
            'fis_hom'  : Fh.assign(h=H(Fh.lat, Fh.lon)).groupby('h').size()}).fillna(0)
        d.to_csv(D/f'reticula_{c.replace(" ","_").lower()}_res{RES}.csv')
        n = len(d); k = max(1, round(n*0.10)); top = d.nlargest(k, 'axa')
        fila[f'celdas_res{RES}']      = n
        fila[f'rho_atusksi_res{RES}'] = round(spearmanr(d.axa, d.atus_ksi).statistic, 3)
        fila[f'rho_fishom_res{RES}']  = round(spearmanr(d.axa, d.fis_hom ).statistic, 3)
        fila[f'cob_atusksi_res{RES}'] = round(100*top.atus_ksi.sum()/max(d.atus_ksi.sum(),1), 1)
        fila[f'techo_atusksi_res{RES}']=round(100*d.nlargest(k,'atus_ksi').atus_ksi.sum()/max(d.atus_ksi.sum(),1), 1)
        fila[f'cob_fishom_res{RES}']  = round(100*top.fis_hom.sum()/max(d.fis_hom.sum(),1), 1)
        fila[f'techo_fishom_res{RES}']= round(100*d.nlargest(k,'fis_hom').fis_hom.sum()/max(d.fis_hom.sum(),1), 1)
    filas.append(fila)

r = pd.DataFrame(filas)
r.to_csv(D/'resumen_observabilidad_6ciudades.csv', index=False, encoding='utf-8-sig')
pd.set_option('display.width', 250)
print(r[['ciudad','axa_siniestros','atus_eventos','atus_muertos','fis_carpetas','fis_homicidios']].to_string(index=False))
for RES, lab in RESOL.items():
    print(f'\n--- res {RES} {lab}')
    print(r[['ciudad', f'celdas_res{RES}', f'rho_atusksi_res{RES}', f'rho_fishom_res{RES}',
             f'cob_fishom_res{RES}', f'techo_fishom_res{RES}']].to_string(index=False))
print(f"\nGuardado en: {D/'resumen_observabilidad_6ciudades.csv'}")
