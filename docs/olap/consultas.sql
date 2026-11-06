-- Consultas del analisis multidimensional (generadas por olap/consultas.py).
-- Los analisis de casos seleccionan una fuente SIVIGILA; los brotes OMS/HDX se consultan aparte.

-- OPERACION DRILL-DOWN: casos por departamento dentro de la region Andina
SELECT t.area AS departamento, SUM(f.casos) AS valor
FROM fact_notificacion f
JOIN dim_territorio t USING(territorio_key)
JOIN dim_fuente u USING(fuente_key)
WHERE t.ambito='Colombia' AND t.localidad<>'No aplica' AND u.fuente = 'SIVIGILA Colombia' AND CAST(t.region AS TEXT) IN ('Andina')
GROUP BY t.area;

-- OPERACION ROLL-UP: % de dengue grave por region (razon recalculada)
SELECT t.region AS region, a.periodo_analisis AS periodo, 100.0*COALESCE(SUM(CASE WHEN e.evento='DENGUE GRAVE' THEN f.casos END),0)/NULLIF(SUM(CASE WHEN e.enfermedad='Dengue' THEN f.casos END),0) AS valor, COALESCE(SUM(CASE WHEN e.evento='DENGUE GRAVE' THEN f.casos END),0) AS num, SUM(CASE WHEN e.enfermedad='Dengue' THEN f.casos END) AS den
FROM fact_notificacion f
JOIN dim_evento e USING(evento_key)
JOIN dim_territorio t USING(territorio_key)
JOIN dim_tiempo a ON f.tiempo_key=a.tiempo_key
JOIN dim_fuente u USING(fuente_key)
WHERE t.ambito='Colombia' AND t.localidad<>'No aplica' AND u.fuente = 'SIVIGILA Colombia'
GROUP BY t.region, a.periodo_analisis;

-- OPERACION SLICE: casos de chagas por region
SELECT t.region AS region, SUM(f.casos) AS valor
FROM fact_notificacion f
JOIN dim_evento e USING(evento_key)
JOIN dim_territorio t USING(territorio_key)
JOIN dim_fuente u USING(fuente_key)
WHERE t.ambito='Colombia' AND t.localidad<>'No aplica' AND u.fuente = 'SIVIGILA Colombia' AND CAST(e.evento AS TEXT) IN ('CHAGAS')
GROUP BY t.region;

-- OPERACION DICE: Caribe x 2017-2022 x dengue, por departamento
SELECT t.area AS departamento, SUM(f.casos) AS valor
FROM fact_notificacion f
JOIN dim_evento e USING(evento_key)
JOIN dim_territorio t USING(territorio_key)
JOIN dim_tiempo a ON f.tiempo_key=a.tiempo_key
JOIN dim_fuente u USING(fuente_key)
WHERE t.ambito='Colombia' AND t.localidad<>'No aplica' AND u.fuente = 'SIVIGILA Colombia' AND CAST(t.region AS TEXT) IN ('Caribe') AND CAST(a.periodo_analisis AS TEXT) IN ('2017-2022') AND CAST(e.evento AS TEXT) IN ('DENGUE')
GROUP BY t.area;

-- OPERACION PIVOT: region x evento (la matriz se transpone en la aplicacion)
SELECT t.region AS region, e.evento AS evento, SUM(f.casos) AS valor
FROM fact_notificacion f
JOIN dim_evento e USING(evento_key)
JOIN dim_territorio t USING(territorio_key)
JOIN dim_fuente u USING(fuente_key)
WHERE t.ambito='Colombia' AND t.localidad<>'No aplica' AND u.fuente = 'SIVIGILA Colombia'
GROUP BY t.region, e.evento;

-- VISTA 1: composición porcentual por fuente, enfermedad común y periodo.
-- El denominador usa la medida propia de cada fuente y solo Dengue + Chikungunya.
WITH composicion AS ( SELECT u.fuente, u.escala, t.ambito, e.enfermedad, SUM(CASE WHEN u.fuente = 'OMS/HDX' THEN f.brotes ELSE f.casos END) AS medida
FROM fact_notificacion f
JOIN dim_fuente u USING (fuente_key)
JOIN dim_evento e USING (evento_key)
JOIN dim_tiempo d USING (tiempo_key)
JOIN dim_territorio t USING (territorio_key)
WHERE u.fuente IN ('SIVIGILA Colombia', 'SIVIGILA Cundinamarca', 'OMS/HDX') AND e.enfermedad IN ('Dengue', 'Chikungunya') AND d.anio BETWEEN 2007 AND 2022 AND t.region <> 'No geografico'
GROUP BY u.fuente, u.escala, t.ambito, e.enfermedad ) SELECT fuente, escala, ambito, enfermedad, 100.0 * medida / NULLIF(SUM(medida) OVER (PARTITION BY fuente), 0) AS porcentaje
FROM composicion ORDER BY escala, fuente, enfermedad;

-- VISTA 2: casos por departamento y anio
SELECT t.area AS departamento, a.anio AS anio, SUM(f.casos) AS valor
FROM fact_notificacion f
JOIN dim_territorio t USING(territorio_key)
JOIN dim_tiempo a ON f.tiempo_key=a.tiempo_key
JOIN dim_fuente u USING(fuente_key)
WHERE t.ambito='Colombia' AND t.localidad<>'No aplica' AND u.fuente = 'SIVIGILA Colombia'
GROUP BY t.area, a.anio;

-- VISTA 2: casos por region y tipo de anio
SELECT t.region AS region, a.tipo_anio_sivigila AS tipo_anio, SUM(f.casos) AS valor
FROM fact_notificacion f
JOIN dim_territorio t USING(territorio_key)
JOIN dim_tiempo a ON f.tiempo_key=a.tiempo_key
JOIN dim_fuente u USING(fuente_key)
WHERE t.ambito='Colombia' AND t.localidad<>'No aplica' AND u.fuente = 'SIVIGILA Colombia'
GROUP BY t.region, a.tipo_anio_sivigila;

-- VISTA 3: casos por region, anio y trimestre (dengue, semanas 1-52); el indice se calcula normalizando cada anio
SELECT t.region AS region, a.anio AS anio, a.trimestre_epi_nombre AS trimestre, SUM(f.casos) AS valor
FROM fact_notificacion f
JOIN dim_evento e USING(evento_key)
JOIN dim_territorio t USING(territorio_key)
JOIN dim_tiempo a ON f.tiempo_key=a.tiempo_key
JOIN dim_fuente u USING(fuente_key)
WHERE t.ambito='Colombia' AND t.localidad<>'No aplica' AND a.semana > 0 AND a.semana <= 52 AND u.fuente = 'SIVIGILA Colombia' AND CAST(e.evento AS TEXT) IN ('DENGUE')
GROUP BY t.region, a.anio, a.trimestre_epi_nombre;

-- VISTA 4: % de dengue grave por departamento y periodo
SELECT t.area AS departamento, a.periodo_analisis AS periodo, 100.0*COALESCE(SUM(CASE WHEN e.evento='DENGUE GRAVE' THEN f.casos END),0)/NULLIF(SUM(CASE WHEN e.enfermedad='Dengue' THEN f.casos END),0) AS valor, COALESCE(SUM(CASE WHEN e.evento='DENGUE GRAVE' THEN f.casos END),0) AS num, SUM(CASE WHEN e.enfermedad='Dengue' THEN f.casos END) AS den
FROM fact_notificacion f
JOIN dim_evento e USING(evento_key)
JOIN dim_territorio t USING(territorio_key)
JOIN dim_tiempo a ON f.tiempo_key=a.tiempo_key
JOIN dim_fuente u USING(fuente_key)
WHERE t.ambito='Colombia' AND t.localidad<>'No aplica' AND u.fuente = 'SIVIGILA Colombia'
GROUP BY t.area, a.periodo_analisis;

-- VISTA 4: % de dengue grave por departamento y anio
SELECT t.area AS departamento, a.anio AS anio, 100.0*COALESCE(SUM(CASE WHEN e.evento='DENGUE GRAVE' THEN f.casos END),0)/NULLIF(SUM(CASE WHEN e.enfermedad='Dengue' THEN f.casos END),0) AS valor, COALESCE(SUM(CASE WHEN e.evento='DENGUE GRAVE' THEN f.casos END),0) AS num, SUM(CASE WHEN e.enfermedad='Dengue' THEN f.casos END) AS den
FROM fact_notificacion f
JOIN dim_evento e USING(evento_key)
JOIN dim_territorio t USING(territorio_key)
JOIN dim_tiempo a ON f.tiempo_key=a.tiempo_key
JOIN dim_fuente u USING(fuente_key)
WHERE t.ambito='Colombia' AND t.localidad<>'No aplica' AND u.fuente = 'SIVIGILA Colombia'
GROUP BY t.area, a.anio;

-- VISTA 4: Cundinamarca anual por departamento y periodo
SELECT t.area AS departamento, a.periodo_analisis AS periodo, SUM(f.casos) AS valor
FROM fact_notificacion f
JOIN dim_territorio t USING(territorio_key)
JOIN dim_tiempo a ON f.tiempo_key=a.tiempo_key
JOIN dim_fuente u USING(fuente_key)
WHERE t.ambito='Colombia' AND t.localidad<>'No aplica' AND u.fuente = 'SIVIGILA Cundinamarca'
GROUP BY t.area, a.periodo_analisis;

-- VISTA 5: brotes OMS/HDX por region OMS
SELECT t.region, SUM(f.brotes) AS brotes_reportados
FROM fact_notificacion f
JOIN dim_territorio t USING(territorio_key)
JOIN dim_fuente u USING(fuente_key)
WHERE u.fuente = 'OMS/HDX'
GROUP BY t.region
ORDER BY brotes_reportados DESC;

-- VALIDACIONES (scripts/olap/cargar_modelo.py, funcion validar)
SELECT COUNT(*), COUNT(DISTINCT tiempo_key) FROM dim_tiempo;
SELECT COUNT(*) FROM fact_notificacion f LEFT JOIN dim_tiempo d USING(tiempo_key) WHERE d.tiempo_key IS NULL;
SELECT COUNT(*) FROM fact_notificacion f LEFT JOIN dim_territorio d USING(territorio_key) WHERE d.territorio_key IS NULL;
SELECT COUNT(*) FROM fact_notificacion f LEFT JOIN dim_evento d USING(evento_key) WHERE d.evento_key IS NULL;
SELECT COUNT(*) FROM fact_notificacion f LEFT JOIN dim_fuente d USING(fuente_key) WHERE d.fuente_key IS NULL;
SELECT COUNT(*) FROM (
    SELECT 1 FROM fact_notificacion
    GROUP BY fuente_key, tiempo_key, territorio_key, evento_key, id_brote HAVING COUNT(*) > 1
);
SELECT u.fuente, COUNT(*) AS filas, SUM(f.casos) AS casos, SUM(f.brotes) AS brotes
FROM fact_notificacion f JOIN dim_fuente u USING(fuente_key)
GROUP BY u.fuente;
