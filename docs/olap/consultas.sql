-- Consultas del analisis multidimensional (generadas por olap/consultas.py).
-- Los filtros de territorio excluyen 'Exterior' y 'Procedencia desconocida'.

-- OPERACION DRILL-DOWN: casos por departamento dentro de la region Andina
SELECT t.departamento AS departamento, SUM(f.casos) AS valor
FROM fact_notificacion f
JOIN dim_territorio t USING(territorio_key)
WHERE t.tipo_ubicacion IN ('Municipio','Sin municipio asignado') AND CAST(t.region_natural AS TEXT) IN ('Andina')
GROUP BY t.departamento;

-- OPERACION ROLL-UP: % de dengue grave por region (razon recalculada)
SELECT t.region_natural AS region, a.periodo AS periodo, 100.0*COALESCE(SUM(CASE WHEN e.evento='DENGUE GRAVE' THEN f.casos END),0)/NULLIF(SUM(CASE WHEN e.familia='Dengue' THEN f.casos END),0) AS valor, COALESCE(SUM(CASE WHEN e.evento='DENGUE GRAVE' THEN f.casos END),0) AS num, SUM(CASE WHEN e.familia='Dengue' THEN f.casos END) AS den
FROM fact_notificacion f
JOIN dim_evento e USING(evento_key)
JOIN dim_territorio t USING(territorio_key)
JOIN dim_anio a USING(anio_key)
WHERE t.tipo_ubicacion IN ('Municipio','Sin municipio asignado')
GROUP BY t.region_natural, a.periodo;

-- OPERACION SLICE: casos de chagas por region
SELECT t.region_natural AS region, SUM(f.casos) AS valor
FROM fact_notificacion f
JOIN dim_evento e USING(evento_key)
JOIN dim_territorio t USING(territorio_key)
WHERE t.tipo_ubicacion IN ('Municipio','Sin municipio asignado') AND CAST(e.evento AS TEXT) IN ('CHAGAS')
GROUP BY t.region_natural;

-- OPERACION DICE: Caribe x 2017-2022 x dengue, por departamento
SELECT t.departamento AS departamento, SUM(f.casos) AS valor
FROM fact_notificacion f
JOIN dim_evento e USING(evento_key)
JOIN dim_territorio t USING(territorio_key)
JOIN dim_anio a USING(anio_key)
WHERE t.tipo_ubicacion IN ('Municipio','Sin municipio asignado') AND CAST(t.region_natural AS TEXT) IN ('Caribe') AND CAST(a.periodo AS TEXT) IN ('2017-2022') AND CAST(e.evento AS TEXT) IN ('DENGUE')
GROUP BY t.departamento;

-- OPERACION PIVOT: region x evento (la matriz se transpone en la aplicacion)
SELECT t.region_natural AS region, e.evento AS evento, SUM(f.casos) AS valor
FROM fact_notificacion f
JOIN dim_evento e USING(evento_key)
JOIN dim_territorio t USING(territorio_key)
WHERE t.tipo_ubicacion IN ('Municipio','Sin municipio asignado')
GROUP BY t.region_natural, e.evento;

-- VISTA 1: concentracion por municipio y evento
SELECT t.municipio || ' (' || t.departamento || ')' AS municipio, e.evento AS evento, SUM(f.casos) AS valor
FROM fact_notificacion f
JOIN dim_evento e USING(evento_key)
JOIN dim_territorio t USING(territorio_key)
WHERE t.tipo_ubicacion IN ('Municipio','Sin municipio asignado')
GROUP BY t.municipio || ' (' || t.departamento || ')', e.evento;

-- VISTA 2: casos por departamento y anio
SELECT t.departamento AS departamento, f.anio_key AS anio, SUM(f.casos) AS valor
FROM fact_notificacion f
JOIN dim_territorio t USING(territorio_key)
WHERE t.tipo_ubicacion IN ('Municipio','Sin municipio asignado')
GROUP BY t.departamento, f.anio_key;

-- VISTA 2: casos por region y tipo de anio
SELECT t.region_natural AS region, a.tipo_anio AS tipo_anio, SUM(f.casos) AS valor
FROM fact_notificacion f
JOIN dim_territorio t USING(territorio_key)
JOIN dim_anio a USING(anio_key)
WHERE t.tipo_ubicacion IN ('Municipio','Sin municipio asignado')
GROUP BY t.region_natural, a.tipo_anio;

-- VISTA 3: casos por region, anio y trimestre (dengue, semanas 1-52); el indice se calcula normalizando cada anio
SELECT t.region_natural AS region, f.anio_key AS anio, s.trimestre AS trimestre, SUM(f.casos) AS valor
FROM fact_notificacion f
JOIN dim_evento e USING(evento_key)
JOIN dim_territorio t USING(territorio_key)
JOIN dim_semana s USING(semana_key)
WHERE t.tipo_ubicacion IN ('Municipio','Sin municipio asignado') AND f.semana_key <= 52 AND CAST(e.evento AS TEXT) IN ('DENGUE')
GROUP BY t.region_natural, f.anio_key, s.trimestre;

-- VISTA 4: % de dengue grave por departamento y periodo
SELECT t.departamento AS departamento, a.periodo AS periodo, 100.0*COALESCE(SUM(CASE WHEN e.evento='DENGUE GRAVE' THEN f.casos END),0)/NULLIF(SUM(CASE WHEN e.familia='Dengue' THEN f.casos END),0) AS valor, COALESCE(SUM(CASE WHEN e.evento='DENGUE GRAVE' THEN f.casos END),0) AS num, SUM(CASE WHEN e.familia='Dengue' THEN f.casos END) AS den
FROM fact_notificacion f
JOIN dim_evento e USING(evento_key)
JOIN dim_territorio t USING(territorio_key)
JOIN dim_anio a USING(anio_key)
WHERE t.tipo_ubicacion IN ('Municipio','Sin municipio asignado')
GROUP BY t.departamento, a.periodo;

-- VISTA 4: % de dengue grave por departamento y anio
SELECT t.departamento AS departamento, f.anio_key AS anio, 100.0*COALESCE(SUM(CASE WHEN e.evento='DENGUE GRAVE' THEN f.casos END),0)/NULLIF(SUM(CASE WHEN e.familia='Dengue' THEN f.casos END),0) AS valor, COALESCE(SUM(CASE WHEN e.evento='DENGUE GRAVE' THEN f.casos END),0) AS num, SUM(CASE WHEN e.familia='Dengue' THEN f.casos END) AS den
FROM fact_notificacion f
JOIN dim_evento e USING(evento_key)
JOIN dim_territorio t USING(territorio_key)
WHERE t.tipo_ubicacion IN ('Municipio','Sin municipio asignado')
GROUP BY t.departamento, f.anio_key;

-- VALIDACIONES (ver scripts/olap/cargar_modelo.py, funcion validar)
SELECT COUNT(*), COUNT(DISTINCT territorio_key) FROM dim_territorio;                 -- unicidad de claves
SELECT COUNT(*) FROM fact_notificacion f LEFT JOIN dim_evento d USING(evento_key)
 WHERE d.evento_key IS NULL;                                                          -- integridad referencial
SELECT COUNT(*) FROM (SELECT 1 FROM fact_notificacion
 GROUP BY evento_key, territorio_key, anio_key, semana_key HAVING COUNT(*)>1);         -- duplicados en el grano
SELECT SUM(casos), COUNT(*) FROM fact_notificacion;                                   -- coherencia con el CSV
