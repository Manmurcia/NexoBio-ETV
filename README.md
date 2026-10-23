# NexoBio-ETV

Sistema web de vigilancia epidemiológica e indicadores de salud pública para enfermedades transmitidas por vectores (ETV).
Proyecto de la materia **Minería de Datos**, Universidad de Cundinamarca — Extensión Chía.

- **Aplicación publicada:** https://enfermedades-7kju.onrender.com/
- **Repositorio:** https://github.com/Manmurcia/NexoBio-ETV
- **Pull requests:** [#1 Etapa 1](https://github.com/Manmurcia/NexoBio-ETV/pull/1) · [#2 Etapa 2](https://github.com/Manmurcia/NexoBio-ETV/pull/2) · [#3](https://github.com/Manmurcia/NexoBio-ETV/pull/3) y [#4](https://github.com/Manmurcia/NexoBio-ETV/pull/4) Etapa 3 · [#5 correcciones de la Etapa 2](https://github.com/Manmurcia/NexoBio-ETV/pull/5)
- **Informe de Power BI (Etapa 4):** _pendiente de publicar — ver [powerbi/GUIA_CONSTRUCCION_POWERBI.md](powerbi/GUIA_CONSTRUCCION_POWERBI.md)_

**Integrantes:** Carlos Julio Pérez Rodríguez, Manuel Felipe Murcia Suarez, José Daniel Gómez Rodríguez.
**Docente / gestor del conocimiento:** Edison Gustavo Cañon Varela.

## Estructura

```
app.py                      Aplicación Flask (rutas de las Etapas 1 a 4)
requirements.txt            Dependencias (Flask y gunicorn para la web; pandas, openpyxl y tabulate para los scripts)
templates/etapa 1|2|3|4/    Páginas de cada etapa (la Etapa 4 es el menú "Conocimiento evidente")
static/                     CSS, imágenes e informes PDF
data/                       Archivos de datos originales (Etapas 1 y 2), sin modificar
salida/                     Resultado de la consolidación de la Etapa 1
reporte_perfilamiento/      Resultado de los scripts de calidad de la Etapa 2
powerbi/                    Etapa 4: datos del ETL, modelo, medidas DAX y guía del informe de Power BI
scripts/
    consolidar_datos.py         Etapa 1: consolida los datos por escala (global, nacional, regional)
    perfilamiento_etapa2.py     Etapa 2: perfil por variable (tipo, únicos, nulos, mín/máx/promedio)
    dimensiones_calidad.py      Etapa 2: las 6 dimensiones de calidad con fórmula y resultado
    tratamiento_etapa2.py       Etapa 2: aplica el plan de tratamiento y mide antes / después
    verificar_etapa4.py         Etapa 4: calcula los valores que deben mostrar las medidas DAX
```

## Datos

**Etapas 1 y 2** — archivos originales en `data/`:

| Archivo | Institución | Registros | Portal de origen |
|---|---|---:|---|
| `sivigila_dengue.csv` | Instituto Nacional de Salud (SIVIGILA) | 53.813 | [Buscador de microdatos SIVIGILA](https://portalsivigila.ins.gov.co/Paginas/Buscador.aspx) |
| `PERFIL_EPIDEMIOLOGICO_ANUAL.csv` | Gobernación de Cundinamarca | 98.322 | incluido en `data/` |
| `SALUD.xlsx` | Gobernación de Cundinamarca | 63.978 | incluido en `data/` |
| `disease_outbreaks_HDX.xlsx` | OMS / Humanitarian Data Exchange | 3.566 | [HDX · Global pandemic and epidemic outbreaks](https://data.humdata.org/dataset/global-pandemic-and-epidemic-outbreaks) |
| `Datos_de_Vigilancia_en_Salud_Publica_de_Colombia.csv` | Instituto Nacional de Salud | 241.746 | [Portal SIVIGILA](https://portalsivigila.ins.gov.co/) |
| `Public_Use_Ixodes_County_Table_2023.xlsx` | CDC (ArboNET Tick Module) | 21.775 (7 hojas) | [CDC · Tick Surveillance Data](https://www.cdc.gov/ticks/surveillance/TickSurveillanceData.html) |

**Etapa 4** — archivos resultantes del ETL de la Etapa 3, en `powerbi/datos/`:

| Archivo | Contenido | Registros | Periodo |
|---|---|---:|---|
| `Datos_de_Vigilancia_Colombia_Limpio.csv` | Vigilancia de **Cundinamarca**, 42 eventos (el nombre del archivo dice «Colombia») | 107.645 filas · 298.690 casos | 2007–2022 |
| `Datos_de_Vigilancia_ColombiaCompleto_Limpio.csv` | Dengue, dengue grave, chikungunya y chagas en Colombia | 237.141 filas · 1.269.342 casos | 2007–2022 |
| `Regional_Cundinamarca_ETV_Limpio.csv` | Casos ETV por municipio de Cundinamarca, con tasa de incidencia de dengue | 1.608 filas · 41.556 casos | 2007–2022 |
| `Disease_Outbreaks_HDX_Limpio.xlsx` | Brotes reportados a la OMS en el mundo | 3.568 brotes | 1996–2026 (2026 incompleto) |

Más cinco tablas de apoyo hechas por el equipo (`clasificacion_evento_vigilancia.csv`, `clasificacion_enfermedad_hdx.csv`, `dim_departamento.csv`, `dim_evento_etv.csv`, `dim_anio.csv`).
La fuente original del archivo de Cundinamarca (todos los eventos) no está en `data/`; en el repositorio solo está el archivo ya tratado.

## Ejecutar la aplicación

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python app.py                   # http://127.0.0.1:5000
```

## Etapa 2 — Calidad de datos

Desde la raíz del repositorio:

```bash
python scripts/perfilamiento_etapa2.py       # reporte_perfilamiento/perfil_*.csv y resumen_global.*
python scripts/dimensiones_calidad.py        # reporte_perfilamiento/dimensiones_calidad.json
python scripts/tratamiento_etapa2.py         # reporte_perfilamiento/antes_despues.json
```

Criterios que aplican los scripts:

- `"SD"`, `"SIN INFORMACION"` y `"MUNICIPIO DESCONOCIDO"` se cuentan como **valores faltantes**, no como categorías válidas (por eso la completitud de `sivigila_dengue` es 86,50 % y no 100 %). Las columnas de códigos (`iso2`, `iso3`, `State`) se excluyen de ese reemplazo porque `SD` es Sudán y Dakota del Sur.
- Los CSV se leen como UTF-8 (leerlos como latin1 corrompe caracteres como la «Ñ»).
- El texto se estandariza **antes** de eliminar duplicados; de lo contrario quedan 11.801 filas repetidas ocultas por mayúsculas y espacios.
- Los valores fuera de rango (edad, años, decimales perdidos) no se eliminan ni se imputan: pasan a una tabla de revisión.

| Dataset | Registros | Completitud | Hallazgo principal |
|---|---:|---:|---|
| SIVIGILA Dengue | 53.813 | 86,50 % | `cod_mun_d` con 92 % de "SD"; 3 edades fuera de 0–110 |
| Perfil Epidemiológico | 98.322 | 99,9999 % | 54.524 filas repetidas (55,45 %) tras estandarizar; columnas CICLO DE VIDA / MES desalineadas |
| SALUD Cundinamarca | 63.978 | 95,96 % | 565 valores con decimal perdido; 22 filas con año > 2024; 35 filas no municipales |
| Disease Outbreaks HDX | 3.566 | 99,31 % | 419 celdas faltantes (who_region 266) |
| Vigilancia Colombia | 241.746 | 99,79 % | `ANO` y `COD_MUN_O` como texto; 4.605 municipios desconocidos |
| Ixodes (CDC) | 21.775 | 100,00 % | Encabezado desplazado en las 7 hojas de datos |

## Etapa 3 — ETL con SSIS

Las páginas de la Etapa 3 (reglas de tratamiento, diseño del paquete, iteraciones, comparación, informe y video) están en `templates/etapa 3/`;
el informe técnico está en `static/docs/informe_etapa3.pdf`. Los cuatro archivos resultantes del ETL se usan en la Etapa 4.

## Etapa 4 — Conocimiento evidente (Power BI)

Análisis exploratorio de los archivos del ETL, presentado en un informe de Power BI de cuatro páginas (una por pregunta) e integrado en la aplicación (menú **Conocimiento evidente**).

| Tablero | Pregunta | Datos | Unidad de análisis |
|---|---|---|---|
| 1 · Composición | ¿Qué se notifica en Cundinamarca y qué peso tienen las ETV? | Vigilancia de Cundinamarca | casos por evento, municipio, semana y año |
| 2 · Territorios | ¿Dónde se concentran los casos y dónde pesa más el dengue grave? | Colombia completo + regional de Cundinamarca | casos agregados por territorio |
| 3 · Tiempo | ¿Qué ciclos, estacionalidad y cambios de gravedad hay entre 2007 y 2022? | Colombia completo | casos por evento, municipio, semana y año |
| 4 · Multivariado | ¿Dónde y cuándo pesan más las ETV entre los brotes globales? | Brotes de la OMS (1996–2025) | un brote reportado |

Archivos:

- `powerbi/datos/` — los cuatro archivos del ETL y las tablas de apoyo que se cargan en Power BI.
- `powerbi/MEDIDAS_DAX.md` — modelo de datos, medidas DAX por tablero y **resultados esperados** para comprobarlas.
- `powerbi/GUIA_CONSTRUCCION_POWERBI.md` — cómo construir, publicar, insertar y actualizar el informe.
- `powerbi/NexoBio_ConocimientoEvidente.pbix` — archivo de Power BI (si pesa más de 100 MB, enlace de descarga aquí: _pendiente_).
- Los textos de cada tablero (preguntas, interpretaciones, doce conocimientos con sus ocho elementos, limitaciones y decisiones) están en la web, sección **Conocimiento evidente**.

Verificar las cifras (desde la raíz del repositorio):

```bash
pip install -r requirements.txt
python scripts/verificar_etapa4.py
```

Abrir y actualizar el informe: abrir el `.pbix` en Power BI Desktop, ajustar el parámetro `RutaDatos` a la carpeta `powerbi/datos` y pulsar **Actualizar**.

## Gestión en GitHub

Una rama por etapa (`feature/etapa-1`, `feature/etapa-2`, …) integrada a `main` mediante pull request.
