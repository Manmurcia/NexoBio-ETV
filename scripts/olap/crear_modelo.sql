-- =====================================================================
-- Modelo estrella NexoBio-ETV (SQLite) - Analisis multidimensional
-- 1 tabla de hechos (fact_notificacion) + 4 dimensiones
-- Decisiones de diseno: docs/olap/decisiones_modelo.md
-- =====================================================================
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS fact_notificacion;
DROP TABLE IF EXISTS dim_tiempo;
DROP TABLE IF EXISTS dim_territorio;
DROP TABLE IF EXISTS dim_evento;
DROP TABLE IF EXISTS dim_fuente;

-- ---------------------------------------------------------------------
-- DIMENSION TIEMPO. Jerarquia: periodo > anio > trimestre epidemiologico > semana
-- tiempo_key = anio * 100 + semana (semana 0 = registro anual, sin semana)
-- periodo          : cortes para series largas de brotes OMS (1996-2008, 2009-2019, 2020-2026)
-- periodo_analisis : cortes de las vistas SIVIGILA (2007-2022); es un corte de anios,
--                    por eso vale para cualquier fuente
-- tipo_anio_sivigila: 'Epidemico' si los casos ETV de SIVIGILA Colombia del anio superan
--                    el promedio anual de 2007-2022 (79.334); 'No aplica' fuera de ese rango
-- ---------------------------------------------------------------------
CREATE TABLE dim_tiempo (
    tiempo_key           INTEGER PRIMARY KEY,
    anio                 INTEGER NOT NULL,
    semana               INTEGER NOT NULL CHECK (semana BETWEEN 0 AND 53),
    trimestre_epi        INTEGER NOT NULL CHECK (trimestre_epi BETWEEN 0 AND 4),
    trimestre_epi_nombre TEXT    NOT NULL,       -- 'T1 (sem 1-13)', ..., 'Sin semana'
    periodo              TEXT    NOT NULL,       -- '1996-2008', '2009-2019', '2020-2026'
    periodo_analisis     TEXT    NOT NULL CHECK (periodo_analisis IN
                         ('2007-2010', '2011-2016', '2017-2022', 'Fuera de 2007-2022')),
    tipo_anio_sivigila   TEXT    NOT NULL CHECK (tipo_anio_sivigila IN
                         ('Epidemico', 'No epidemico', 'No aplica')),
    anio_completo        TEXT    NOT NULL CHECK (anio_completo IN ('Si', 'No')),
    UNIQUE (anio, semana),
    CHECK (tiempo_key = anio * 100 + semana)
);

-- ---------------------------------------------------------------------
-- DIMENSION TERRITORIO. Jerarquia: ambito > region > area > localidad
-- Colombia: Colombia > region natural > departamento > municipio
-- Mundo:    Mundo    > region OMS     > pais         > 'No aplica'
-- Categorias no geograficas de SIVIGILA (region = 'No geografico'):
--    area 'Exterior' (localidad = pais) y area 'Procedencia desconocida'.
-- 'Sin municipio asignado' es un municipio ficticio de un departamento real
--    (region natural normal); no es 'No geografico'.
-- OJO: 'area' mezcla departamentos y paises; agrupar siempre junto con 'ambito'.
-- ---------------------------------------------------------------------
CREATE TABLE dim_territorio (
    territorio_key    INTEGER PRIMARY KEY,
    ambito            TEXT NOT NULL CHECK (ambito IN ('Colombia', 'Mundo')),
    region            TEXT NOT NULL,             -- region natural / region OMS / 'Sin region' / 'No geografico'
    area              TEXT NOT NULL,             -- departamento / pais
    localidad         TEXT NOT NULL,             -- municipio / 'No aplica'
    codigo_territorio TEXT NOT NULL,             -- codigo DANE del municipio o nombre del pais
    cod_departamento  TEXT,                      -- solo Colombia
    subregion_onu     TEXT,                      -- solo Mundo (unsd_region)
    UNIQUE (ambito, codigo_territorio)
);

-- ---------------------------------------------------------------------
-- DIMENSION EVENTO. Jerarquia: enfermedad > evento
-- Solo eventos transmitidos por vectores (ETV). Los eventos de mortalidad
-- (defunciones, no casos) no se cargan en la tabla de hechos.
-- anio_primer_registro: primer anio con notificacion en la fuente; los anios
-- anteriores significan 'sin vigilancia', no 'cero casos'.
-- ---------------------------------------------------------------------
CREATE TABLE dim_evento (
    evento_key          INTEGER PRIMARY KEY,
    catalogo            TEXT NOT NULL CHECK (catalogo IN ('SIVIGILA', 'CIE-10 OMS')),
    cod_evento          TEXT,                    -- codigo SIVIGILA del evento
    evento              TEXT NOT NULL,           -- nombre original del evento o enfermedad
    enfermedad          TEXT NOT NULL,           -- armonizada entre catalogos
    cobertura           TEXT    NOT NULL CHECK (cobertura IN ('Nacional', 'Solo Cundinamarca', 'Global')),
    capitulo_cie10      TEXT,                    -- solo OMS (icd10n)
    anio_primer_registro INTEGER,
    UNIQUE (catalogo, evento, cobertura)
);

-- ---------------------------------------------------------------------
-- DIMENSION FUENTE. Jerarquia: escala > fuente
-- ---------------------------------------------------------------------
CREATE TABLE dim_fuente (
    fuente_key     INTEGER PRIMARY KEY,
    fuente         TEXT NOT NULL UNIQUE,
    escala         TEXT NOT NULL CHECK (escala IN ('Global', 'Nacional', 'Regional')),
    unidad_medida  TEXT NOT NULL CHECK (unidad_medida IN ('Casos notificados', 'Brotes reportados')),
    archivo_origen TEXT NOT NULL
);

-- ---------------------------------------------------------------------
-- TABLA DE HECHOS
-- Granularidad: notificacion municipal por semana epidemiologica (INS), o brote
-- reportado por pais y anio (OMS, semana 0). Casos y brotes son excluyentes.
-- Las coberturas SIVIGILA se solapan; las consultas deben filtrar una fuente
-- y nunca sumar ambas. Casos y brotes tampoco se suman entre si.
-- ---------------------------------------------------------------------
CREATE TABLE fact_notificacion (
    notificacion_id INTEGER PRIMARY KEY,
    tiempo_key      INTEGER NOT NULL REFERENCES dim_tiempo (tiempo_key),
    territorio_key  INTEGER NOT NULL REFERENCES dim_territorio (territorio_key),
    evento_key      INTEGER NOT NULL REFERENCES dim_evento (evento_key),
    fuente_key      INTEGER NOT NULL REFERENCES dim_fuente (fuente_key),
    id_brote        TEXT    NOT NULL DEFAULT '',   -- id_outbreak; '' en vigilancia
    casos           INTEGER CHECK (casos IS NULL OR casos >= 1),
    brotes          INTEGER CHECK (brotes IS NULL OR brotes = 1),
    CHECK ((casos IS NOT NULL AND brotes IS NULL) OR (casos IS NULL AND brotes IS NOT NULL)),
    UNIQUE (fuente_key, tiempo_key, territorio_key, evento_key, id_brote)
);

CREATE INDEX ix_fact_tiempo     ON fact_notificacion (tiempo_key);
CREATE INDEX ix_fact_territorio ON fact_notificacion (territorio_key);
CREATE INDEX ix_fact_evento     ON fact_notificacion (evento_key);
CREATE INDEX ix_fact_fuente     ON fact_notificacion (fuente_key);
