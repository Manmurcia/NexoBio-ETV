# Decisiones del modelo OLAP de la Etapa 5

El modelo combina tres fuentes en `fact_notificacion`, con cuatro dimensiones conformadas. El esquema está en [`../../scripts/olap/crear_modelo.sql`](../../scripts/olap/crear_modelo.sql); el ETL, la carga y la validación se ejecutan con `python scripts/olap/cargar_modelo.py`.

## 1. Fuentes, unidad y cobertura

| Fuente | Archivo | Registros cargados | Medida |
|---|---|---:|---:|
| SIVIGILA Colombia | `datos/Datos_de_Vigilancia_ColombiaCompleto_Limpio.csv` | 237.141 | 1.269.342 casos |
| SIVIGILA Cundinamarca | `consolidacion/regional_cundinamarca_etv.csv` | 1.640 | 42.430 casos |
| OMS/HDX | `datos/Disease_Outbreaks_HDX_Limpio.xlsx` | 563 | 563 brotes |

El hecho tiene 239.344 filas. Los casos nacionales incluyen 1.265.731 ubicados en departamentos y 3.611 clasificados como Exterior o procedencia desconocida. Las coberturas nacional y regional de SIVIGILA se superponen en Cundinamarca; los casos regionales no se suman a los nacionales. Las consultas de casos filtran una sola fuente y rechazan selecciones de múltiples fuentes. La vista comparativa calcula porcentajes dentro de cada fuente, no totales combinados.

La fuente regional está agregada por año, municipio y evento; no tiene semana epidemiológica. Se representa con semana 0 y no se une con la fuente nacional como si compartiera su granularidad semanal. La tasa de incidencia y letalidad regional no se cargan: el modelo conserva casos notificados y no tiene población como denominador.

## 2. Alcance y correspondencias de evento

Se cargan solo enfermedades transmitidas por vectores. La clasificación de SIVIGILA excluye eventos no ETV y eventos de mortalidad. `mapeo_enfermedad_sivigila.csv` armoniza el evento original: dengue, dengue grave y mortalidad por dengue comparten enfermedad Dengue, aunque mortalidad no entra al hecho.

OMS/HDX se clasifica por `icd104n`, no por `icd103n`, que puede agrupar enfermedades distintas. `clasificacion_enfermedad_hdx.csv` incluye la correspondencia por enfermedad, el nombre armonizado y la marca ETV. Así se mantiene Chikungunya, Zika y Oropouche como enfermedades diferenciadas. La tabla debe tener una fila única por código `icd104n`; aliases descriptivos del archivo de origen se consolidan en esa clave.

No se incluye una dimensión de vector porque el origen no da esa relación para todos los eventos y asignarla manualmente sería una clasificación inferida. La jerarquía dimensional es enfermedad armonizada → evento original.

## 3. Medidas y exclusividad

`casos` y `brotes` son medidas excluyentes por registro. Cada fila SIVIGILA tiene `casos` y `brotes = NULL`; cada fila OMS/HDX tiene `brotes = 1` y `casos = NULL`. La carga valida las medidas según la fuente y concilia los totales de registros y medidas con cada archivo de origen.

Los eventos `MORTALIDAD POR DENGUE` y `MORTALIDAD POR MALARIA` representan defunciones, no casos: se excluyen del hecho para no mezclar unidades. Por esta razón, el porcentaje de dengue grave usa como denominador Dengue + Dengue grave y se recalcula por cada grupo.

## 4. Tiempo y estacionalidad

La clave temporal es `tiempo_key = año * 100 + semana`. SIVIGILA Colombia conserva su semana epidemiológica; SIVIGILA Cundinamarca y OMS/HDX usan semana 0 para datos anuales. Las etiquetas `periodo_analisis` (2007–2010, 2011–2016 y 2017–2022) y `tipo_anio_sivigila` permiten reproducir los análisis existentes. La dimensión también conserva `periodo` de la serie OMS y marca 2026 como incompleto.

El índice estacional se calcula por año y unidad: los casos de cada trimestre o semana se dividen por el total anual de esa unidad, se expresan como porcentaje y luego se promedian entre años. Se excluyen semana 0 (sin semana) y semana 53; el índice semanal usa las semanas 1–52.

## 5. Territorio y HDX

En Colombia, el código DANE permite asignar región natural, departamento y municipio. «Exterior» y «Procedencia desconocida» se conservan con `region = 'No geografico'` y se excluyen de rankings territoriales de departamentos. Los agregados nacionales que los incluyen se identifican explícitamente.

El archivo limpio de HDX no trae códigos ISO2/ISO3. El nombre del país se utiliza como `codigo_territorio`; se conservan `who_region` y `unsd_region` como región OMS y subregión ONU. No se fabrican identificadores que no estén en el origen.

## 6. Validaciones y regresión

`cargar_modelo.py` regenera `olap/nexobio_olap.db` y `olap/validaciones.json`, comprobando claves únicas, integridad referencial, granularidad, exclusividad de medidas y conciliación por fuente. `verificar_conocimientos.py` prueba las cifras publicadas, el aislamiento de fuentes y los porcentajes de la vista comparativa.

La regresión con los datos de Etapa 4 debe preservar:

| Indicador | Valor |
|---|---:|
| Casos nacionales ubicados en departamentos | 1.265.731 |
| Porcentaje acumulado de los cinco departamentos principales | 47,79 % |
| Porcentaje territorial de dengue grave | 3,67 % |
| Promedio anual nacional (2007–2022) | 79.334 |

La comparación de fuentes usa únicamente Dengue y Chikungunya, las enfermedades comunes a las tres fuentes dentro de los datos cargados; los porcentajes se normalizan independientemente en cada una.
