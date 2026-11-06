-- Modelo estrella NexoBio-ETV (SQLite), consolidado de tres fuentes.
PRAGMA foreign_keys = ON;

CREATE TABLE dim_tiempo (
    tiempo_key            INTEGER PRIMARY KEY,
    anio                  INTEGER NOT NULL,
    semana                INTEGER NOT NULL CHECK (semana BETWEEN 0 AND 53),
    trimestre_epi         INTEGER NOT NULL CHECK (trimestre_epi BETWEEN 0 AND 4),
    trimestre_epi_nombre  TEXT NOT NULL,
    periodo               TEXT NOT NULL,
    periodo_analisis      TEXT NOT NULL,
    tipo_anio_sivigila    TEXT NOT NULL CHECK (tipo_anio_sivigila IN
                          ('Epidemico', 'No epidemico', 'No aplica')),
    anio_completo         TEXT NOT NULL CHECK (anio_completo IN ('Si', 'No')),
    UNIQUE (anio, semana),
    CHECK (tiempo_key = anio * 100 + semana)
);

CREATE TABLE dim_territorio (
    territorio_key    INTEGER PRIMARY KEY,
    ambito            TEXT NOT NULL CHECK (ambito IN ('Colombia', 'Mundo')),
    region            TEXT NOT NULL,
    area              TEXT NOT NULL,
    localidad         TEXT NOT NULL,
    codigo_territorio TEXT NOT NULL,
    cod_departamento  TEXT,
    subregion_onu     TEXT,
    UNIQUE (ambito, codigo_territorio)
);

CREATE TABLE dim_evento (
    evento_key          INTEGER PRIMARY KEY,
    catalogo            TEXT NOT NULL CHECK (catalogo IN ('SIVIGILA', 'CIE-10 OMS')),
    cod_evento          TEXT,
    evento              TEXT NOT NULL,
    enfermedad          TEXT NOT NULL,
    vector              TEXT NOT NULL,
    cobertura           TEXT NOT NULL CHECK (cobertura IN
                        ('Nacional', 'Solo Cundinamarca', 'Global')),
    capitulo_cie10      TEXT,
    anio_primer_registro INTEGER NOT NULL,
    UNIQUE (catalogo, evento, cobertura)
);

CREATE TABLE dim_fuente (
    fuente_key     INTEGER PRIMARY KEY,
    fuente         TEXT NOT NULL UNIQUE,
    escala         TEXT NOT NULL CHECK (escala IN ('Global', 'Nacional', 'Regional')),
    unidad_medida  TEXT NOT NULL,
    archivo_origen TEXT NOT NULL
);

CREATE TABLE fact_notificacion (
    notificacion_id INTEGER PRIMARY KEY,
    tiempo_key      INTEGER NOT NULL REFERENCES dim_tiempo (tiempo_key),
    territorio_key  INTEGER NOT NULL REFERENCES dim_territorio (territorio_key),
    evento_key      INTEGER NOT NULL REFERENCES dim_evento (evento_key),
    fuente_key      INTEGER NOT NULL REFERENCES dim_fuente (fuente_key),
    id_brote        TEXT NOT NULL DEFAULT '',
    casos           INTEGER CHECK (casos IS NULL OR casos >= 1),
    brotes          INTEGER CHECK (brotes IS NULL OR brotes = 1),
    CHECK ((casos IS NOT NULL AND brotes IS NULL) OR
           (casos IS NULL AND brotes IS NOT NULL)),
    UNIQUE (fuente_key, tiempo_key, territorio_key, evento_key, id_brote)
);

CREATE INDEX ix_fact_tiempo     ON fact_notificacion (tiempo_key);
CREATE INDEX ix_fact_territorio ON fact_notificacion (territorio_key);
CREATE INDEX ix_fact_evento     ON fact_notificacion (evento_key);
CREATE INDEX ix_fact_fuente     ON fact_notificacion (fuente_key);
