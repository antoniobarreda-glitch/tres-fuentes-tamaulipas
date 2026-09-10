# Paquete de replicación — auditoría de observabilidad AXA / ATUS / Fiscalía

Tamaulipas y Nuevo León, 2019–2023. Material para coautores del manuscrito
enviado a ICSC-CITIES 2026.

**Alcance:** este paquete contiene únicamente datos de Tamaulipas y Nuevo León.
No incluye material de Querétaro, Chihuahua, Sonora ni Ciudad de México, que
pertenecen a otras líneas del proyecto.

---

## Procedencia de los datos

Las cuatro fuentes son públicas y ninguna contiene datos personales.

| Fuente | Origen | Acceso |
|---|---|---|
| AXA / I2DS | Datos abiertos publicados por AXA Seguros a través del Instituto Internacional de Ciencia de Datos | i2ds.org/datos-abiertos |
| ATUS | Accidentes de tránsito terrestre en zonas urbanas y suburbanas, INEGI | inegi.org.mx/programas/accidentes |
| Fiscalías de Tamaulipas y Nuevo León | Respuestas a solicitudes por la Plataforma Nacional de Transparencia (folio 811197026000256, oficio FGJ/DGAJDH/IP/12551/2026; expediente SAI/314/2026) | incluidas en este paquete |
| Defunciones registradas (EDR) | INEGI, 2019–2024 | inegi.org.mx/programas/edr |
| AGEB urbanas | Marco Geoestadístico 2020, INEGI | inegi.org.mx/programas/mg |

Las carpetas de investigación se identifican por unidad, fecha, delito y municipio;
no traen nombres ni datos identificables de las víctimas.

Cuando el manuscrito se publique, este paquete puede hacerse público y obtener un
DOI (por ejemplo conectando el repositorio a Zenodo) para que sea citable.

## Qué hay aquí

```
datos/
  tamaulipas/     las tres fuentes de las seis ciudades + los registros ya
                  etiquetados por estrato urbano/periurbano (estratos_*.csv)
                  y las retículas H3 por ciudad y resolución
  nuevo_leon/     respuesta íntegra de la Fiscalía de NL (folio SAI-314-2026)
                  y el resumen de los seis municipios
  inegi/          validación de mortalidad, AGEB urbanas de ambos estados (mg/)
                  y los polígonos urbanos disueltos (.gpkg, abre en QGIS)
  resultados/     las salidas del análisis: matriz_urbano.csv es la tabla
                  principal, pisos_urbano.csv el piso estructural,
                  periurbano_resumen.csv el estrato que queda fuera del polígono
scripts/          01 a 08, en orden de ejecución
```

## Orden de ejecución

```
pip install pandas numpy h3 scipy geopandas shapely openpyxl
```

En Windows/PowerShell, si `pip` no responde: `python -m pip install ...`
Si geopandas truena al instalarse en Windows, la vía fácil es
`conda install -c conda-forge geopandas`.

| # | Script | Qué produce |
|---|--------|-------------|
| 1 | `01_extraer_axa_tamaulipas.py` | AXA filtrado a las seis ciudades |
| 2 | `02_extraer_atus_tamaulipas.py` | ATUS filtrado a las seis ciudades |
| 3 | `03_limpiar_fiscalia.py` | Fiscalía de Tamaulipas con coordenadas corregidas |
| — | `extraer_ageb.ps1` | saca las AGEB de INEGI del zip nacional (PowerShell) |
| 7 | `07_poligono_urbano.py` | polígonos urbanos y `estratos_*.csv` |
| 8 | `08_corridas_urbano.py` | **la tabla principal de resultados** |
| 6 | `06_validacion_inegi.py` | contraste contra mortalidad INEGI |

Los pasos 1 a 3 solo hacen falta si se quiere reconstruir desde las bases
nacionales; sus salidas ya vienen en `datos/`. Para reproducir los resultados
basta correr **07 y luego 08**.

`04` y `05` son las versiones anteriores, cuando el recorte era un rectángulo de
coordenadas en vez del polígono urbano. Se conservan para poder comparar, pero
los resultados vigentes son los de `08`.

Cada script trae adentro sus propias instrucciones de ejecución.

## Antes de revisar los números

Lee `PROCESOS.pdf`. Recorre el pipeline paso a paso y marca en rojo los ocho
puntos donde hay una decisión estadística que debe confirmarse antes del envío,
con la pregunta concreta en cada uno.
