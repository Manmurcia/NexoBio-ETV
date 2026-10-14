# NexoBio-ETV

Sistema web de vigilancia epidemiológica e indicadores de salud pública para enfermedades
transmitidas por vectores (ETV). Proyecto de la materia **Minería de Datos**, Universidad de
Cundinamarca — Extensión Chía.

- **Aplicación publicada:** https://enfermedades-7kju.onrender.com/
- **Repositorio:** https://github.com/Manmurcia/NexoBio-ETV
- **Pull requests:** [#1 Etapa 1](https://github.com/Manmurcia/NexoBio-ETV/pull/1) · [#2 Etapa 2](https://github.com/Manmurcia/NexoBio-ETV/pull/2)

**Integrantes:** Carlos Julio Pérez Rodríguez, Manuel Felipe Murcia Suarez, José Daniel Gómez Rodríguez.
**Docente / gestor del conocimiento:** Edison Gustavo Cañon Varela.

## Estructura

```
app.py                           Aplicación Flask (rutas de Etapas)
requirements.txt                 Dependencias de la aplicación web (Flask, gunicorn)
requirements-scripts.txt         Dependencias de los scripts de calidad (pandas, openpyxl, tabulate)
templates/etapa 1|2|3/           Páginas de cada etapa
static/                          CSS, imágenes e informes PDF
data/                            Archivos de datos originales (los 6 datasets, sin modificar)
scripts/
    consolidar_datos.py          Etapa 1: consolida los datos por escala (global, nacional, regional)
    perfilamiento_etapa2.py      Etapa 2: perfil por variable (tipo, únicos, nulos, mín/máx/promedio)
    dimensiones_calidad.py       Etapa 2: 6 dimensiones de calidad con fórmula y resultado
    tratamiento_etapa2.py        Etapa 2: aplica el plan de tratamiento y mide antes / después
    generar_plantillas_etapa2.py Genera las páginas 3 y 4 de la web desde el reporte
reporte_perfilamiento/           Salida de los scripts (CSV y JSON); es la fuente de los números de la web
salida/                          Salida de consolidar_datos.py
```

## Datos

Los seis archivos originales están en `data/` (sin modificar). Instituciones y portales de origen:

| Archivo | Institución | Registros | Portal de origen |
|---|---|---:|---|
| `sivigila_dengue.csv` | Instituto Nacional de Salud (SIVIGILA) | 53.813 | [Buscador de microdatos SIVIGILA](https://portalsivigila.ins.gov.co/Paginas/Buscador.aspx) |
| `PERFIL_EPIDEMIOLOGICO_ANUAL.csv` | Gobernación de Cundinamarca | 98.322 | incluido en `data/` |
| `SALUD.xlsx` | Gobernación de Cundinamarca (Secretaría de Prospectiva e Integración Territorial) | 63.978 | incluido en `data/` |
| `disease_outbreaks_HDX.xlsx` | OMS / Humanitarian Data Exchange | 3.566 | [HDX · Global pandemic and epidemic outbreaks](https://data.humdata.org/dataset/global-pandemic-and-epidemic-outbreaks) |
| `Datos_de_Vigilancia_en_Salud_Publica_de_Colombia.csv` | Instituto Nacional de Salud | 241.746 | [Portal SIVIGILA](https://portalsivigila.ins.gov.co/) · incluido en `data/` |
| `Public_Use_Ixodes_County_Table_2023.xlsx` | CDC (ArboNET Tick Module) | 21.775 (7 hojas) | [CDC · Tick Surveillance Data](https://www.cdc.gov/ticks/surveillance/TickSurveillanceData.html) |

Los registros se cuentan sin títulos institucionales, encabezados ni filas de etiquetas.

## Ejecutar la aplicación

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python app.py                   # http://127.0.0.1:5000
```

## Reproducir el perfilamiento y la calidad de datos (Etapa 2)

Ejecutar desde la raíz del repositorio:

```bash
pip install -r requirements-scripts.txt
python scripts/perfilamiento_etapa2.py       # -> reporte_perfilamiento/perfil_*.csv, resumen_global.*
python scripts/dimensiones_calidad.py        # -> reporte_perfilamiento/dimensiones_calidad.json
python scripts/tratamiento_etapa2.py         # -> reporte_perfilamiento/antes_despues.json
python scripts/generar_plantillas_etapa2.py  # -> templates/etapa 2/3_perfilamiento.html y 4_dimensiones.html
```

Criterios que aplican los scripts:

- `"SD"`, `"SIN INFORMACION"` y `"MUNICIPIO DESCONOCIDO"` se cuentan como **valores faltantes**, no como categorías válidas
  (por eso la completitud de `sivigila_dengue` es 86,50 % y no 100 %). Las columnas de códigos de país/estado
  (`iso2`, `iso3`, `State`) se excluyen de ese reemplazo porque `SD` es Sudán / Dakota del Sur.
- Los CSV se leen como UTF-8 (leerlos como latin1 corrompe caracteres como la "Ñ").
- Se estandariza el texto **antes** de eliminar duplicados; de lo contrario quedan 11.801 filas repetidas ocultas por mayúsculas.
- Los valores fuera de rango (edad, años, decimales perdidos) no se eliminan ni se imputan: pasan a una tabla de revisión.

## Resultados principales

| Dataset | Registros | Completitud | Hallazgo principal |
|---|---:|---:|---|
| SIVIGILA Dengue | 53.813 | 86,50 % | `cod_mun_d` con 92 % de "SD"; 3 edades fuera de 0–110 |
| Perfil Epidemiológico | 98.322 | 99,9999 % | 54.524 filas repetidas (55,45 %) tras estandarizar; columnas CICLO DE VIDA / MES desalineadas |
| SALUD Cundinamarca | 63.978 | 95,96 % | 565 valores con decimal perdido; 22 filas con año > 2024; 35 filas no municipales |
| Disease Outbreaks HDX | 3.566 | 99,31 % | 419 celdas faltantes (who_region 266) |
| Vigilancia Colombia | 241.746 | 99,79 % | `ANO` y `COD_MUN_O` como texto; 4.605 municipios desconocidos |
| Ixodes (CDC) | 21.775 | 100,00 % | Encabezado desplazado en las 7 hojas de datos |

## Etapa 3 — ETL con SSIS

Las páginas de la Etapa 3 (reglas de tratamiento, diseño del paquete, iteraciones, comparación, informe y video)
están en `templates/etapa 3/`. El paquete SSIS (`ETL_Enfermedades`) y sus scripts SQL se documentan allí.

## Gestión en GitHub

Una rama por etapa (`feature/etapa-1`, `feature/etapa-2`, …) integrada a `main` mediante pull request.
