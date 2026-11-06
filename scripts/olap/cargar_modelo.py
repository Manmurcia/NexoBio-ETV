"""Construye y valida el modelo estrella multifuente de la Etapa 5."""
import json
import os
import sqlite3
import sys
import tempfile

import pandas as pd

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATOS = os.path.join(RAIZ, "datos")
CONSOLIDACION = os.path.join(RAIZ, "consolidacion")
DB = os.path.join(RAIZ, "olap", "nexobio_olap.db")
SQL = os.path.join(RAIZ, "scripts", "olap", "crear_modelo.sql")
VALIDACIONES = os.path.join(RAIZ, "olap", "validaciones.json")

ARCHIVOS = {
    "nacional": "Datos_de_Vigilancia_ColombiaCompleto_Limpio.csv",
    "regional": "regional_cundinamarca_etv.csv",
    "global": "global_brotes_etv.csv",
}
FUENTES = [
    ("SIVIGILA Colombia", "Nacional", "casos notificados", ARCHIVOS["nacional"]),
    ("SIVIGILA Cundinamarca", "Regional", "casos notificados", ARCHIVOS["regional"]),
    ("OMS/HDX", "Global", "brotes reportados", ARCHIVOS["global"]),
]

REGION_NATURAL = {}
for region, codigos in {
    "Andina": [5, 11, 15, 17, 25, 41, 54, 63, 66, 68, 73],
    "Caribe": [8, 13, 20, 23, 44, 47, 70],
    "Pacifica": [19, 27, 52, 76],
    "Orinoquia": [50, 81, 85, 99],
    "Amazonia": [18, 86, 91, 94, 95, 97],
    "Insular": [88],
}.items():
    REGION_NATURAL.update({str(codigo): region for codigo in codigos})

VECTOR_NACIONAL = {
    "DENGUE": "Aedes",
    "DENGUE GRAVE": "Aedes",
    "CHIKUNGUNYA": "Aedes",
    "CHAGAS": "Triatominos",
}
VECTOR_GLOBAL = {
    "Dengue": "Aedes",
    "Yellow fever": "Aedes",
    "Other mosquito-borne viral fevers": "Mosquitos",
    "Mosquito-borne viral encephalitis": "Mosquitos",
    "Plasmodium falciparum malaria": "Anopheles",
    "Plasmodium vivax malaria": "Anopheles",
    "Unspecified malaria": "Anopheles",
    "Leishmaniasis": "Flebotominos",
    "Plague": "Pulgas",
    "Typhus fever": "No especificado",
    "Other arthropod-borne viral fevers, not elsewhere classified": "Artrópodos",
}
PERIODOS_ANALISIS = [
    (2007, 2010, "2007-2010"),
    (2011, 2016, "2011-2016"),
    (2017, 2022, "2017-2022"),
]


def _texto(valor, predeterminado=""):
    if pd.isna(valor):
        return predeterminado
    return str(valor).strip()


def _codigo(valor):
    if pd.isna(valor):
        raise ValueError("Se encontró un código territorial vacío.")
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor).strip()


def _periodo_analisis(anio):
    for inicio, fin, periodo in PERIODOS_ANALISIS:
        if inicio <= anio <= fin:
            return periodo
    if anio < 2007:
        return "Anterior a 2007"
    return "Posterior a 2022"


def _periodo_oms(anio):
    if anio <= 2008:
        return "1996-2008"
    if anio <= 2019:
        return "2009-2019"
    return "2020-2026"


def _trimestre(semana):
    if semana == 0:
        return 0, "Sin semana"
    trimestre = min((semana - 1) // 13 + 1, 4)
    inicio = (trimestre - 1) * 13 + 1
    fin = 53 if trimestre == 4 else trimestre * 13
    return trimestre, f"T{trimestre} (sem. {inicio}-{fin})"


def _periodo_y_tipo_anio(src_nacional):
    por_anio = src_nacional.groupby("ano").conteo.sum()
    promedio = float(por_anio.mean())
    tipo = {
        int(anio): ("Epidemico" if casos > promedio else "No epidemico")
        for anio, casos in por_anio.items()
    }
    return tipo, promedio


def _cargar_fuentes():
    archivos = {
        nombre: os.path.join(CONSOLIDACION if nombre in ("regional", "global") else DATOS, archivo)
        for nombre, archivo in ARCHIVOS.items()
    }
    faltantes = [ruta for ruta in archivos.values() if not os.path.isfile(ruta)]
    if faltantes:
        raise FileNotFoundError("No se encontraron fuentes requeridas: " + ", ".join(faltantes))

    nacional = pd.read_csv(archivos["nacional"], encoding="utf-8-sig")
    regional = pd.read_csv(archivos["regional"], encoding="utf-8-sig")
    global_oms = pd.read_csv(archivos["global"], encoding="utf-8-sig")
    clasif_siv = pd.read_csv(os.path.join(DATOS, "clasificacion_evento_vigilancia.csv"), encoding="utf-8-sig")
    clasif_hdx = pd.read_csv(os.path.join(DATOS, "clasificacion_enfermedad_hdx.csv"), encoding="utf-8-sig")
    departamentos = pd.read_csv(os.path.join(DATOS, "dim_departamento.csv"), encoding="utf-8-sig")

    grupos_siv = dict(zip(clasif_siv.nombre_evento, clasif_siv.grupo_evento))
    eventos_siv = set(nacional.nombre_evento.dropna()) | set(regional.evento.dropna())
    no_clasificados = eventos_siv - set(grupos_siv)
    if no_clasificados:
        raise ValueError(f"Eventos SIVIGILA sin clasificación: {sorted(no_clasificados)}")
    no_etv = {evento for evento in eventos_siv if grupos_siv[evento] != "ETV"}
    eventos_sin_vector = no_etv | (eventos_siv - set(VECTOR_NACIONAL))
    if eventos_sin_vector:
        raise ValueError(f"Eventos fuera del alcance ETV o sin vector: {sorted(eventos_sin_vector)}")

    mapa_hdx = dict(zip(clasif_hdx.icd103n, clasif_hdx.es_etv.astype(str).str.strip().str.lower()))
    sin_clasificar_hdx = set(global_oms.icd103n.dropna()) - set(mapa_hdx)
    if sin_clasificar_hdx:
        raise ValueError(f"Enfermedades OMS/HDX sin clasificación: {sorted(sin_clasificar_hdx)}")
    global_oms = global_oms[
        global_oms.icd103n.map(mapa_hdx).isin(("si", "sí", "yes", "true", "1"))
    ].copy()
    if global_oms.id_outbreak.isna().any():
        raise ValueError("La fuente OMS/HDX contiene brotes sin id_outbreak.")
    if global_oms.id_outbreak.duplicated().any():
        raise ValueError("La fuente OMS/HDX contiene id_outbreak duplicados.")

    return nacional, regional, global_oms, departamentos


def _construir_dimensiones(src_nacional, src_regional, src_global, departamentos):
    tipo_anio, promedio = _periodo_y_tipo_anio(src_nacional)

    fuente_ids = {nombre: i for i, (nombre, *_resto) in enumerate(FUENTES, start=1)}
    dim_fuente = pd.DataFrame([
        {
            "fuente_key": fuente_ids[nombre],
            "fuente": nombre,
            "escala": escala,
            "unidad_medida": unidad,
            "archivo_origen": archivo,
        }
        for nombre, escala, unidad, archivo in FUENTES
    ])

    # Las dimensiones de evento distinguen la cobertura para no confundir el dato
    # nacional con el subconjunto regional que se utiliza para contrastes.
    eventos = {}

    codigos_siv = (
        src_nacional[["cod_eve", "nombre_evento", "ano"]]
        .groupby("nombre_evento", as_index=False)
        .agg(cod_evento=("cod_eve", "first"), anio_primer_registro=("ano", "min"))
    )
    codigo_por_evento = {
        fila.nombre_evento: _codigo(fila.cod_evento) for fila in codigos_siv.itertuples()
    }
    primer_anio_siv = {
        fila.nombre_evento: int(fila.anio_primer_registro) for fila in codigos_siv.itertuples()
    }
    for evento in sorted(set(src_nacional.nombre_evento) | set(src_regional.evento)):
        enfermedad = {
            "DENGUE": "Dengue",
            "DENGUE GRAVE": "Dengue",
            "CHIKUNGUNYA": "Chikungunya",
            "CHAGAS": "Chagas",
        }[evento]
        for cobertura in ("Nacional", "Solo Cundinamarca"):
            eventos[("SIVIGILA", evento, cobertura)] = {
                "catalogo": "SIVIGILA",
                "cod_evento": codigo_por_evento.get(evento),
                "evento": evento,
                "enfermedad": enfermedad,
                "vector": VECTOR_NACIONAL[evento],
                "cobertura": cobertura,
                "capitulo_cie10": None,
                "anio_primer_registro": primer_anio_siv[evento],
            }

    clasif_hdx = pd.read_csv(os.path.join(DATOS, "clasificacion_enfermedad_hdx.csv"), encoding="utf-8-sig")
    etv_hdx = set(
        clasif_hdx.loc[
            clasif_hdx.es_etv.astype(str).str.strip().str.lower().isin(("si", "sí", "yes", "true", "1")),
            "icd103n",
        ]
    )
    for (nombre_evento, enfermedad, capitulo), grupo in src_global.groupby(
        ["icd104n", "icd103n", "icd10n"], dropna=False
    ):
        if enfermedad not in etv_hdx:
            continue
        vector = VECTOR_GLOBAL.get(enfermedad, "No especificado")
        key = ("CIE-10 OMS", _texto(nombre_evento), "Global")
        eventos[key] = {
            "catalogo": "CIE-10 OMS",
            "cod_evento": _texto(grupo.icd104c.iloc[0]) or None,
            "evento": _texto(nombre_evento),
            "enfermedad": _texto(enfermedad),
            "vector": vector,
            "cobertura": "Global",
            "capitulo_cie10": _texto(capitulo) or None,
            "anio_primer_registro": int(grupo.Year.min()),
        }

    dim_evento = pd.DataFrame([
        {"evento_key": i, **eventos[key]}
        for i, key in enumerate(sorted(eventos), start=1)
    ])
    evento_ids = {
        (row.catalogo, row.evento, row.cobertura): int(row.evento_key)
        for row in dim_evento.itertuples()
    }

    dep_nombre = {
        _codigo(row.cod_dpto_o): _texto(row.nombre_mostrar)
        for row in departamentos.itertuples()
    }
    territorios = {}

    def agregar_territorio_colombia(codigo, municipio, cod_departamento, departamento):
        codigo = _codigo(codigo)
        cod_departamento = _codigo(cod_departamento)
        municipio = _texto(municipio).replace("*", "").strip()
        if cod_departamento == "0":
            area, localidad, region = "Procedencia desconocida", "No aplica", "No geografico"
        elif cod_departamento == "1":
            area, localidad, region = "Exterior", "No aplica", "No geografico"
        else:
            area = dep_nombre.get(cod_departamento, _texto(departamento, "Sin departamento"))
            if "SIN MUNICIPIO" in municipio.upper() or codigo == "25000":
                localidad = "Sin municipio asignado"
            else:
                localidad = municipio
            region = REGION_NATURAL.get(cod_departamento, "Sin region")
        key = ("Colombia", codigo)
        row = {
            "ambito": "Colombia",
            "region": region,
            "area": area,
            "localidad": localidad,
            "codigo_territorio": codigo,
            "cod_departamento": cod_departamento,
            "subregion_onu": None,
        }
        anterior = territorios.get(key)
        if anterior and anterior != row:
            # La fuente nacional es la referencia de nombres cuando ambas fuentes
            # describen el mismo municipio.
            if anterior["localidad"] != "Sin municipio asignado":
                return
        territorios[key] = row

    for row in src_nacional[["cod_mun_o", "municipio_ocurrencia", "cod_dpto_o", "departamento_ocurrencia"]].drop_duplicates().itertuples(index=False):
        agregar_territorio_colombia(*row)
    for row in src_regional[["cod_municipio", "municipio", "anio"]].drop_duplicates("cod_municipio").itertuples(index=False):
        agregar_territorio_colombia(row.cod_municipio, row.municipio, 25, "CUNDINAMARCA")

    for row in src_global[["iso3", "Country", "who_region", "unsd_subregion"]].drop_duplicates("iso3").itertuples(index=False):
        codigo = _texto(row.iso3).upper()
        if not codigo:
            raise ValueError(f"País OMS/HDX sin código ISO3: {row.Country}")
        key = ("Mundo", codigo)
        territorio = {
            "ambito": "Mundo",
            "region": _texto(row.who_region, "Sin region OMS") or "Sin region OMS",
            "area": _texto(row.Country, "Pais sin nombre"),
            "localidad": "No aplica",
            "codigo_territorio": codigo,
            "cod_departamento": None,
            "subregion_onu": _texto(row.unsd_subregion) or None,
        }
        if key in territorios and territorios[key] != territorio:
            raise ValueError(f"El codigo de territorio {codigo} tiene geografia OMS inconsistente.")
        territorios[key] = territorio

    dim_territorio = pd.DataFrame([
        {"territorio_key": i, **territorios[key]}
        for i, key in enumerate(sorted(territorios), start=1)
    ])
    territorio_ids = {
        (row.ambito, row.codigo_territorio): int(row.territorio_key)
        for row in dim_territorio.itertuples()
    }

    tiempos = set()
    tiempos.update((int(anio), int(semana)) for anio, semana in zip(src_nacional.ano, src_nacional.semana))
    tiempos.update((int(anio), 0) for anio in src_regional.anio.unique())
    tiempos.update((int(anio), 0) for anio in src_global.Year.unique())
    tiempo_rows = []
    for anio, semana in sorted(tiempos):
        trimestre_epi, trimestre_nombre = _trimestre(semana)
        tiempo_rows.append({
            "tiempo_key": anio * 100 + semana,
            "anio": anio,
            "semana": semana,
            "trimestre_epi": trimestre_epi,
            "trimestre_epi_nombre": trimestre_nombre,
            "periodo": _periodo_oms(anio) if anio in set(src_global.Year) else "No aplica",
            "periodo_analisis": _periodo_analisis(anio),
            "tipo_anio_sivigila": tipo_anio.get(anio, "No aplica"),
            "anio_completo": "No" if anio == 2026 else "Si",
        })
    dim_tiempo = pd.DataFrame(tiempo_rows)
    tiempo_ids = {
        (int(row.anio), int(row.semana)): int(row.tiempo_key)
        for row in dim_tiempo.itertuples()
    }

    return (
        dim_tiempo, dim_territorio, dim_evento, dim_fuente,
        tiempo_ids, territorio_ids, evento_ids, fuente_ids, promedio,
    )


def transformar():
    nacional, regional, global_oms, _departamentos = _cargar_fuentes()
    (dim_tiempo, dim_territorio, dim_evento, dim_fuente,
     tiempo_ids, territorio_ids, evento_ids, fuente_ids, promedio) = _construir_dimensiones(
        nacional, regional, global_oms, _departamentos
    )

    evento_nacional = {
        _texto(row.nombre_evento): _texto(row.cod_eve)
        for row in nacional[["cod_eve", "nombre_evento"]].drop_duplicates().itertuples()
    }
    evento_regional = {
        nombre: evento_ids[("SIVIGILA", nombre, "Solo Cundinamarca")]
        for nombre in regional.evento.drop_duplicates()
    }
    evento_nacional_ids = {
        nombre: evento_ids[("SIVIGILA", nombre, "Nacional")]
        for nombre in nacional.nombre_evento.drop_duplicates()
    }
    territorio_nacional = {
        _codigo(row.cod_mun_o): territorio_ids[("Colombia", _codigo(row.cod_mun_o))]
        for row in nacional[["cod_mun_o"]].drop_duplicates().itertuples()
    }
    territorio_regional = {
        _codigo(row.cod_municipio): territorio_ids[("Colombia", _codigo(row.cod_municipio))]
        for row in regional[["cod_municipio"]].drop_duplicates().itertuples()
    }
    territorio_global = {
        _texto(row.iso3).upper(): territorio_ids[("Mundo", _texto(row.iso3).upper())]
        for row in global_oms[["iso3"]].drop_duplicates().itertuples()
    }
    event_global = {
        ( _texto(row.icd104n), _texto(row.icd103n), _texto(row.icd10n)):
            evento_ids[("CIE-10 OMS", _texto(row.icd104n), "Global")]
        for row in global_oms[["icd104n", "icd103n", "icd10n"]].drop_duplicates().itertuples()
    }

    nacional_hechos = pd.DataFrame({
        "tiempo_key": [tiempo_ids[(int(y), int(s))] for y, s in zip(nacional.ano, nacional.semana)],
        "territorio_key": [territorio_nacional[_codigo(c)] for c in nacional.cod_mun_o],
        "evento_key": [evento_nacional_ids[_texto(e)] for e in nacional.nombre_evento],
        "fuente_key": fuente_ids["SIVIGILA Colombia"],
        "id_brote": "",
        "casos": nacional.conteo.astype(int),
        "brotes": None,
    })
    regional_hechos = pd.DataFrame({
        "tiempo_key": [tiempo_ids[(int(y), 0)] for y in regional.anio],
        "territorio_key": [territorio_regional[_codigo(c)] for c in regional.cod_municipio],
        "evento_key": [evento_regional[_texto(e)] for e in regional.evento],
        "fuente_key": fuente_ids["SIVIGILA Cundinamarca"],
        "id_brote": "",
        "casos": regional.conteo.astype(int),
        "brotes": None,
    })
    global_hechos = pd.DataFrame({
        "tiempo_key": [tiempo_ids[(int(y), 0)] for y in global_oms.Year],
        "territorio_key": [territorio_global[_texto(c).upper()] for c in global_oms.iso3],
        "evento_key": [
            event_global[(_texto(e), _texto(d), _texto(ch))]
            for e, d, ch in zip(global_oms.icd104n, global_oms.icd103n, global_oms.icd10n)
        ],
        "fuente_key": fuente_ids["OMS/HDX"],
        "id_brote": global_oms.id_outbreak.astype(str).str.strip(),
        "casos": None,
        "brotes": 1,
    })
    fact = pd.concat([nacional_hechos, regional_hechos, global_hechos], ignore_index=True)
    fact.insert(0, "notificacion_id", range(1, len(fact) + 1))

    sources = {"nacional": nacional, "regional": regional, "global": global_oms}
    return {
        "dim_tiempo": dim_tiempo,
        "dim_territorio": dim_territorio,
        "dim_evento": dim_evento,
        "dim_fuente": dim_fuente,
        "fact_notificacion": fact,
    }, sources, promedio


def _insertar(con, nombre, df):
    columnas = ",".join(df.columns)
    marcas = ",".join("?" for _ in df.columns)
    consulta = f"INSERT INTO {nombre} ({columnas}) VALUES ({marcas})"
    con.executemany(consulta, df.astype(object).itertuples(index=False, name=None))


def validar(con, tablas, fuentes):
    validaciones = []

    def agregar(grupo, nombre, esperado, obtenido, nota=""):
        validaciones.append({
            "grupo": grupo,
            "nombre": nombre,
            "esperado": esperado,
            "obtenido": obtenido,
            "ok": esperado == obtenido,
            "nota": nota,
        })

    for tabla, clave in [
        ("dim_tiempo", "tiempo_key"),
        ("dim_territorio", "territorio_key"),
        ("dim_evento", "evento_key"),
        ("dim_fuente", "fuente_key"),
        ("fact_notificacion", "notificacion_id"),
    ]:
        total, distintos = con.execute(
            f"SELECT COUNT(*), COUNT(DISTINCT {clave}) FROM {tabla}"
        ).fetchone()
        agregar("Unicidad", f"{tabla}.{clave}", total, distintos)

    for tabla, fk in [
        ("dim_tiempo", "tiempo_key"),
        ("dim_territorio", "territorio_key"),
        ("dim_evento", "evento_key"),
        ("dim_fuente", "fuente_key"),
    ]:
        huerfanos = con.execute(
            f"SELECT COUNT(*) FROM fact_notificacion f "
            f"LEFT JOIN {tabla} d USING ({fk}) WHERE d.{fk} IS NULL"
        ).fetchone()[0]
        agregar("Integridad referencial", f"Hechos sin {tabla}", 0, huerfanos)
    agregar("Integridad referencial", "PRAGMA foreign_key_check", 0,
            len(con.execute("PRAGMA foreign_key_check").fetchall()))

    duplicados = con.execute(
        "SELECT COUNT(*) FROM (SELECT 1 FROM fact_notificacion "
        "GROUP BY fuente_key, tiempo_key, territorio_key, evento_key, id_brote "
        "HAVING COUNT(*) > 1)"
    ).fetchone()[0]
    agregar("Grano", "Duplicados en la clave natural del hecho", 0, duplicados)
    medidas_invalidas = con.execute(
        "SELECT COUNT(*) FROM fact_notificacion WHERE "
        "((casos IS NOT NULL AND brotes IS NOT NULL) OR "
        "(casos IS NULL AND brotes IS NULL) OR "
        "(casos IS NOT NULL AND casos < 1) OR (brotes IS NOT NULL AND brotes <> 1))"
    ).fetchone()[0]
    agregar("Medidas", "Casos y brotes excluyentes y válidos", 0, medidas_invalidas)

    esperados_filas = {
        "SIVIGILA Colombia": len(fuentes["nacional"]),
        "SIVIGILA Cundinamarca": len(fuentes["regional"]),
        "OMS/HDX": len(fuentes["global"]),
    }
    esperados_casos = {
        "SIVIGILA Colombia": int(fuentes["nacional"].conteo.sum()),
        "SIVIGILA Cundinamarca": int(fuentes["regional"].conteo.sum()),
        "OMS/HDX": None,
    }
    obtenidos_filas = dict(con.execute(
        "SELECT d.fuente, COUNT(*) FROM fact_notificacion f "
        "JOIN dim_fuente d USING (fuente_key) GROUP BY d.fuente"
    ))
    obtenidos_casos = dict(con.execute(
        "SELECT d.fuente, SUM(f.casos) FROM fact_notificacion f "
        "JOIN dim_fuente d USING (fuente_key) GROUP BY d.fuente"
    ))
    for fuente, filas_esperadas in esperados_filas.items():
        agregar("Coherencia con fuentes", f"Filas de {fuente}", filas_esperadas,
                obtenidos_filas.get(fuente, 0))
        if esperados_casos[fuente] is not None:
            agregar("Coherencia con fuentes", f"Casos de {fuente}", esperados_casos[fuente],
                    obtenidos_casos.get(fuente))
    brotes = con.execute(
        "SELECT SUM(brotes) FROM fact_notificacion f "
        "JOIN dim_fuente d USING (fuente_key) WHERE d.fuente = 'OMS/HDX'"
    ).fetchone()[0]
    agregar("Coherencia con fuentes", "Brotes OMS/HDX", esperados_filas["OMS/HDX"], brotes)
    fuentes_sin_hechos = con.execute(
        "SELECT COUNT(*) FROM dim_fuente s WHERE NOT EXISTS "
        "(SELECT 1 FROM fact_notificacion f WHERE f.fuente_key = s.fuente_key)"
    ).fetchone()[0]
    agregar("Cobertura", "Fuentes con registros", 0, fuentes_sin_hechos)
    eventos_no_etv = con.execute(
        "SELECT COUNT(*) FROM dim_evento WHERE evento_key NOT IN "
        "(SELECT DISTINCT evento_key FROM fact_notificacion)"
    ).fetchone()[0]
    agregar("Cobertura", "Eventos sin registros asociados", 0, eventos_no_etv)

    return validaciones


def _esquema_actual(con):
    tablas = {
        row[0] for row in con.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    requeridas = {"dim_tiempo", "dim_territorio", "dim_evento", "dim_fuente", "fact_notificacion"}
    if not requeridas.issubset(tablas):
        return False
    columnas = {
        row[1] for row in con.execute("PRAGMA table_info(dim_tiempo)")
    }
    if not {"periodo_analisis", "tipo_anio_sivigila"}.issubset(columnas):
        return False
    columnas_evento = {row[1] for row in con.execute("PRAGMA table_info(dim_evento)")}
    if not {"vector", "anio_primer_registro"}.issubset(columnas_evento):
        return False
    fuentes = {row[0] for row in con.execute("SELECT fuente FROM dim_fuente")}
    return {"SIVIGILA Colombia", "SIVIGILA Cundinamarca", "OMS/HDX"}.issubset(fuentes)


def construir():
    print("Cargando fuentes y construyendo dimensiones ...")
    tablas, fuentes, promedio = transformar()
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    temp = tempfile.NamedTemporaryFile(
        prefix="nexobio_olap_", suffix=".db", dir=os.path.dirname(DB), delete=False
    )
    ruta_temp = temp.name
    temp.close()
    con = None
    try:
        con = sqlite3.connect(ruta_temp)
        con.executescript(open(SQL, encoding="utf-8").read())
        for nombre, df in tablas.items():
            _insertar(con, nombre, df)
        con.commit()
        print("Validando integridad, grano y medidas ...")
        resultados = validar(con, tablas, fuentes)
        con.execute("ANALYZE")
        con.close()
        con = None

        with open(VALIDACIONES, "w", encoding="utf-8") as salida:
            json.dump({
                "fuente": "SIVIGILA Colombia + SIVIGILA Cundinamarca + OMS/HDX",
                "filas_origen": len(tablas["fact_notificacion"]),
                "casos_origen": int(tablas["fact_notificacion"].casos.sum()),
                "brotes_origen": int(tablas["fact_notificacion"].brotes.sum()),
                "validaciones": resultados,
            }, salida, ensure_ascii=False, indent=2)

        os.replace(ruta_temp, DB)
    finally:
        if con is not None:
            con.close()
        if os.path.exists(ruta_temp):
            os.remove(ruta_temp)

    fallidas = [r for r in resultados if not r["ok"]]
    for resultado in resultados:
        print(("OK   " if resultado["ok"] else "FALLA"),
              "|", resultado["grupo"], "|", resultado["nombre"])
    print(f"\n{len(resultados) - len(fallidas)}/{len(resultados)} validaciones correctas. BD: {DB}")
    return resultados, len(fallidas)


def main():
    _resultados, fallos = construir()
    sys.exit(1 if fallos else 0)


if __name__ == "__main__":
    main()
