# Decisiones de diseño del modelo estrella

El modelo integra tres fuentes (SIVIGILA Colombia, SIVIGILA Cundinamarca y brotes de la OMS) en una sola tabla de hechos.
Al unir fuentes aparecen riesgos de doble conteo y de mezcla de unidades; estas cuatro decisiones los resuelven antes de cargar datos.
Todas las cifras se obtuvieron de los archivos tratados en la Etapa 3 (`powerbi/datos/`).

## Decisión 1. Qué se carga y cómo se evita el doble conteo

**Problema.** Los casos de Cundinamarca aparecen en tres archivos. Los 4 eventos que el archivo de Cundinamarca comparte con el nacional
(dengue, dengue grave, chikungunya, chagas) son idénticos al departamento 25 del archivo nacional: 13.571 filas y 41.556 casos en ambos.
El archivo regional ETV (1.608 filas) vuelve a contener esos mismos 41.556 casos. Cargar los tres y sumar contaría Cundinamarca dos o tres veces.

**Decisión.** Cargar tres fuentes que no se solapan por construcción:

| Fuente (`dim_fuente`) | Qué se carga | Filas | Medida |
|---|---|---:|---|
| SIVIGILA Colombia (Nacional) | Dengue, dengue grave, chikungunya y chagas, 2007–2022 | 237.141 | 1.269.342 casos |
| SIVIGILA Cundinamarca (Regional) | Solo eventos que el nacional no trae: zika, malaria (5 variantes) y leishmaniasis (3 variantes) | 3.747 | 8.782 casos |
| OMS / HDX (Global) | Brotes de enfermedades transmitidas por vectores, 1996–2026 | 563 | 563 brotes |

**No se carga:**

- Los 4 eventos repetidos del archivo de Cundinamarca (13.571 filas, 41.556 casos).
- El archivo regional ETV (1.608 filas). Se conserva como validación independiente: los casos de Cundinamarca del modelo deben coincidir con él.
- La tasa de incidencia y la letalidad del archivo regional: no hay población por municipio para recalcularlas ni contrastarlas. Se documenta como limitación.

**Consecuencia.** Zika, malaria y leishmaniasis solo existen para Cundinamarca; en `dim_evento.cobertura` figuran como «Solo Cundinamarca»
y no pueden presentarse como cifras nacionales. Como las dos fuentes SIVIGILA no comparten eventos, `SUM(casos)` entre ellas no duplica.

## Decisión 2. Solo enfermedades transmitidas por vectores (ETV)

**Problema.** Los archivos traen eventos ajenos al proyecto: 27 eventos de Cundinamarca (90.270 filas, 248.294 casos) y 3.005 brotes de la OMS
(COVID-19, cólera, etc.). Cargarlos obligaría a filtrar en cada consulta y distorsionaría los totales.

**Decisión.** Cargar únicamente ETV. La composición con eventos no ETV ya se presentó en la Etapa 4.
Para la OMS se usa `clasificacion_enfermedad_hdx.csv` (`es_etv = 'Si'`): 563 brotes, 150 países, 14 de ellos en 2026 (año incompleto).

**Consecuencia en la jerarquía de evento.** Con solo ETV el nivel `grupo` (ETV / No ETV) sería constante. Se reemplaza por **vector → enfermedad → evento**.
La clasificación por vector la define el equipo a partir del agente transmisor de cada enfermedad, igual que la región natural se define a partir del código del departamento:

| Vector | Enfermedades |
|---|---|
| Mosquito | Dengue, chikungunya, zika, fiebre amarilla, malaria, encefalitis transmitidas por mosquitos, otras fiebres virales transmitidas por mosquitos |
| Triatomino | Chagas |
| Flebótomo | Leishmaniasis |
| Pulga | Peste |
| Piojo | Tifus epidémico |
| No especificado | Fiebres virales por artrópodos sin vector específico (p. ej. Oropouche) |

## Decisión 3. Eventos de mortalidad fuera de la tabla de hechos

**Problema.** `MORTALIDAD POR DENGUE` (56 filas, 57 defunciones) y `MORTALIDAD POR MALARIA` (1 fila, 1 defunción) guardan muertes en la misma columna donde
los demás eventos guardan casos. Sumarlos mezclaría unidades y, con la enfermedad armonizada «Dengue», contaminaría el denominador del porcentaje de dengue grave.

**Decisión.** No cargarlos. Permanecen en el archivo de origen y se mencionan en la documentación. La medida `casos` queda con una sola unidad.
Alternativa descartada: cargarlos con un atributo `tipo_registro`; obligaría a filtrar en cada consulta y no hay denominador comparable para calcular letalidad.

**Consecuencia.** El denominador del porcentaje de dengue grave es DENGUE + DENGUE GRAVE por construcción.

## Decisión 4. Periodos, año epidémico y años sin vigilancia

**Problema.** `dim_tiempo.periodo` (1996–2008, 2009–2019, 2020–2025, 2026) sirve para la serie de brotes, pero parte los 16 años de SIVIGILA en tres cortes sin sentido
para el análisis. Las vistas y conocimientos ya construidos usan 2007–2010, 2011–2016 y 2017–2022 y la marca de año epidémico, que el modelo nuevo no tenía.

**Decisión.** Agregar a `dim_tiempo`:

- `periodo_analisis`: 2007–2010, 2011–2016, 2017–2022 o «Fuera de 2007-2022». Es un corte de años, no de fuente.
- `tipo_anio_sivigila`: «Epidemico» si los casos ETV del año en SIVIGILA Colombia superan el promedio anual (79.334). Corresponde a 2010, 2013, 2014, 2015, 2016 y 2019.
  Fuera de 2007–2022 vale «No aplica».

Y a `dim_evento`: `anio_primer_registro`, el primer año con notificación en la fuente. Chagas empieza en 2012, chikungunya en 2014 y zika en 2015;
los años anteriores son «sin vigilancia», no «cero casos».

## Cifras de control

Con las cuatro decisiones, el modelo cargado debe dar:

| Control | Valor |
|---|---:|
| Filas en `fact_notificacion` | 241.451 (237.141 + 3.747 + 563) |
| Casos (suma de `casos`) | 1.278.124 (1.269.342 + 8.782) |
| Brotes (suma de `brotes`) | 563 |

Estas cifras son la base de las validaciones de la carga (`validaciones.json`).
