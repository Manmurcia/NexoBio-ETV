-- =====================================================================
-- Modelo estrella NexoBio-ETV (SQLite) - Analisis multidimensional
-- 1 tabla de hechos (fact_notificacion) + 4 dimensiones
-- =====================================================================
PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- DIMENSION TIEMPO. Jerarquia: periodo > anio > trimestre epidemiologico > semana
-- tiempo_key = anio * 100 + semana (semana 0 = registro anual, sin semana)
-- ---------------------------------------------------------------------
CREATE TABLE dim_tiempo (
    tiempo_key           INTEGER PRIMARY KEY,
    anio                 INTEGER NOT NULL,
    semana               INTEGER NOT NULL CHECK (semana BETWEEN 0 AND 53),
    trimestre_epi        INTEGER NOT NULL CHECK (trimestre_epi BETWEEN 0 AND 4),
    trimestre_epi_nombre TEXT    NOT NULL,       -- 'T1 (sem. 1-13)', ..., 'Sin semana'
    periodo              TEXT    NOT NULL,       -- '1996-2008', '2009-2019', '2020-2025', '2026 (incompleto)'
    anio_completo        TEXT    NOT NULL CHECK (anio_completo IN ('Si', 'No')),
    UNIQUE (anio, semana),
    CHECK (tiempo_key = anio * 100 + semana)
);

-- ---------------------------------------------------------------------
-- DIMENSION TERRITORIO. Jerarquia: ambito > region > area > localidad
-- Colombia: Colombia > region natural > departamento > municipio
-- Mundo:    Mundo    > region OMS     > pais         > 'No aplica'
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
-- DIMENSION EVENTO. Jerarquia: grupo > enfermedad > evento
-- ---------------------------------------------------------------------
CREATE TABLE dim_evento (
    evento_key     INTEGER PRIMARY KEY,
    catalogo       TEXT NOT NULL CHECK (catalogo IN ('SIVIGILA', 'CIE-10 OMS')),
    cod_evento     TEXT,                         -- codigo SIVIGILA del evento
    evento         TEXT NOT NULL,                -- nombre original del evento o enfermedad
    enfermedad     TEXT NOT NULL,                -- armonizada entre catalogos
    grupo          TEXT NOT NULL CHECK (grupo IN ('ETV', 'No ETV')),
    cobertura      TEXT NOT NULL CHECK (cobertura IN ('Nacional', 'Solo Cundinamarca', 'Global')),
    capitulo_cie10 TEXT,                         -- solo OMS (icd10n)
    UNIQUE (catalogo, evento)
);

-- ---------------------------------------------------------------------
-- DIMENSION FUENTE. Jerarquia: escala > fuente
-- ---------------------------------------------------------------------
CREATE TABLE dim_fuente (
    fuente_key     INTEGER PRIMARY KEY,
    fuente         TEXT NOT NULL UNIQUE,
    escala         TEXT NOT NULL CHECK (escala IN ('Global', 'Nacional', 'Regional')),
    unidad_medida  TEXT NOT NULL,                -- casos notificados / brotes reportados
    archivo_origen TEXT NOT NULL
);

-- ---------------------------------------------------------------------
-- TABLA DE HECHOS
-- Granularidad: notificacion municipal por semana epidemiologica (INS), o brote
-- reportado por pais y anio (OMS, semana 0). Casos y brotes son excluyentes.
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
