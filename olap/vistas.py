"""Arma el contexto de indicadores, graficas, matrices y controles de las vistas OLAP."""
import pandas as pd

from . import consultas as C
from .conocimientos import CONOCIMIENTOS, VISTAS_META

EVENTOS = ["DENGUE", "DENGUE GRAVE", "CHIKUNGUNYA", "CHAGAS"]
PERIODOS = ["2007-2010", "2011-2016", "2017-2022"]
REGIONES = ["Andina", "Caribe", "Pacifica", "Orinoquia", "Amazonia", "Insular"]
FUENTES_CASOS = ["SIVIGILA Colombia", "SIVIGILA Cundinamarca"]
COLOR_REGION = {"Andina": "#0284c7", "Caribe": "#f59e0b", "Pacifica": "#10b981",
                "Orinoquia": "#8b5cf6", "Amazonia": "#ef4444", "Insular": "#64748b"}
PALETA = ["#0284c7", "#f59e0b", "#10b981", "#8b5cf6", "#ef4444", "#64748b", "#0f766e", "#be185d"]
NOMBRE_REGION = {"Pacifica": "Pacífica", "Orinoquia": "Orinoquía", "Amazonia": "Amazonía"}


# ----------------------------------------------------------------------------- formato es-CO
def fm(v, dec=0):
    if v is None or pd.isna(v):
        return "–"
    s = f"{v:,.{dec}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def fp(v, dec=1):
    return "–" if v is None or pd.isna(v) else fm(v, dec) + " %"


PLURAL = {"region": "regiones", "departamento": "departamentos", "municipio": "municipios"}


def sin40_53(df):
    """La vista de estacionalidad excluye la semana 53: el trimestre 4 cubre las semanas 40-52."""
    return df.rename(columns=lambda c: c.replace("40-53", "40-52") if isinstance(c, str) else c)


def bonito(x):
    return NOMBRE_REGION.get(x, x)


def tono(v, vmin, vmax, centro=None):
    """Color de fondo de celda (mapa de calor). Con 'centro' usa escala divergente."""
    if v is None or pd.isna(v):
        return "background:#f1f5f9;color:#94a3b8;"
    if centro is not None:
        dev = v - centro
        rango = max(abs(vmax - centro), abs(vmin - centro)) or 1
        t = min(abs(dev) / rango, 1)
        base = "2,132,199" if dev >= 0 else "245,158,11"
        return f"background:rgba({base},{0.07 + 0.6 * t:.2f});" + ("color:#fff;" if t > 0.75 else "")
    t = (v - vmin) / (vmax - vmin) if vmax > vmin else 0
    return f"background:rgba(2,132,199,{0.06 + 0.62 * t:.2f});" + ("color:#fff;" if t > 0.72 else "")


# ----------------------------------------------------------------------------- utilidades de vista
def _filtros(a, claves):
    f = {}
    for k in claves:
        v = (a.get(k) or "").strip()
        if k == "fuente":
            v = v if v in FUENTES_CASOS else FUENTES_CASOS[0]
        if v:
            f[k] = [v]
    return f


def _operaciones(filtros, niveles_info, pivot, extra=None):
    """Texto de las operaciones activas: drill/roll (nivel), slice, dice y pivot."""
    ops = list(niveles_info)
    dims = {}
    for nivel, vals in filtros.items():
        dims.setdefault(C.NIVELES[nivel]["dim"], []).append(f"{C.NIVELES[nivel]['etiqueta']} = {', '.join(bonito(v) for v in vals)}")
    if len(dims) == 1:
        ops.append("Slice → " + "; ".join(sum(dims.values(), [])))
    elif len(dims) >= 2:
        ops.append("Dice → " + " × ".join("; ".join(v) for v in dims.values()))
    if pivot:
        ops.append("Pivot → filas y columnas intercambiadas")
    if extra:
        ops.extend(extra)
    return ops


def _seleccion(filtros):
    return [(C.NIVELES[n]["etiqueta"], ", ".join(bonito(v) for v in vals)) for n, vals in filtros.items()]


def _tabla(m, medida, modo, pivot_cols_label, fila_link=None, centro=None, umbral_den=None):
    """Convierte la salida de C.matriz en una tabla lista para la plantilla (texto + color)."""
    vals = [c["v"] for f in m["filas"] for c in f["celdas"] if c["v"] is not None and not f["es_resto"]]
    vmin, vmax = (min(vals), max(vals)) if vals else (0, 1)
    es_pct = modo != "valor" or medida == "pct_grave"
    fmt = (lambda v: fp(v, 1)) if es_pct else (lambda v: fm(v))
    filas = []
    for f in m["filas"]:
        celdas = []
        for c in f["celdas"]:
            bajo = umbral_den is not None and c["den"] is not None and c["den"] < umbral_den
            titulo = ""
            if c["num"] is not None and c["den"] is not None:
                titulo = f"{fm(c['num'])} de {fm(c['den'])} casos de dengue"
            celdas.append({
                "txt": fmt(c["v"]) + ("*" if bajo else ""),
                "style": "" if f["es_resto"] else tono(c["v"], vmin, vmax, centro),
                "title": titulo,
            })
        total = f["total"]
        filas.append({
            "etiqueta": bonito(f["etiqueta"]), "raw": f["etiqueta"], "es_resto": f["es_resto"],
            "link": fila_link(f["etiqueta"]) if (fila_link and not f["es_resto"]) else None,
            "celdas": celdas,
            "total": fm(total) if (modo == "valor" and medida != "pct_grave") else (
                fp(total, 2) if medida == "pct_grave" else "100,0 %" if modo == "pct_fila" else ""),
        })
    pie = []
    for v in m["total_columna"]:
        pie.append(fm(v) if (modo == "valor" and medida != "pct_grave") else (
            fp(v, 2) if medida == "pct_grave" else "100,0 %" if modo == "pct_col" else ""))
    return {"columnas": [bonito(str(c)) for c in m["columnas"]], "filas": filas, "pie": pie,
            "gran_total": (fm(m["gran_total"]) if medida != "pct_grave" else fp(m["gran_total"], 2)),
            "tiene_total": modo in ("valor",) or medida == "pct_grave",
            "ocultas": m["filas_ocultas"], "ocultas_den": m.get("ocultas_den", 0),
            "cols_ocultas": m.get("cols_ocultas", 0), "etq_cols": pivot_cols_label}


def _opts(valores, actual, etiquetas=None):
    return [{"v": v, "t": (etiquetas or {}).get(v, bonito(v)), "sel": str(v) == str(actual)} for v in valores]


def _base(vid, a, filtros, pivot, niveles_info, nota_extra=None):
    meta = VISTAS_META[vid]
    return {
        "vid": vid, "meta": meta, "conocimientos": CONOCIMIENTOS[vid],
        "seleccion": _seleccion(filtros),
        "operaciones": _operaciones(filtros, niveles_info, pivot, nota_extra),
        "cobertura": C.cobertura(), "sin_datos": False, "params": dict(a),
    }


# =============================================================================== VISTA 1
def concentracion(a):
    periodos = {
        "2007-2022": "2007–2022",
        "2007-2010": "2007–2010",
        "2011-2016": "2011–2016",
        "2017-2022": "2017–2022",
    }
    periodo = a.get("periodo", "2007-2022")
    if periodo not in periodos:
        periodo = "2007-2022"
    filas = C.composicion_fuentes(periodo)
    fuentes = [
        "SIVIGILA Colombia",
        "SIVIGILA Cundinamarca",
        "OMS/HDX",
    ]
    colores = {
        "SIVIGILA Colombia": "#0284c7",
        "SIVIGILA Cundinamarca": "#f59e0b",
        "OMS/HDX": "#10b981",
    }
    return {
        "vid": "concentracion",
        "meta": VISTAS_META["concentracion"],
        "cobertura": C.cobertura(),
        "periodo": periodo,
        "periodo_etiqueta": periodos[periodo],
        "periodos": [
            {"valor": valor, "etiqueta": etiqueta, "seleccionado": valor == periodo}
            for valor, etiqueta in periodos.items()
        ],
        "filas": filas,
        "enfermedades": list(C.ENFERMEDADES_COMUNES),
        "datasets": [
            {
                "label": fuente,
                "data": [
                    next(
                        fila["porcentaje"]
                        for fila in filas
                        if fila["fuente"] == fuente and fila["enfermedad"] == enfermedad
                    )
                    for enfermedad in C.ENFERMEDADES_COMUNES
                ],
                "backgroundColor": colores[fuente],
            }
            for fuente in fuentes
        ],
    }


# =============================================================================== VISTA 2
def ciclos(a):
    nt = a.get("nivel_t", "region")
    nt = nt if nt in ("region", "departamento") else "region"
    na = a.get("nivel_a", "anio")
    na = na if na in ("periodo", "anio") else "anio"
    filtros = _filtros(a, ["fuente", "evento", "region", "tipo_anio"])
    modo = a.get("modo", "valor")
    modo = modo if modo in ("valor", "pct_fila", "pct_col") else "valor"
    pivot = a.get("pivot") == "1"
    info = [f"Nivel de territorio: {C.NIVELES[nt]['etiqueta']}", f"Nivel de tiempo: {C.NIVELES[na]['etiqueta']}"]
    if nt == "departamento" and "region" in filtros:
        info.append(f"Drill-down: Región → Departamento dentro de {bonito(filtros['region'][0])}")
    ctx = _base("ciclos", a, filtros, pivot, info)

    base = C.consulta([nt, "anio"], "casos", filtros)
    if base.empty:
        ctx["sin_datos"] = True
        return ctx
    pv = base.pivot(index=nt, columns="anio", values="valor").fillna(0)
    tot_anio = pv.sum()
    total = float(tot_anio.sum())
    anio_pico = int(tot_anio.idxmax())
    picos = pv.idxmax(axis=1)
    n_unid = len(pv)
    n_picos = int(picos.nunique())
    tipos = C.consulta(["anio", "tipo_anio"], "casos").set_index("anio").tipo_anio
    ep = float(tot_anio[[y for y in tot_anio.index if tipos[y] == "Epidemico"]].sum())
    unidad = "regiones" if nt == "region" else "departamentos"

    ctx["indicadores"] = [
        {"valor": fm(total), "titulo": "Casos notificados", "nota": "Suma de casos de la selección (2007–2022)."},
        {"valor": f"{anio_pico}", "titulo": "Año con más casos en la selección",
         "nota": f"{fm(tot_anio.max())} casos ({fp(100 * tot_anio.max() / total, 1)} del total de la selección)."},
        {"valor": f"{n_picos} años", "titulo": f"Años distintos de pico entre {n_unid} {unidad}",
         "nota": "Año en que cada unidad alcanza su máximo. Si todas coincidieran, el valor sería 1."},
    ]
    top = list(pv.sum(axis=1).sort_values(ascending=False).head(6).index)
    ctx["graficas"] = [
        {"id": "g1", "tipo": "line", "titulo": f"Casos por año en las {len(top)} unidades con más casos ({unidad}; casos)",
         "labels": [str(y) for y in pv.columns],
         "datasets": [{"label": bonito(u), "data": [float(x) for x in pv.loc[u]],
                       "color": COLOR_REGION.get(u, PALETA[i % len(PALETA)])} for i, u in enumerate(top)],
         "ytitle": "Casos notificados", "xtitle": "Año",
         "nota": "Las curvas no suben ni bajan a la vez: eso indica ciclos desfasados entre territorios."},
        {"id": "g2", "tipo": "bar", "titulo": f"Número de {unidad} cuyo año pico es cada año",
         "labels": [str(y) for y in sorted(picos.unique())],
         "datasets": [{"label": f"{unidad.capitalize()} con pico ese año",
                       "data": [int((picos == y).sum()) for y in sorted(picos.unique())], "color": "#f59e0b"}],
         "ytitle": f"Número de {unidad}", "xtitle": "Año pico",
         "nota": "Se calcula con los casos anuales de cada unidad (a nivel de año, aunque la matriz esté en periodos)."},
    ]
    if pivot:
        m = C.matriz(na, nt, "casos", filtros, modo, max_cols=12)
        etq = f"{C.NIVELES[nt]['etiqueta']} (top 12)"
        link = None
    else:
        m = C.matriz(nt, na, "casos", filtros, modo)
        etq = C.NIVELES[na]["etiqueta"]
        link = None
        if nt == "region":
            link = lambda etiqueta: dict({k: v[0] for k, v in filtros.items()}, nivel_t="departamento", region=etiqueta,
                                         nivel_a=na, modo=modo)
    tabla = _tabla(m, "casos", modo, etq, link)
    tabla["titulo"] = f"{C.NIVELES[nt]['etiqueta']} × {C.NIVELES[na]['etiqueta']} · " + {
        "valor": "casos", "pct_fila": "% de la fila", "pct_col": "% de la columna"}[modo]
    tabla["denominador"] = {
        "valor": "Casos notificados; los totales se recalculan con su propia consulta.",
        "pct_fila": ("Cada fila suma 100 %: denominador = casos de esa " + ("unidad en la selección (distribución en el tiempo)." if not pivot else "columna.")),
        "pct_col": ("Cada columna suma 100 %: denominador = casos de ese " + ("año/periodo en la selección (peso de cada unidad)." if not pivot else "territorio.")),
    }[modo]
    ctx["matriz"] = tabla
    ctx["lectura"] = (
        f"La selección suma {fm(total)} casos; {fp(100 * ep / total, 1)} de ellos (denominador: casos de la selección) ocurrió en años epidémicos "
        f"(2010, 2013–2016 y 2019, años con más casos que el promedio anual nacional de 79.334). "
        f"Entre {n_unid} {unidad} hay {n_picos} años de pico distintos: el ciclo no es simultáneo.")
    ctx["controles"] = {
        "ayuda": "Elija el nivel de territorio y de tiempo (drill-down / roll-up), filtre (slice / dice) y pivote la matriz. El modo % permite comparar ciclos entre territorios de distinto tamaño.",
        "selects": [
            {"name": "fuente", "label": "Fuente de casos", "opts": _opts(FUENTES_CASOS, filtros["fuente"][0])},
            {"name": "evento", "label": "Evento (dimensión Evento)", "opts": _opts([""] + EVENTOS, a.get("evento", ""), {"": "Todos los eventos"})},
            {"name": "region", "label": "Región natural (dimensión Territorio)", "opts": _opts([""] + REGIONES, a.get("region", ""), {"": "Todas las regiones"})},
            {"name": "tipo_anio", "label": "Tipo de año (dimensión Año)", "opts": _opts(["", "Epidemico", "No epidemico"], a.get("tipo_anio", ""),
                                                                                       {"": "Todos los años", "Epidemico": "Epidémico", "No epidemico": "No epidémico"})},
        ],
        "niveles": [
            {"name": "nivel_t", "label": "Nivel de territorio", "opts": _opts(["region", "departamento"], nt, {"region": "Región natural", "departamento": "Departamento"})},
            {"name": "nivel_a", "label": "Nivel de tiempo", "opts": _opts(["periodo", "anio"], na, {"periodo": "Periodo", "anio": "Año"})},
        ],
        "modo": {"name": "modo", "opts": _opts(["valor", "pct_fila", "pct_col"], modo, {"valor": "Casos", "pct_fila": "% de la fila", "pct_col": "% de la columna"})},
        "pivot": pivot, "ocultos": {},
    }
    return ctx


# =============================================================================== VISTA 3
def estacionalidad(a):
    nt = a.get("nivel_t", "region")
    nt = nt if nt in ("region", "departamento") else "region"
    ns = a.get("nivel_s", "trimestre")
    ns = ns if ns in ("trimestre", "semana") else "trimestre"
    if "evento" not in a:                      # primera visita: dengue (evento de la Etapa 4)
        a = dict(a, evento="DENGUE")
    filtros = {"fuente": [FUENTES_CASOS[0]]}
    filtros.update(_filtros(a, ["evento", "periodo", "region"]))
    try:
        min_casos = int(a.get("min_casos", 5000 if nt == "departamento" else 0))
    except ValueError:
        min_casos = 0
    pivot = a.get("pivot") == "1"
    info = [f"Nivel de territorio: {C.NIVELES[nt]['etiqueta']}", f"Nivel de semana: {C.NIVELES[ns]['etiqueta']}",
            "Semana 53 excluida (solo existe en 2008, 2014 y 2020)"]
    ctx = _base("estacionalidad", a, filtros, pivot, info)

    f_nac = {k: v for k, v in filtros.items() if k != "region"}
    nac, cs_nac, n_anios = C.indice_estacional(None, ns, f_nac)
    sel, cs_sel, _ = C.indice_estacional(None, ns, filtros)
    uni, cs_uni, _ = C.indice_estacional(nt, ns, filtros, min_casos=min_casos)
    nac, sel, uni = sin40_53(nac), sin40_53(sel), sin40_53(uni)
    if sel.empty or uni.empty:
        ctx["sin_datos"] = True
        return ctx
    amp_sel = C.amplitud(sel.iloc[0])
    amp_nac = C.amplitud(nac.iloc[0])
    amps = uni.apply(C.amplitud, axis=1).sort_values(ascending=False)
    mayor = amps.index[0]
    pico_col = sel.iloc[0].idxmax()
    n_per = uni.shape[1]
    esperado = 100.0 / n_per
    total = float(cs_sel.iloc[0])

    ctx["indicadores"] = [
        {"valor": fm(total), "titulo": "Casos notificados (semanas 1–52)", "nota": "Suma de casos de la selección; base de los índices estacionales."},
        {"valor": f"{fm(amp_sel, 1)} pp", "titulo": "Amplitud estacional de la selección",
         "nota": f"Diferencia entre el periodo de mayor peso ({fp(sel.iloc[0].max(), 1)}, {pico_col}) y el de menor peso ({fp(sel.iloc[0].min(), 1)}). Referencia nacional: {fm(amp_nac, 1)} pp."},
        {"valor": f"{fm(amps.iloc[0], 1)} pp", "titulo": f"Mayor amplitud entre {PLURAL[nt]}: {bonito(mayor)}",
         "nota": f"Entre {len(amps)} unidades" + (f" con al menos {fm(min_casos)} casos" if min_casos else " (sin mínimo de casos)") + f"; contraste con {fm(amp_nac, 1)} pp del agregado nacional."},
    ]
    # graficas
    labels = [str(c) for c in uni.columns]
    top = list(cs_uni.sort_values(ascending=False).head(6).index)
    ds = [{"label": "Colombia (referencia)", "data": [round(float(x), 2) for x in nac.iloc[0]], "color": "#0f172a", "dash": True}]
    for i, u in enumerate(top):
        ds.append({"label": bonito(u), "data": [round(float(x), 2) for x in uni.loc[u]], "color": COLOR_REGION.get(u, PALETA[i % len(PALETA)])})
    ctx["graficas"] = [
        {"id": "g1", "tipo": "line", "titulo": f"% promedio del total anual por {ns} (6 unidades con más casos y referencia nacional)",
         "labels": labels, "datasets": ds, "ytitle": "% del total anual (promedio de 16 años)", "xtitle": C.NIVELES[ns]["etiqueta"],
         "nota": "Cada año se normaliza a 100 % antes de promediar, para que los años epidémicos no dominen. Si no hubiera estacionalidad, cada periodo valdría " + fm(esperado, 1) + " %."},
        {"id": "g2", "tipo": "bar", "horizontal": True, "titulo": "Amplitud estacional por unidad (puntos porcentuales; Colombia = referencia)",
         "labels": ["Colombia (agregado)"] + [bonito(u) for u in amps.index[:15]],
         "datasets": [{"label": "Amplitud (pp)", "data": [round(amp_nac, 2)] + [round(float(x), 2) for x in amps.head(15)],
                       "color": "#0284c7", "primer_color": "#0f172a"}],
         "ytitle": "Amplitud (pp)", "nota": "Amplitud = % del periodo más alto − % del periodo más bajo. El agregado nacional oculta unidades con amplitud mucho mayor."},
    ]
    # matriz (unidades x periodos)
    orden = list(amps.index) if not pivot else list(amps.index[:12])
    cols = list(uni.columns)
    vmin, vmax = float(uni.min().min()), float(uni.max().max())
    filas = []
    if pivot:
        etq_cols = f"{C.NIVELES[nt]['etiqueta']} (12 con mayor amplitud)"
        for c in cols:
            filas.append({"etiqueta": str(c), "raw": c, "es_resto": False, "link": None, "total": "",
                          "celdas": [{"txt": fp(uni.loc[u, c], 1), "style": tono(uni.loc[u, c], vmin, vmax, esperado), "title": ""} for u in orden]})
        columnas = [bonito(u) for u in orden]
        pie = [fp(amps[u], 1) for u in orden]
        pie_et = "Amplitud (pp)"
    else:
        etq_cols = C.NIVELES[ns]["etiqueta"]
        for u in orden:
            filas.append({"etiqueta": bonito(u), "raw": u, "es_resto": False, "link": None,
                          "celdas": [{"txt": fp(uni.loc[u, c], 1), "style": tono(uni.loc[u, c], vmin, vmax, esperado), "title": ""} for c in cols],
                          "total": f"{fm(amps[u], 1)} pp · {fm(cs_uni[u])} casos"})
        columnas = [str(c) for c in cols]
        pie = [fp(nac.iloc[0][c], 1) for c in cols]
        pie_et = "Colombia (referencia)"
    ctx["matriz"] = {
        "titulo": f"{C.NIVELES[nt]['etiqueta']} × {C.NIVELES[ns]['etiqueta']} · % promedio del total anual",
        "denominador": f"Denominador: casos de cada unidad en cada año (cada fila-año suma 100 % y luego se promedian {n_anios} años). " + (f"Unidades con menos de {fm(min_casos)} casos se ocultan por inestabilidad." if min_casos else "Sin mínimo de casos por unidad.") + f"",
        "columnas": columnas, "filas": filas, "pie": pie, "pie_etiqueta": pie_et, "etq_cols": etq_cols,
        "total_titulo": "Amplitud · casos" if not pivot else "", "gran_total": "", "tiene_total": False, "ocultas": 0,
        "ocultas_den": 0, "cols_ocultas": 0, "personalizada": True, "es_pct": True,
        "leyenda": "Azul: periodo con más peso que el promedio esperado; ámbar: con menos."}
    ctx["lectura"] = (
        f"A nivel agregado el peso de los periodos varía solo {fm(amp_sel, 1)} pp, pero entre {len(amps)} unidades la amplitud llega a "
        f"{fm(amps.iloc[0], 1)} pp en {bonito(mayor)}. Un agregado plano puede esconder patrones locales que se compensan.")
    ctx["controles"] = {
        "ayuda": "Cambie entre trimestre y semana epidemiológica (drill-down / roll-up), filtre por evento, periodo o región (slice / dice) y pivote la matriz.",
        "selects": [
            {"name": "evento", "label": "Evento (dimensión Evento)", "opts": _opts(EVENTOS + [""], a.get("evento", "DENGUE"), {"": "Todos los eventos"})},
            {"name": "periodo", "label": "Periodo (dimensión Año)", "opts": _opts([""] + PERIODOS, a.get("periodo", ""), {"": "Todos los periodos"})},
            {"name": "region", "label": "Región natural (dimensión Territorio)", "opts": _opts([""] + REGIONES, a.get("region", ""), {"": "Todas las regiones"})},
        ],
        "niveles": [
            {"name": "nivel_t", "label": "Nivel de territorio", "opts": _opts(["region", "departamento"], nt, {"region": "Región natural", "departamento": "Departamento"})},
            {"name": "nivel_s", "label": "Nivel de semana", "opts": _opts(["trimestre", "semana"], ns, {"trimestre": "Trimestre epidemiológico", "semana": "Semana epidemiológica"})},
            {"name": "min_casos", "label": "Casos mínimos por unidad", "opts": _opts(["0", "5000", "20000"], str(min_casos), {"0": "Sin mínimo", "5000": "≥ 5.000", "20000": "≥ 20.000"})},
        ],
        "modo": None, "pivot": pivot, "ocultos": {},
    }
    return ctx


# =============================================================================== VISTA 4
def gravedad(a):
    nt = a.get("nivel_t", "departamento")
    nt = nt if nt in ("region", "departamento") else "departamento"
    na = a.get("nivel_a", "periodo")
    na = na if na in ("periodo", "anio") else "periodo"
    filtros = _filtros(a, ["fuente", "region", "periodo"])
    try:
        min_den = int(a.get("min_den", 2000))
    except ValueError:
        min_den = 2000
    pivot = a.get("pivot") == "1"
    info = [f"Nivel de territorio: {C.NIVELES[nt]['etiqueta']}", f"Nivel de tiempo: {C.NIVELES[na]['etiqueta']}",
            "Evento: dengue grave / (dengue + dengue grave)"]
    ctx = _base("gravedad", a, filtros, pivot, info)

    glob = C.consulta([], "pct_grave", filtros)
    if glob.empty or pd.isna(glob.valor.iloc[0]):
        ctx["sin_datos"] = True
        return ctx
    pg, num, den = float(glob.valor.iloc[0]), float(glob.num.iloc[0]), float(glob.den.iloc[0])
    por_per = C.consulta([nt, "periodo"], "pct_grave", filtros)
    den_u = por_per.groupby(nt).den.sum()
    validas = set(den_u[den_u >= min_den].index)
    perf = sorted(por_per.periodo.unique())
    primero, ultimo = perf[0], perf[-1]
    pv = por_per.pivot(index=nt, columns="periodo", values="valor")
    dpv = por_per.pivot(index=nt, columns="periodo", values="den")
    if len(perf) >= 2:
        elegibles = [u for u in pv.index if (dpv.loc[u, primero] or 0) >= min_den]
        bajan = [u for u in elegibles if pv.loc[u, ultimo] < pv.loc[u, primero]]
        ind3 = {"valor": f"{len(bajan)} de {len(elegibles)}",
                "titulo": f"{PLURAL[nt].capitalize()} con % menor en {ultimo} que en {primero}",
                "nota": f"Solo unidades con al menos {fm(min_den)} casos de dengue en {primero}."}
    else:
        elegibles, bajan = [], []
        ind3 = {"valor": "–", "titulo": "Unidades con descenso entre periodos",
                "nota": "Requiere al menos dos periodos: quite el filtro de periodo."}
    ctx["indicadores"] = [
        {"valor": fp(pg, 2), "titulo": "% de dengue grave en la selección",
         "nota": f"{fm(num)} casos de dengue grave / {fm(den)} casos de dengue + dengue grave."},
        {"valor": fm(den), "titulo": "Casos de dengue y dengue grave (denominador)",
         "nota": f"De ellos {fm(num)} son dengue grave. Es el denominador del porcentaje."},
        ind3,
    ]
    # graficas
    anual = C.consulta(["anio", nt], "pct_grave", filtros)
    den_tot = anual.groupby(nt).den.sum().sort_values(ascending=False)
    top = [u for u in den_tot.index if u in validas][:6]
    anios = sorted(anual.anio.unique())
    ds = []
    for i, u in enumerate(top):
        s = anual[anual[nt] == u].set_index("anio").valor
        ds.append({"label": bonito(u), "data": [None if pd.isna(s.get(y)) else round(float(s.get(y)), 2) for y in anios],
                   "color": COLOR_REGION.get(u, PALETA[i % len(PALETA)])})
    nac_a = C.consulta(["anio"], "pct_grave", filtros).set_index("anio").valor
    ds.insert(0, {"label": "Colombia (selección)", "data": [round(float(nac_a.get(y)), 2) if y in nac_a.index and not pd.isna(nac_a.get(y)) else None for y in anios],
                  "color": "#0f172a", "dash": True})
    ctx["graficas"] = [
        {"id": "g1", "tipo": "line", "titulo": f"% de dengue grave por año (6 unidades con más dengue y referencia nacional)",
         "labels": [str(y) for y in anios], "datasets": ds, "ytitle": "% de dengue grave (sobre dengue + dengue grave)", "xtitle": "Año",
         "nota": "El porcentaje se recalcula en cada año y unidad (casos de dengue grave / casos de dengue); no se promedian porcentajes."},
    ]
    if len(perf) >= 2 and elegibles:
        orden = sorted(elegibles, key=lambda u: -pv.loc[u, primero])[:15]
        ctx["graficas"].append({
            "id": "g2", "tipo": "bar", "horizontal": True,
            "titulo": f"% de dengue grave: {primero} frente a {ultimo} ({PLURAL[nt]} con ≥ {fm(min_den)} casos de dengue en {primero})",
            "labels": [bonito(u) for u in orden],
            "datasets": [{"label": primero, "data": [round(float(pv.loc[u, primero]), 2) for u in orden], "color": "#f59e0b"},
                         {"label": ultimo, "data": [round(float(pv.loc[u, ultimo]), 2) if not pd.isna(pv.loc[u, ultimo]) else None for u in orden], "color": "#0284c7"}],
            "ytitle": "% de dengue grave", "nota": "Las unidades donde la barra azul no es menor que la ámbar son las excepciones al descenso."})
    else:
        ctx["graficas"].append({"id": "g2", "tipo": "bar", "titulo": "% de dengue grave por unidad (un solo periodo seleccionado)",
                                "labels": [bonito(u) for u in pv.index if u in validas],
                                "datasets": [{"label": primero, "data": [round(float(pv.loc[u, primero]), 2) for u in pv.index if u in validas], "color": "#0284c7"}],
                                "ytitle": "% de dengue grave", "nota": "Quite el filtro de periodo para comparar el primer y el último periodo."})
    # matriz
    if pivot:
        m = C.matriz(na, nt, "pct_grave", filtros, "valor", max_cols=10)
        etq = f"{C.NIVELES[nt]['etiqueta']} (top 10)"
    else:
        m = C.matriz(nt, na, "pct_grave", filtros, "valor", min_den=min_den)
        etq = C.NIVELES[na]["etiqueta"]
    link = None
    if nt == "region" and not pivot:
        link = lambda etiqueta: dict({k: v[0] for k, v in filtros.items()}, nivel_t="departamento", region=etiqueta, nivel_a=na)
    tabla = _tabla(m, "pct_grave", "valor", etq, link, umbral_den=300)
    tabla["titulo"] = f"{C.NIVELES[nt]['etiqueta']} × {C.NIVELES[na]['etiqueta']} · % de dengue grave"
    tabla["denominador"] = ("Cada celda = dengue grave / (dengue + dengue grave) en esa celda; el total de fila y de columna se recalcula "
                            "con su propia consulta (no es suma ni promedio de celdas). * = menos de 300 casos de dengue en la celda: interprete con cautela. "
                            f"Se ocultan {m.get('ocultas_den', 0)} unidades con menos de {fm(min_den)} casos de dengue.")
    ctx["matriz"] = tabla
    ctx["lectura"] = (
        f"El dengue grave es {fp(pg, 2)} de los {fm(den)} casos de dengue de la selección. "
        + (f"{len(bajan)} de {len(elegibles)} unidades con suficiente dengue en {primero} tienen un porcentaje menor en {ultimo}; "
           f"las excepciones merecen revisión." if elegibles else "Seleccione más de un periodo para ver el cambio."))
    ctx["controles"] = {
        "ayuda": "Cambie el nivel de territorio y de tiempo (drill-down / roll-up), filtre por región o periodo (slice / dice) y pivote la matriz.",
        "selects": [
            {"name": "fuente", "label": "Fuente de casos", "opts": _opts(FUENTES_CASOS, filtros["fuente"][0])},
            {"name": "region", "label": "Región natural (dimensión Territorio)", "opts": _opts([""] + REGIONES, a.get("region", ""), {"": "Todas las regiones"})},
            {"name": "periodo", "label": "Periodo (dimensión Año)", "opts": _opts([""] + PERIODOS, a.get("periodo", ""), {"": "Todos los periodos"})},
        ],
        "niveles": [
            {"name": "nivel_t", "label": "Nivel de territorio", "opts": _opts(["region", "departamento"], nt, {"region": "Región natural", "departamento": "Departamento"})},
            {"name": "nivel_a", "label": "Nivel de tiempo", "opts": _opts(["periodo", "anio"], na, {"periodo": "Periodo", "anio": "Año"})},
            {"name": "min_den", "label": "Casos mínimos de dengue por unidad", "opts": _opts(["0", "2000", "10000"], str(min_den), {"0": "Sin mínimo", "2000": "≥ 2.000", "10000": "≥ 10.000"})},
        ],
        "modo": None, "pivot": pivot, "ocultos": {},
    }
    return ctx


def brotes(a):
    """Vista de brotes OMS/HDX, sin mezclar su unidad con los casos SIVIGILA."""
    niveles = {
        "periodo": ("d.periodo", "Periodo de brotes"),
        "anio": ("d.anio", "Año"),
        "region": ("t.region", "Región OMS"),
        "pais": ("t.area", "País"),
        "enfermedad": ("e.enfermedad", "Enfermedad"),
        "evento": ("e.evento", "Evento CIE-10 OMS"),
    }
    nivel = a.get("nivel", "region")
    if nivel not in niveles:
        nivel = "region"

    con = C._con()
    try:
        periodos = [r[0] for r in con.execute(
            "SELECT DISTINCT d.periodo FROM fact_notificacion f "
            "JOIN dim_tiempo d USING(tiempo_key) JOIN dim_fuente u USING(fuente_key) "
            "WHERE u.fuente='OMS/HDX' ORDER BY d.periodo"
        )]
        anios = [r[0] for r in con.execute(
            "SELECT DISTINCT d.anio FROM fact_notificacion f "
            "JOIN dim_tiempo d USING(tiempo_key) JOIN dim_fuente u USING(fuente_key) "
            "WHERE u.fuente='OMS/HDX' ORDER BY d.anio"
        )]
        regiones = [r[0] for r in con.execute(
            "SELECT DISTINCT t.region FROM fact_notificacion f "
            "JOIN dim_territorio t USING(territorio_key) JOIN dim_fuente u USING(fuente_key) "
            "WHERE u.fuente='OMS/HDX' ORDER BY t.region"
        )]
        enfermedades = [r[0] for r in con.execute(
            "SELECT DISTINCT e.enfermedad FROM fact_notificacion f "
            "JOIN dim_evento e USING(evento_key) JOIN dim_fuente u USING(fuente_key) "
            "WHERE u.fuente='OMS/HDX' ORDER BY e.enfermedad"
        )]

        filtros = []
        params = ["OMS/HDX"]
        anio = a.get("anio", "")
        if anio and anio.isdigit() and int(anio) in anios:
            filtros.append("d.anio = ?")
            params.append(int(anio))
        else:
            anio = ""
        region = a.get("region", "")
        if region in regiones:
            filtros.append("t.region = ?")
            params.append(region)
        else:
            region = ""
        enfermedad = a.get("enfermedad", "")
        if enfermedad in enfermedades:
            filtros.append("e.enfermedad = ?")
            params.append(enfermedad)
        else:
            enfermedad = ""
        where = " WHERE u.fuente = ?" + "".join(f" AND {condicion}" for condicion in filtros)
        base = (
            " FROM fact_notificacion f JOIN dim_tiempo d USING(tiempo_key) "
            "JOIN dim_territorio t USING(territorio_key) JOIN dim_evento e USING(evento_key) "
            "JOIN dim_fuente u USING(fuente_key)"
        )
        total, paises, eventos, desde, hasta = con.execute(
            "SELECT COALESCE(SUM(f.brotes), 0), COUNT(DISTINCT t.territorio_key), "
            "COUNT(DISTINCT f.evento_key), MIN(d.anio), MAX(d.anio)"
            + base + where,
            params,
        ).fetchone()
        expr, etiqueta = niveles[nivel]
        sql = (
            f"SELECT {expr} AS etiqueta, SUM(f.brotes) AS brotes"
            + base + where + f" GROUP BY {expr} ORDER BY brotes DESC, etiqueta"
        )
        resultado = pd.read_sql_query(sql, con, params=params)
        sql_legible = C.sql_legible(sql, params)
    finally:
        con.close()

    filas = [
        {"etiqueta": str(row.etiqueta), "brotes": int(row.brotes)}
        for row in resultado.itertuples(index=False)
    ]
    return {
        "meta": VISTAS_META["brotes"],
        "slug_activo": "olap-brotes",
        "cobertura": C.cobertura(),
        "nivel": nivel,
        "etiqueta_nivel": etiqueta,
        "anios": anios,
        "periodos": periodos,
        "regiones": regiones,
        "enfermedades": enfermedades,
        "seleccion": {"anio": anio, "region": region, "enfermedad": enfermedad},
        "filas": filas,
        "total": int(total),
        "paises": int(paises),
        "eventos": int(eventos),
        "desde": desde,
        "hasta": hasta,
        "labels": [row["etiqueta"] for row in filas[:25]],
        "data": [row["brotes"] for row in filas[:25]],
        "sql": sql_legible,
    }


VISTAS = {
    "concentracion": concentracion,
    "ciclos": ciclos,
    "estacionalidad": estacionalidad,
    "gravedad": gravedad,
    "brotes": brotes,
}
