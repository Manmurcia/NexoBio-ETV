"""
consultas.py - Motor de consultas multidimensionales sobre el modelo estrella (SQLite).

Todas las cifras de la aplicacion salen de aqui: cada funcion arma una sola consulta SQL
parametrizada sobre fact_notificacion + dimensiones. Los niveles y medidas son listas
cerradas (no se concatena texto del usuario en el SQL; los valores van como parametros).

Operaciones multidimensionales:
  drill-down / roll-up : cambiar el nivel de una jerarquia (se recalcula con GROUP BY en el nuevo nivel)
  slice                : un filtro de UN valor sobre UNA dimension
  dice                 : filtros combinados sobre DOS o mas dimensiones
  pivot                : intercambiar filas y columnas de la matriz
"""
import os
import sqlite3

import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(AQUI, "nexobio_olap.db")

# ----------------------------------------------------------------------------------------------
# Niveles de las jerarquias (nombre -> expresion SQL, dimension, etiqueta)
# ----------------------------------------------------------------------------------------------
NIVELES = {
    "region":       {"expr": "t.region", "dim": "Territorio", "etiqueta": "Región natural"},
    "departamento": {"expr": "t.area", "dim": "Territorio", "etiqueta": "Departamento"},
    "municipio":    {"expr": "t.localidad || ' (' || t.area || ')'", "dim": "Territorio",
                     "etiqueta": "Municipio"},
    "enfermedad":   {"expr": "e.enfermedad", "dim": "Evento", "etiqueta": "Enfermedad"},
    "familia":      {"expr": "e.enfermedad", "dim": "Evento", "etiqueta": "Enfermedad"},
    "evento":       {"expr": "e.evento", "dim": "Evento", "etiqueta": "Evento"},
    "periodo":      {"expr": "a.periodo_analisis", "dim": "Tiempo", "etiqueta": "Periodo de análisis"},
    "tipo_anio":    {"expr": "a.tipo_anio_sivigila", "dim": "Tiempo", "etiqueta": "Tipo de año SIVIGILA"},
    "anio":         {"expr": "a.anio", "dim": "Tiempo", "etiqueta": "Año"},
    "trimestre":    {"expr": "a.trimestre_epi_nombre", "dim": "Tiempo", "etiqueta": "Trimestre epidemiológico"},
    "semana":       {"expr": "a.semana", "dim": "Tiempo", "etiqueta": "Semana epidemiológica"},
    "escala":       {"expr": "u.escala", "dim": "Fuente", "etiqueta": "Escala de la fuente"},
    "fuente":       {"expr": "u.fuente", "dim": "Fuente", "etiqueta": "Fuente de datos"},
}

JERARQUIAS = {
    "Territorio": ["region", "departamento", "municipio"],
    "Evento": ["enfermedad", "evento"],
    "Tiempo": ["periodo", "anio", "trimestre", "semana"],
    "Semana": ["trimestre", "semana"],
    "Fuente": ["escala", "fuente"],
}

# Niveles con orden natural (no por valor de la medida)
ORDEN_NATURAL = {"periodo", "tipo_anio", "anio", "trimestre", "semana", "escala", "fuente"}

# ----------------------------------------------------------------------------------------------
# Medidas. 'aditiva' indica si se puede sumar entre grupos; las demas se RECALCULAN por grupo.
# ----------------------------------------------------------------------------------------------
GRAVE = "SUM(CASE WHEN e.evento='DENGUE GRAVE' THEN f.casos END)"
DENGUE = "SUM(CASE WHEN e.enfermedad='Dengue' THEN f.casos END)"

MEDIDAS = {
    "casos": {"sql": "SUM(f.casos)", "nombre": "Casos notificados", "unidad": "casos", "aditiva": True,
              "formula": "SUM(casos)"},
    "registros": {"sql": "COUNT(*)", "nombre": "Registros de notificación", "unidad": "registros",
                  "aditiva": True, "formula": "COUNT(*) de la tabla de hechos"},
    "municipios": {"sql": "COUNT(DISTINCT CASE WHEN t.ambito='Colombia' "
                          "AND t.localidad NOT IN ('No aplica','Sin municipio asignado') "
                          "THEN f.territorio_key END)",
                   "nombre": "Municipios con casos", "unidad": "municipios", "aditiva": False,
                   "formula": "COUNT(DISTINCT municipio con casos)"},
    "pct_grave": {"sql": f"100.0*COALESCE({GRAVE},0)/NULLIF({DENGUE},0)",
                  "num": f"COALESCE({GRAVE},0)", "den": f"{DENGUE}",
                  "nombre": "% de dengue grave", "unidad": "%", "aditiva": False,
                  "formula": "100 × casos dengue grave / (casos dengue + dengue grave)"},
}

SOLO_DEPARTAMENTOS = "t.ambito='Colombia' AND t.localidad<>'No aplica'"

# Cada alias se une solo si la consulta lo usa (menos joins = consultas mas rapidas)
_JOINS = {"e": "JOIN dim_evento e USING(evento_key)", "t": "JOIN dim_territorio t USING(territorio_key)",
          "a": "JOIN dim_tiempo a ON f.tiempo_key=a.tiempo_key",
          "u": "JOIN dim_fuente u USING(fuente_key)"}


def _from(textos):
    usados = "".join(textos)
    return " FROM fact_notificacion f " + " ".join(j for al, j in _JOINS.items() if f"{al}." in usados) + " "


def _con():
    if not os.path.exists(DB):
        raise FileNotFoundError(
            "No existe olap/nexobio_olap.db. Ejecute: python scripts/olap/cargar_modelo.py")
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    return con


def _validar_niveles(niveles):
    desconocidos = [nivel for nivel in niveles if nivel not in NIVELES]
    if desconocidos:
        raise ValueError(f"Niveles de consulta desconocidos: {desconocidos}")


PERIODOS_COMPARACION = {
    "2007-2022": (2007, 2022),
    "2007-2010": (2007, 2010),
    "2011-2016": (2011, 2016),
    "2017-2022": (2017, 2022),
}
ENFERMEDADES_COMUNES = ("Dengue", "Chikungunya")
SQL_COMPOSICION_FUENTES = """
WITH composicion AS (
    SELECT u.fuente, u.escala, t.ambito, e.enfermedad,
           SUM(CASE WHEN u.fuente = 'OMS/HDX' THEN f.brotes ELSE f.casos END) AS medida
    FROM fact_notificacion f
    JOIN dim_fuente u USING (fuente_key)
    JOIN dim_evento e USING (evento_key)
    JOIN dim_tiempo d USING (tiempo_key)
    JOIN dim_territorio t USING (territorio_key)
    WHERE u.fuente IN (?, ?, ?) AND e.enfermedad IN (?, ?)
      AND d.anio BETWEEN ? AND ? AND t.region <> 'No geografico'
    GROUP BY u.fuente, u.escala, t.ambito, e.enfermedad
)
SELECT fuente, escala, ambito, enfermedad,
       100.0 * medida / NULLIF(SUM(medida) OVER (PARTITION BY fuente), 0) AS porcentaje
FROM composicion
ORDER BY escala, fuente, enfermedad
"""


def composicion_fuentes(periodo="2007-2022"):
    """Compara porcentajes por fuente en el conjunto comun de Dengue/Chikungunya."""
    if periodo not in PERIODOS_COMPARACION:
        raise ValueError(f"Periodo de comparacion no permitido: {periodo}")
    desde, hasta = PERIODOS_COMPARACION[periodo]
    con = _con()
    try:
        resultados = con.execute(
            SQL_COMPOSICION_FUENTES,
            (
                "SIVIGILA Colombia", "SIVIGILA Cundinamarca", "OMS/HDX",
                *ENFERMEDADES_COMUNES, desde, hasta,
            ),
        ).fetchall()
    finally:
        con.close()

    por_fuente = {}
    for fuente, escala, ambito, enfermedad, porcentaje in resultados:
        por_fuente.setdefault(fuente, {
            "escala": escala, "ambito": ambito, "porcentajes": {},
        })["porcentajes"][enfermedad] = float(porcentaje)

    esperado = ("SIVIGILA Colombia", "SIVIGILA Cundinamarca", "OMS/HDX")
    registros = []
    for fuente in esperado:
        detalle = por_fuente.get(fuente)
        if detalle is None:
            raise RuntimeError(f"No hay datos comparables para la fuente {fuente}.")
        for enfermedad in ENFERMEDADES_COMUNES:
            registros.append({
                "fuente": fuente,
                "escala": detalle["escala"],
                "ambito": detalle["ambito"],
                "enfermedad": enfermedad,
                "porcentaje": detalle["porcentajes"].get(enfermedad, 0.0),
            })
    return registros


def _donde(filtros, incluir_desconocidos, semana_max, excluir_semana_cero=False):
    partes, params = [], []
    if not incluir_desconocidos:
        partes.append(SOLO_DEPARTAMENTOS)
    if excluir_semana_cero:
        partes.append("a.semana > 0")
    if semana_max:
        partes.append("a.semana <= ?")
        params.append(int(semana_max))
    filtros = filtros or {}
    desconocidos = set(filtros) - NIVELES.keys()
    if desconocidos:
        raise ValueError(f"Filtros de consulta desconocidos: {sorted(desconocidos)}")
    fuente = filtros.get("fuente", "SIVIGILA Colombia")
    fuentes = [fuente] if isinstance(fuente, str) else list(fuente)
    if len(fuentes) != 1:
        raise ValueError("Cada consulta debe seleccionar exactamente una fuente.")
    partes.append("u.fuente = ?")
    params.append(str(fuentes[0]))
    for nivel, valores in filtros.items():
        if nivel == "fuente" or nivel not in NIVELES or not valores:
            continue
        valores = [valores] if isinstance(valores, (str, int)) else list(valores)
        marcas = ",".join("?" * len(valores))
        partes.append(f"CAST({NIVELES[nivel]['expr']} AS TEXT) IN ({marcas})")
        params.extend(str(v) for v in valores)
    return (" WHERE " + " AND ".join(partes)) if partes else "", params


def _consulta_sql(filas=(), medida="casos", filtros=None, incluir_desconocidos=False, semana_max=None):
    """Agrupa la medida por los niveles indicados. Devuelve DataFrame con una columna por nivel,
    'valor' y, para razones, 'num' y 'den'. Sin niveles devuelve el total de la seleccion."""
    if medida not in MEDIDAS:
        raise ValueError(f"Medida de consulta desconocida: {medida}")
    _validar_niveles(filas)
    if len(set(filas)) != len(filas):
        raise ValueError(f"Niveles de consulta repetidos: {filas}")
    m = MEDIDAS[medida]
    sel = [f"{NIVELES[n]['expr']} AS {n}" for n in filas]
    sel.append(f"{m['sql']} AS valor")
    if "num" in m:
        sel += [f"{m['num']} AS num", f"{m['den']} AS den"]
    excluir_semana_cero = any(nivel in ("trimestre", "semana") for nivel in filas)
    donde, params = _donde(
        filtros, incluir_desconocidos, semana_max,
        excluir_semana_cero=excluir_semana_cero,
    )
    sql = "SELECT " + ", ".join(sel) + _from(sel + [donde]) + donde
    if filas:
        sql += " GROUP BY " + ", ".join(NIVELES[n]["expr"] for n in filas)
    con = _con()
    try:
        df = pd.read_sql_query(sql, con, params=params)
    finally:
        con.close()
    df.attrs["sql"] = sql_legible(sql, params)
    return df


_CACHE = {}


def consulta(filas=(), medida="casos", filtros=None, incluir_desconocidos=False, semana_max=None):
    """Version con cache (la base es de solo lectura). Devuelve siempre una copia."""
    clave = (tuple(filas), medida, tuple(sorted((k, tuple(v) if not isinstance(v, (str, int)) else (v,))
                                               for k, v in (filtros or {}).items())),
             incluir_desconocidos, semana_max)
    if clave not in _CACHE:
        if len(_CACHE) > 600:
            _CACHE.clear()
        _CACHE[clave] = _consulta_sql(filas, medida, filtros, incluir_desconocidos, semana_max)
    df = _CACHE[clave].copy()
    df.attrs["sql"] = _CACHE[clave].attrs["sql"]
    return df


def sql_legible(sql, params):
    """SQL con los parametros sustituidos (solo para mostrarlo en la documentacion)."""
    partes = sql.replace("\n", " ").split("?")
    out = partes[0]
    for p, resto in zip(params, partes[1:]):
        out += (str(p) if str(p).lstrip("-").isdigit() else "'" + str(p).replace("'", "''") + "'") + resto
    import re
    out = re.sub(r"\s+", " ", out).strip()
    for kw in (" FROM ", " JOIN ", " WHERE ", " GROUP BY "):
        out = out.replace(kw, "\n" + kw.strip() + " ")
    return out


def valores_nivel(nivel, filtros=None):
    """Valores existentes de un nivel (para llenar los filtros), en orden natural o alfabetico."""
    _validar_niveles([nivel])
    filtros = filtros or {}
    donde, params = _donde(filtros, incluir_desconocidos=False, semana_max=None)
    expr = NIVELES[nivel]["expr"]
    sql = f"SELECT DISTINCT {expr} AS v" + _from([expr, donde]) + donde + " ORDER BY 1"
    con = _con()
    try:
        vals = [r[0] for r in con.execute(sql, params).fetchall()]
    finally:
        con.close()
    return vals


def total(medida="casos", filtros=None, **kw):
    df = consulta((), medida, filtros, **kw)
    v = df.valor.iloc[0]
    return None if pd.isna(v) else float(v)


def ordenar(df, nivel, medida="casos"):
    if nivel in ORDEN_NATURAL:
        return df.sort_values(nivel).reset_index(drop=True)
    return df.sort_values("valor", ascending=False, na_position="last").reset_index(drop=True)


def ranking(nivel, medida="casos", filtros=None, **kw):
    """Casos por unidad de un nivel, ordenado de mayor a menor, con % sobre el total de la seleccion."""
    df = ordenar(consulta([nivel], medida, filtros, **kw), nivel)
    if MEDIDAS[medida]["aditiva"]:
        tot = df.valor.sum()
        df["pct"] = 100 * df.valor / tot if tot else 0.0
        df["acum"] = df.pct.cumsum()
    return df


def matriz(nivel_fila, nivel_col, medida="casos", filtros=None, modo="valor", max_filas=None,
           max_cols=None, min_den=None, **kw):
    """Cruce de dos niveles. modo: 'valor' | 'pct_fila' | 'pct_col' | 'pct_total'.
    Los totales de fila, de columna y el total general se RECALCULAN con su propia consulta
    (no se suman celdas), de modo que tambien son correctos para razones y conteos distintos.
    min_den: oculta filas cuyo denominador (solo razones) sea menor al umbral."""
    celdas = consulta([nivel_fila, nivel_col], medida, filtros, **kw)
    tot_f = consulta([nivel_fila], medida, filtros, **kw).set_index(nivel_fila)
    tot_c = consulta([nivel_col], medida, filtros, **kw).set_index(nivel_col)
    gran = total(medida, filtros, **kw)
    aditiva = MEDIDAS[medida]["aditiva"]

    if nivel_fila in ORDEN_NATURAL:
        filas = sorted(tot_f.index)
    else:
        filas = list(tot_f.sort_values("valor", ascending=False, na_position="last").index)
    if nivel_col in ORDEN_NATURAL:
        cols = sorted(tot_c.index)
    else:
        cols = list(tot_c.sort_values("valor", ascending=False, na_position="last").index)

    ocultas_den = 0
    if min_den and "den" in tot_f:
        ok = [f for f in filas if (tot_f.loc[f, "den"] or 0) >= min_den]
        ocultas_den = len(filas) - len(ok)
        filas = ok
    cols_ocultas = 0
    if max_cols and len(cols) > max_cols:
        cols_ocultas = len(cols) - max_cols
        cols = cols[:max_cols]
    resto = 0
    if max_filas and len(filas) > max_filas:
        resto = len(filas) - max_filas
        filas_resto = filas[max_filas:]
        filas = filas[:max_filas]

    idx = {(r[nivel_fila], r[nivel_col]): r for _, r in celdas.iterrows()}
    brutas = []   # (etiqueta, total_fila, [(valor, den)])
    for f in filas:
        fila = []
        for c in cols:
            r = idx.get((f, c))
            v = _num(r["valor"]) if r is not None else (0.0 if aditiva else None)
            d = _num(r["den"]) if (r is not None and "den" in r.index) else None
            fila.append((v, d))
        brutas.append((f, _num(tot_f.loc[f, "valor"]), fila))
    if resto and aditiva:
        fila = []
        for k, c in enumerate(cols):
            usado = sum(b[2][k][0] or 0 for b in brutas)
            fila.append((_num(tot_c.loc[c, "valor"]) - usado, None))
        usado_t = sum(b[1] or 0 for b in brutas)
        brutas.append((f"Resto ({resto} unidades)", gran - usado_t, fila))

    def conv(v, tf, c):
        if modo == "valor" or not aditiva or v is None:
            return v
        base = {"pct_fila": tf, "pct_col": _num(tot_c.loc[c, "valor"]), "pct_total": gran}[modo]
        return (100 * v / base) if base else None

    out = {"filas": [], "columnas": cols, "gran_total": gran, "modo": modo, "medida": medida,
           "filas_ocultas": resto if aditiva else resto, "ocultas_den": ocultas_den,
           "cols_ocultas": cols_ocultas, "resto_agregado": bool(resto and aditiva),
           "total_columna": [_num(tot_c.loc[c, "valor"]) for c in cols]}
    for etiqueta, tf, fila in brutas:
        out["filas"].append({"etiqueta": etiqueta, "total": tf, "es_resto": str(etiqueta).startswith("Resto ("),
                             "celdas": [{"v": conv(v, tf, c), "den": d, "num": None}
                                        for (v, d), c in zip(fila, cols)]})
    if "num" in celdas.columns:
        for f_out in out["filas"]:
            for cel, c in zip(f_out["celdas"], cols):
                r = idx.get((f_out["etiqueta"], c))
                cel["num"] = _num(r["num"]) if r is not None else None
    return out


def _num(x):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    return float(x)


# ----------------------------------------------------------------------------------------------
# Indice estacional: % del total anual que cae en cada semana/trimestre, promediado entre anios.
# Cada anio se normaliza a 100 % ANTES de promediar para que los anios epidemicos no dominen.
# ----------------------------------------------------------------------------------------------
def indice_estacional(nivel_unidad, nivel_periodo, filtros=None, min_casos=0, **kw):
    """Devuelve (DataFrame unidad x periodo con el % promedio del total anual, casos por unidad,
    n de anios usados). Excluye la semana 53 (solo existe en 2008, 2014 y 2020)."""
    kw = dict(kw)
    kw["semana_max"] = 52
    if nivel_unidad is None:
        df = consulta(["anio", nivel_periodo], "casos", filtros, **kw)
        df["unidad"] = "Colombia (departamentos)"
    else:
        df = consulta([nivel_unidad, "anio", nivel_periodo], "casos", filtros, **kw)
        df = df.rename(columns={nivel_unidad: "unidad"})
    if df.empty:
        return pd.DataFrame(), pd.Series(dtype=float), 0
    casos_u = df.groupby("unidad").valor.sum()
    pv = df.pivot_table(index=["unidad", "anio"], columns=nivel_periodo, values="valor",
                        aggfunc="sum", fill_value=0)
    tot = pv.sum(axis=1)
    pv = pv[tot > 0].div(tot[tot > 0], axis=0) * 100
    idx = pv.groupby(level=0).mean()
    n_anios = int(df.anio.nunique())
    idx = idx[casos_u.reindex(idx.index) >= min_casos]
    return idx, casos_u.reindex(idx.index), n_anios


def amplitud(serie):
    """Diferencia (puntos porcentuales) entre el periodo con mayor y menor peso."""
    return float(serie.max() - serie.min())


# ----------------------------------------------------------------------------------------------
# Utilidades de jerarquia
# ----------------------------------------------------------------------------------------------
def nivel_inferior(nivel):
    for niveles in JERARQUIAS.values():
        if nivel in niveles and niveles.index(nivel) < len(niveles) - 1:
            return niveles[niveles.index(nivel) + 1]
    return None


def nivel_superior(nivel):
    for niveles in JERARQUIAS.values():
        if nivel in niveles and niveles.index(nivel) > 0:
            return niveles[niveles.index(nivel) - 1]
    return None


def cobertura():
    """Resumen de registros cargados, con cobertura nacional para las vistas 1-4."""
    df = consulta((), "casos")
    con = _con()
    try:
        a, b = con.execute(
            "SELECT MIN(t.anio), MAX(t.anio) FROM fact_notificacion f "
            "JOIN dim_tiempo t USING(tiempo_key) JOIN dim_fuente u USING(fuente_key) "
            "WHERE u.fuente='SIVIGILA Colombia'"
        ).fetchone()
        filas = con.execute(
            "SELECT COUNT(*) FROM fact_notificacion f JOIN dim_fuente u USING(fuente_key) "
            "WHERE u.fuente='SIVIGILA Colombia'"
        ).fetchone()[0]
        mun = con.execute(
            "SELECT COUNT(*) FROM dim_territorio WHERE ambito='Colombia' "
            "AND localidad NOT IN ('No aplica','Sin municipio asignado')"
        ).fetchone()[0]
        total_all = con.execute(
            "SELECT SUM(f.casos) FROM fact_notificacion f JOIN dim_fuente u USING(fuente_key) "
            "WHERE u.fuente='SIVIGILA Colombia'"
        ).fetchone()[0]
        regional = con.execute(
            "SELECT COUNT(*), SUM(f.casos) FROM fact_notificacion f "
            "JOIN dim_fuente u USING(fuente_key) WHERE u.fuente='SIVIGILA Cundinamarca'"
        ).fetchone()
        brotes = con.execute(
            "SELECT COUNT(*), SUM(f.brotes) FROM fact_notificacion f "
            "JOIN dim_fuente u USING(fuente_key) WHERE u.fuente='OMS/HDX'"
        ).fetchone()
        filas_modelo = con.execute("SELECT COUNT(*) FROM fact_notificacion").fetchone()[0]
    finally:
        con.close()
    return {"desde": a, "hasta": b, "registros": filas, "municipios": mun,
            "casos_base": int(df.valor.iloc[0]), "casos_totales": int(total_all),
            "casos_excluidos": int(total_all - df.valor.iloc[0]),
            "filas_modelo": filas_modelo, "filas_regional": regional[0],
            "casos_regional": int(regional[1]), "filas_brotes": brotes[0],
            "brotes": int(brotes[1])}
