"""
cargar_modelo.py  -  ETL del modelo estrella (Etapa 5)

Transforma los datos tratados en la Etapa 3 (datos/Datos_de_Vigilancia_ColombiaCompleto_Limpio.csv)
en dimensiones + tabla de hechos dentro de SQLite (olap/nexobio_olap.db) y ejecuta las validaciones.

USO (desde la raiz del repositorio):
    python scripts/olap/cargar_modelo.py
Salidas:
    olap/nexobio_olap.db        base de datos del modelo
    olap/validaciones.json      resultado de las validaciones (lo muestra la aplicacion Flask)
"""
import json
import os
import sqlite3
import sys

import pandas as pd

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ARCHIVO_FUENTE = "Datos_de_Vigilancia_ColombiaCompleto_Limpio.csv"
ARCHIVO_REGIONAL = "Regional_Cundinamarca_ETV_Limpio.csv"


def localizar_datos():
    """Carpeta con los archivos tratados de la Etapa 3 (powerbi/datos en la rama principal; datos/ en ramas antiguas)."""
    for rel in ("powerbi/datos", "datos", "data"):
        ruta = os.path.join(RAIZ, *rel.split("/"))
        if os.path.exists(os.path.join(ruta, ARCHIVO_FUENTE)):
            return ruta
    raise FileNotFoundError(f"No se encontro {ARCHIVO_FUENTE} en powerbi/datos/, datos/ ni data/")


DATOS = localizar_datos()
DB = os.path.join(RAIZ, "olap", "nexobio_olap.db")
SQL = os.path.join(RAIZ, "scripts", "olap", "crear_modelo.sql")
VALIDACIONES = os.path.join(RAIZ, "olap", "validaciones.json")

# --- Region natural por codigo DANE de departamento (clasificacion geografica estandar) ----------
REGION_NATURAL = {}
for reg, cods in {
    "Andina": [5, 11, 15, 17, 25, 41, 54, 63, 66, 68, 73],
    "Caribe": [8, 13, 20, 23, 44, 47, 70],
    "Pacifica": [19, 27, 52, 76],
    "Orinoquia": [50, 81, 85, 99],
    "Amazonia": [18, 86, 91, 94, 95, 97],
    "Insular": [88],
}.items():
    for c in cods:
        REGION_NATURAL[c] = reg

# --- Evento: vector -> familia -> evento -------------------------------------------------------
EVENTOS = {
    "DENGUE": ("Dengue", "Aedes"),
    "DENGUE GRAVE": ("Dengue", "Aedes"),
    "CHIKUNGUNYA": ("Chikungunya", "Aedes"),
    "CHAGAS": ("Chagas", "Triatominos"),
}

PERIODOS = [(2007, 2010, "2007-2010"), (2011, 2016, "2011-2016"), (2017, 2022, "2017-2022")]


def periodo_de(anio):
    for a, b, nombre in PERIODOS:
        if a <= anio <= b:
            return nombre
    return "Otro"


def tipo_ubicacion(cod_dpto, nombre_mun):
    if cod_dpto == 0:
        return "Procedencia desconocida"
    if cod_dpto == 1:
        return "Exterior"
    if "SIN MUNICIPIO" in nombre_mun.upper():
        return "Sin municipio asignado"
    return "Municipio"


def limpiar_municipio(nombre):
    return nombre.replace("*", "").strip()


def transformar():
    src = pd.read_csv(os.path.join(DATOS, ARCHIVO_FUENTE))
    dep = pd.read_csv(os.path.join(DATOS, "dim_departamento.csv"))
    nombre_dpto = dict(zip(dep.cod_dpto_o, dep.nombre_mostrar))

    # dim_evento
    ev = src[["cod_eve", "nombre_evento"]].drop_duplicates().sort_values("cod_eve").reset_index(drop=True)
    ev["evento_key"] = ev.index + 1
    ev["familia"] = ev.nombre_evento.map(lambda e: EVENTOS[e][0])
    ev["vector"] = ev.nombre_evento.map(lambda e: EVENTOS[e][1])
    dim_evento = ev.rename(columns={"cod_eve": "cod_evento", "nombre_evento": "evento"})[
        ["evento_key", "cod_evento", "evento", "familia", "vector"]]

    # dim_territorio (un registro por municipio)
    t = src[["cod_mun_o", "municipio_ocurrencia", "cod_dpto_o"]].drop_duplicates("cod_mun_o")
    t = t.sort_values("cod_mun_o").reset_index(drop=True)
    t["territorio_key"] = t.index + 1
    t["municipio"] = t.municipio_ocurrencia.map(limpiar_municipio)
    t["departamento"] = t.cod_dpto_o.map(nombre_dpto)
    t["tipo_ubicacion"] = [tipo_ubicacion(d, m) for d, m in zip(t.cod_dpto_o, t.municipio_ocurrencia)]
    t["region_natural"] = t.cod_dpto_o.map(REGION_NATURAL).fillna("No aplica")
    dim_territorio = t.rename(columns={"cod_mun_o": "cod_municipio", "cod_dpto_o": "cod_departamento"})[
        ["territorio_key", "cod_municipio", "municipio", "cod_departamento", "departamento",
         "region_natural", "tipo_ubicacion"]]

    # dim_anio (tipo_anio: epidemico si los casos del anio superan el promedio anual)
    por_anio = src.groupby("ano").conteo.sum()
    promedio = por_anio.mean()
    dim_anio = pd.DataFrame({
        "anio_key": por_anio.index,
        "periodo": [periodo_de(a) for a in por_anio.index],
        "tipo_anio": ["Epidemico" if v > promedio else "No epidemico" for v in por_anio.values],
    })

    # dim_semana
    semanas = sorted(src.semana.unique())
    nombres = {1: "T1 (sem 1-13)", 2: "T2 (sem 14-26)", 3: "T3 (sem 27-39)", 4: "T4 (sem 40-53)"}
    dim_semana = pd.DataFrame({"semana_key": semanas})
    dim_semana["trimestre_epi"] = dim_semana.semana_key.map(lambda s: min((s - 1) // 13 + 1, 4))
    dim_semana["trimestre"] = dim_semana.trimestre_epi.map(nombres)

    # fact
    f = src.merge(dim_evento[["evento_key", "cod_evento"]], left_on="cod_eve", right_on="cod_evento")
    f = f.merge(dim_territorio[["territorio_key", "cod_municipio"]], left_on="cod_mun_o", right_on="cod_municipio")
    fact = pd.DataFrame({
        "evento_key": f.evento_key, "territorio_key": f.territorio_key,
        "anio_key": f.ano, "semana_key": f.semana, "casos": f.conteo,
    })
    return src, dim_evento, dim_territorio, dim_anio, dim_semana, fact, promedio


def cargar(con, tablas):
    for nombre, df in tablas.items():
        cols = ",".join(df.columns)
        marcas = ",".join("?" * len(df.columns))
        con.executemany(f"INSERT INTO {nombre} ({cols}) VALUES ({marcas})",
                        df.astype(object).itertuples(index=False, name=None))
    con.commit()


def validar(con, src, promedio):
    """Devuelve la lista de comprobaciones. Cada una: nombre, esperado, obtenido, ok, nota."""
    q = lambda s, *a: con.execute(s, a).fetchall()
    v = []

    def add(grupo, nombre, esperado, obtenido, nota=""):
        v.append({"grupo": grupo, "nombre": nombre, "esperado": esperado, "obtenido": obtenido,
                  "ok": esperado == obtenido, "nota": nota})

    # 1. Unicidad de claves de las dimensiones
    for tabla, pk in [("dim_evento", "evento_key"), ("dim_territorio", "territorio_key"),
                      ("dim_anio", "anio_key"), ("dim_semana", "semana_key")]:
        n, nd = q(f"SELECT COUNT(*), COUNT(DISTINCT {pk}) FROM {tabla}")[0]
        add("Unicidad de claves", f"{tabla}.{pk} sin repetidos", n, nd)
    n, nd = q("SELECT COUNT(*), COUNT(DISTINCT cod_municipio) FROM dim_territorio")[0]
    add("Unicidad de claves", "dim_territorio: un registro por codigo de municipio", n, nd)

    # 2. Integridad referencial
    for dim, fk in [("dim_evento", "evento_key"), ("dim_territorio", "territorio_key"),
                    ("dim_anio", "anio_key"), ("dim_semana", "semana_key")]:
        huerf = q(f"SELECT COUNT(*) FROM fact_notificacion f LEFT JOIN {dim} d ON f.{fk}=d.{fk} "
                  f"WHERE d.{fk} IS NULL")[0][0]
        add("Integridad referencial", f"Hechos sin registro en {dim}", 0, huerf)
    add("Integridad referencial", "PRAGMA foreign_key_check", 0, len(q("PRAGMA foreign_key_check")))

    # 3. Duplicaciones en la tabla de hechos (grano)
    dup = q("SELECT COUNT(*) FROM (SELECT 1 FROM fact_notificacion GROUP BY evento_key, territorio_key, "
            "anio_key, semana_key HAVING COUNT(*)>1)")[0][0]
    add("Duplicaciones", "Combinaciones evento-municipio-semana-anio repetidas", 0, dup)
    add("Duplicaciones", "Dimensiones sin municipios huerfanos (todos aparecen en hechos)",
        0, q("SELECT COUNT(*) FROM dim_territorio d WHERE NOT EXISTS "
             "(SELECT 1 FROM fact_notificacion f WHERE f.territorio_key=d.territorio_key)")[0][0])

    # 4. Valores faltantes / categorias desconocidas
    add("Categorias desconocidas", "Hechos con casos nulos o <= 0", 0,
        q("SELECT COUNT(*) FROM fact_notificacion WHERE casos IS NULL OR casos<=0")[0][0])
    desc = dict(q("SELECT t.tipo_ubicacion, SUM(f.casos) FROM fact_notificacion f "
                  "JOIN dim_territorio t USING(territorio_key) GROUP BY 1"))
    esp = src.copy()
    esp["t"] = [tipo_ubicacion(d, m) for d, m in zip(esp.cod_dpto_o, esp.municipio_ocurrencia)]
    esp = esp.groupby("t").conteo.sum().to_dict()
    for k in ["Exterior", "Procedencia desconocida", "Sin municipio asignado"]:
        add("Categorias desconocidas", f"Casos en '{k}' conservados con categoria propia",
            int(esp.get(k, 0)), int(desc.get(k, 0)),
            "No se eliminan ni se mezclan con un municipio real; se excluyen de rankings de departamentos.")

    # 4b. Cada departamento real debe tener una region natural asignada
    add("Categorias desconocidas", "Municipios de departamentos reales sin region natural", 0,
        q("SELECT COUNT(*) FROM dim_territorio WHERE tipo_ubicacion IN ('Municipio','Sin municipio asignado') "
          "AND region_natural='No aplica'")[0][0])
    add("Categorias desconocidas", "Departamentos reales por region natural (33 en total)", 33,
        q("SELECT COUNT(DISTINCT cod_departamento) FROM dim_territorio WHERE region_natural<>'No aplica'")[0][0])

    # 5. Coherencia con los datos tratados (comparacion modelo vs. origen)
    add("Coherencia con el origen", "Filas de hechos = filas del CSV tratado", len(src),
        q("SELECT COUNT(*) FROM fact_notificacion")[0][0])
    add("Coherencia con el origen", "Total de casos (SUM casos) = SUM conteo del CSV", int(src.conteo.sum()),
        q("SELECT SUM(casos) FROM fact_notificacion")[0][0])
    por_ev = src.groupby("nombre_evento").conteo.sum().astype(int).to_dict()
    mod_ev = dict(q("SELECT e.evento, SUM(f.casos) FROM fact_notificacion f JOIN dim_evento e USING(evento_key) GROUP BY 1"))
    add("Coherencia con el origen", "Casos por evento (4 eventos)", por_ev, mod_ev)
    por_an = src.groupby("ano").conteo.sum().astype(int).to_dict()
    mod_an = dict(q("SELECT anio_key, SUM(casos) FROM fact_notificacion GROUP BY 1"))
    add("Coherencia con el origen", "Casos por anio (16 anios)", por_an, mod_an)
    por_dp = src.groupby("cod_dpto_o").conteo.sum().astype(int).to_dict()
    mod_dp = dict(q("SELECT t.cod_departamento, SUM(f.casos) FROM fact_notificacion f "
                    "JOIN dim_territorio t USING(territorio_key) GROUP BY 1"))
    add("Coherencia con el origen", "Casos por departamento (35 codigos)", por_dp, mod_dp)
    add("Coherencia con el origen", "Casos por region natural suman el total",
        int(src.conteo.sum()),
        q("SELECT SUM(c) FROM (SELECT SUM(f.casos) c FROM fact_notificacion f "
          "JOIN dim_territorio t USING(territorio_key) GROUP BY t.region_natural)")[0][0])

    # 6. Contraste con otra fuente tratada (archivo regional de Cundinamarca) y con la Etapa 4
    reg = pd.read_csv(os.path.join(DATOS, ARCHIVO_REGIONAL))
    reg_ev = reg.groupby("evento").conteo.sum().astype(int).to_dict()
    mod_cu = dict(q("SELECT e.evento, SUM(f.casos) FROM fact_notificacion f JOIN dim_evento e USING(evento_key) "
                    "JOIN dim_territorio t USING(territorio_key) WHERE t.cod_departamento=25 GROUP BY 1"))
    add("Contraste con otras fuentes", "Cundinamarca por evento: modelo vs. archivo regional", reg_ev, mod_cu,
        "Dos archivos tratados independientes (SIVIGILA portal vs. Gobernacion) deben coincidir.")
    tot_dep = q("SELECT SUM(f.casos) FROM fact_notificacion f JOIN dim_territorio t USING(territorio_key) "
                "WHERE t.tipo_ubicacion IN ('Municipio','Sin municipio asignado')")[0][0]
    add("Contraste con la Etapa 4", "Casos en departamentos (Power BI: 1.265.731)", 1265731, tot_dep)
    top5 = q("SELECT SUM(c) FROM (SELECT SUM(f.casos) c FROM fact_notificacion f JOIN dim_territorio t "
             "USING(territorio_key) WHERE t.tipo_ubicacion IN ('Municipio','Sin municipio asignado') "
             "GROUP BY t.departamento ORDER BY c DESC LIMIT 5)")[0][0]
    add("Contraste con la Etapa 4", "% casos en los 5 departamentos con mas casos (Power BI: 47,79 %)",
        47.79, round(100 * top5 / tot_dep, 2))
    dg = q("SELECT SUM(CASE WHEN e.evento='DENGUE GRAVE' THEN f.casos END)*100.0/SUM(f.casos) "
           "FROM fact_notificacion f JOIN dim_evento e USING(evento_key) JOIN dim_territorio t USING(territorio_key) "
           "WHERE e.familia='Dengue' AND t.tipo_ubicacion IN ('Municipio','Sin municipio asignado')")[0][0]
    add("Contraste con la Etapa 4", "% de dengue grave en departamentos (Power BI: 3,67 %)", 3.67, round(dg, 2))
    add("Contraste con la Etapa 4", "Promedio anual de casos (Power BI: 79.334)", 79334, round(promedio))
    return v


def construir():
    """Ejecuta todo el ETL y devuelve (resultados de validacion, numero de fallos)."""
    print("Transformando ...")
    src, dim_evento, dim_territorio, dim_anio, dim_semana, fact, promedio = transformar()
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    if os.path.exists(DB):
        os.remove(DB)
    con = sqlite3.connect(DB)
    con.executescript(open(SQL, encoding="utf-8").read())
    print("Cargando dimensiones y hechos ...")
    cargar(con, {"dim_evento": dim_evento, "dim_territorio": dim_territorio, "dim_anio": dim_anio,
                 "dim_semana": dim_semana, "fact_notificacion": fact})
    print("Validando ...")
    resultados = validar(con, src, promedio)
    con.execute("ANALYZE")
    con.close()
    with open(VALIDACIONES, "w", encoding="utf-8") as fh:
        json.dump({"fuente": ARCHIVO_FUENTE, "filas_origen": int(len(src)),
                   "casos_origen": int(src.conteo.sum()), "validaciones": resultados},
                  fh, ensure_ascii=False, indent=2, default=str)
    fallos = [r for r in resultados if not r["ok"]]
    for r in resultados:
        print(("OK   " if r["ok"] else "FALLA"), "|", r["grupo"], "|", r["nombre"])
    print(f"\n{len(resultados) - len(fallos)}/{len(resultados)} comprobaciones correctas. BD: {DB}")
    return resultados, len(fallos)


def main():
    _, fallos = construir()
    sys.exit(1 if fallos else 0)


if __name__ == "__main__":
    main()
