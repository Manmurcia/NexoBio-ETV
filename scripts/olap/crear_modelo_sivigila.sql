-- ============================================================================
-- Modelo operativo SIVIGILA NexoBio-ETV (analisis interactivos actuales)
-- Motor: SQLite 3.  Tabla de hechos: fact_notificacion
-- Granularidad: un registro = casos notificados de UN evento, en UN municipio,
--               en UNA semana epidemiologica de UN anio.
-- ============================================================================
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS fact_notificacion;
DROP TABLE IF EXISTS dim_evento;
DROP TABLE IF EXISTS dim_territorio;
DROP TABLE IF EXISTS dim_anio;
DROP TABLE IF EXISTS dim_semana;

-- Dimension evento. Jerarquia: vector -> familia -> evento
CREATE TABLE dim_evento (
    evento_key   INTEGER PRIMARY KEY,
    cod_evento   INTEGER NOT NULL UNIQUE,      -- cod_eve del INS/SIVIGILA
    evento       TEXT    NOT NULL UNIQUE,
    familia      TEXT    NOT NULL,             -- Dengue | Chikungunya | Chagas
    vector       TEXT    NOT NULL              -- Aedes | Triatominos
);

-- Dimension territorio. Jerarquia: region_natural -> departamento -> municipio
CREATE TABLE dim_territorio (
    territorio_key   INTEGER PRIMARY KEY,
    cod_municipio    INTEGER NOT NULL UNIQUE,
    municipio        TEXT    NOT NULL,
    cod_departamento INTEGER NOT NULL,
    departamento     TEXT    NOT NULL,
    region_natural   TEXT    NOT NULL,         -- 'No aplica' para exterior / desconocido
    tipo_ubicacion   TEXT    NOT NULL CHECK (tipo_ubicacion IN
                     ('Municipio','Sin municipio asignado','Exterior','Procedencia desconocida'))
);

-- Dimension anio. Jerarquia: periodo -> anio
CREATE TABLE dim_anio (
    anio_key   INTEGER PRIMARY KEY,            -- = anio
    periodo    TEXT NOT NULL,                  -- 2007-2010 | 2011-2016 | 2017-2022
    tipo_anio  TEXT NOT NULL CHECK (tipo_anio IN ('Epidemico','No epidemico'))
);

-- Dimension semana epidemiologica. Jerarquia: trimestre epidemiologico -> semana
CREATE TABLE dim_semana (
    semana_key     INTEGER PRIMARY KEY,        -- = semana (1..53)
    trimestre_epi  INTEGER NOT NULL CHECK (trimestre_epi BETWEEN 1 AND 4),
    trimestre      TEXT    NOT NULL            -- 'T1 (sem 1-13)', ...
);

CREATE TABLE fact_notificacion (
    evento_key     INTEGER NOT NULL REFERENCES dim_evento(evento_key),
    territorio_key INTEGER NOT NULL REFERENCES dim_territorio(territorio_key),
    anio_key       INTEGER NOT NULL REFERENCES dim_anio(anio_key),
    semana_key     INTEGER NOT NULL REFERENCES dim_semana(semana_key),
    casos          INTEGER NOT NULL CHECK (casos > 0),   -- medida aditiva
    PRIMARY KEY (evento_key, territorio_key, anio_key, semana_key)
) WITHOUT ROWID;

CREATE INDEX ix_fact_territorio ON fact_notificacion (territorio_key);
CREATE INDEX ix_fact_anio       ON fact_notificacion (anio_key);
CREATE INDEX ix_fact_semana     ON fact_notificacion (semana_key);
