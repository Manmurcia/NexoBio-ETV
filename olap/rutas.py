"""rutas.py - Blueprint 'Análisis multidimensional' (Etapa 5)."""
import json
import os

import pandas as pd
from flask import Blueprint, abort, redirect, render_template, request, url_for

from . import asegurar_bd, consultas as C
from .conocimientos import CONOCIMIENTOS, VISTAS_META
from .vistas import VISTAS, bonito, fm, fp

bp = Blueprint("olap", __name__, url_prefix="/analisis-multidimensional")

SECCIONES = {
    "proposito": "etapa 5/1_proposito.html",
    "modelo": "etapa 5/2_modelo.html",
    "validaciones": "etapa 5/3_validaciones.html",
    "operaciones": "etapa 5/4_operaciones.html",
    "conocimientos": "etapa 5/9_conocimientos.html",
}
ORDEN_VISTAS = ["concentracion", "ciclos", "estacionalidad", "gravedad", "brotes"]
ORDEN_CONOCIMIENTOS = ["concentracion", "ciclos", "estacionalidad", "gravedad"]


@bp.record_once
def _al_registrar(estado):
    asegurar_bd()


@bp.app_template_filter("miles")
def _miles(v):
    return fm(v)


@bp.route("/")
def inicio():
    return redirect(url_for("olap.seccion", seccion="proposito"))


@bp.route("/<seccion>")
def seccion(seccion):
    plantilla = SECCIONES.get(seccion)
    if not plantilla:
        abort(404)
    ctx = {
        "slug_activo": f"olap-{seccion}", "cob": C.cobertura(),
        "metas": VISTAS_META, "orden": ORDEN_VISTAS,
        "orden_conocimientos": ORDEN_CONOCIMIENTOS,
    }
    if seccion == "modelo":
        ctx.update(_ctx_modelo())
    elif seccion == "validaciones":
        ctx.update(_ctx_validaciones())
    elif seccion == "operaciones":
        ctx.update(_ctx_operaciones())
    elif seccion == "conocimientos":
        ctx["conocimientos"] = CONOCIMIENTOS
    return render_template(plantilla, **ctx)


@bp.route("/vista/<vista>")
def vista(vista):
    fn = VISTAS.get(vista)
    if not fn:
        abort(404)
    ctx = fn(request.args.to_dict())
    pos = ORDEN_VISTAS.index(vista)
    if vista == "concentracion":
        ctx.update({
            "slug_activo": f"olap-{vista}",
            "orden": ORDEN_VISTAS,
            "metas": VISTAS_META,
            "anterior": None,
            "siguiente": ORDEN_VISTAS[pos + 1],
        })
        return render_template("etapa 5/vista_fuentes.html", **ctx)
    if vista == "brotes":
        ctx.update({
            "slug_activo": f"olap-{vista}",
            "vid": vista,
            "orden": ORDEN_VISTAS,
            "metas": VISTAS_META,
            "anterior": ORDEN_VISTAS[pos - 1] if pos > 0 else None,
            "siguiente": ORDEN_VISTAS[pos + 1] if pos < len(ORDEN_VISTAS) - 1 else None,
        })
        return render_template("etapa 5/vista_brotes.html", **ctx)
    ctx.update({
        "slug_activo": f"olap-{vista}", "vid": vista, "orden": ORDEN_VISTAS, "metas": VISTAS_META,
        "anterior": ORDEN_VISTAS[pos - 1] if pos > 0 else None,
        "siguiente": ORDEN_VISTAS[pos + 1] if pos < len(ORDEN_VISTAS) - 1 else None,
    })
    return render_template("etapa 5/vista.html", **ctx)


# ------------------------------------------------------------------------------------------------
def _ctx_modelo():
    import sqlite3
    con = sqlite3.connect(f"file:{C.DB}?mode=ro", uri=True)
    try:
        n = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
             for t in ("dim_evento", "dim_territorio", "dim_tiempo", "dim_fuente", "fact_notificacion")}
        n["departamentos"] = con.execute(
            "SELECT COUNT(DISTINCT cod_departamento) FROM dim_territorio "
            "WHERE ambito='Colombia' AND cod_departamento NOT IN ('0','1')"
        ).fetchone()[0]
        n["casos_nacionales"] = con.execute(
            "SELECT COALESCE(SUM(f.casos),0) FROM fact_notificacion f "
            "JOIN dim_fuente u USING(fuente_key) WHERE u.fuente='SIVIGILA Colombia'"
        ).fetchone()[0]
        n["casos_regionales"] = con.execute(
            "SELECT COALESCE(SUM(f.casos),0) FROM fact_notificacion f "
            "JOIN dim_fuente u USING(fuente_key) WHERE u.fuente='SIVIGILA Cundinamarca'"
        ).fetchone()[0]
        n["brotes"] = con.execute(
            "SELECT COALESCE(SUM(f.brotes),0) FROM fact_notificacion f "
            "JOIN dim_fuente u USING(fuente_key) WHERE u.fuente='OMS/HDX'"
        ).fetchone()[0]
        n["fuentes"] = dict(con.execute(
            "SELECT u.fuente, COUNT(*) FROM fact_notificacion f "
            "JOIN dim_fuente u USING(fuente_key) GROUP BY u.fuente"
        ))
    finally:
        con.close()
    return {"n": n, "medidas": C.MEDIDAS}


def _ctx_validaciones():
    ruta = os.path.join(os.path.dirname(C.DB), "validaciones.json")
    if not os.path.exists(ruta):
        return {"val": None}
    datos = json.load(open(ruta, encoding="utf-8"))

    def resumen(x):
        if isinstance(x, dict):
            try:
                return f"{len(x)} grupos · suma {fm(sum(x.values()))}"
            except TypeError:
                return f"{len(x)} grupos"
        if isinstance(x, (int, float)) and not isinstance(x, bool):
            return fm(x, 0 if float(x).is_integer() else 2)
        return str(x)

    grupos = {}
    for r in datos["validaciones"]:
        r = dict(r, esperado_t=resumen(r["esperado"]), obtenido_t=resumen(r["obtenido"]))
        grupos.setdefault(r["grupo"], []).append(r)
    total = len(datos["validaciones"])
    return {"val": datos, "grupos": grupos, "n_total": total, "n_ok": sum(1 for r in datos["validaciones"] if r["ok"])}


def _tabla_df(df, columnas, formatos=None):
    formatos = formatos or {}
    filas = []
    for _, r in df.iterrows():
        filas.append([formatos.get(c, lambda v: v)(r[c]) for c in columnas])
    return filas


def _ctx_operaciones():
    ops = []

    # 1. DRILL-DOWN: region Andina -> departamentos
    reg = C.consulta(["region"], "casos").sort_values("valor", ascending=False)
    d1 = C.ranking("departamento", filtros={"region": ["Andina"]}).head(5)
    ops.append({
        "id": "drill", "nombre": "Drill-down", "icono": "↓",
        "que": "Descender un nivel dentro de una jerarquía: de región natural a departamento (y luego a municipio).",
        "dims": "Territorio (región → departamento). Medida: casos notificados (suma).",
        "nivel": "Antes: región natural. Después: departamento dentro de la región Andina.",
        "sql": d1.attrs["sql"],
        "tabla": {"cab": ["Departamento (región Andina)", "Casos", "% de la región"],
                  "filas": [[bonito(r.departamento), fm(r.valor), fp(r.pct, 1)] for r in d1.itertuples()]},
        "lectura": f"La región Andina suma {fm(reg.set_index('region').loc['Andina', 'valor'])} casos; al descender, {bonito(d1.iloc[0].departamento)} concentra {fp(d1.iloc[0].pct, 1)} de ellos. El porcentaje usa como denominador los casos de la región Andina, no los del país: al cambiar de nivel el denominador cambia.",
        "enlace": ("concentracion", {"nivel": "departamento", "region": "Andina"}),
    })

    # 2. ROLL-UP: departamentos del Caribe -> region (razon recalculada, no promedio)
    dep = C.consulta(["departamento", "periodo"], "pct_grave", {"region": ["Caribe"]})
    dep = dep[dep.periodo == "2017-2022"].sort_values("valor", ascending=False)
    caribe = C.consulta(["periodo"], "pct_grave", {"region": ["Caribe"]})
    cr = caribe[caribe.periodo == "2017-2022"].iloc[0]
    ingenuo = float(dep.valor.mean())
    ops.append({
        "id": "roll", "nombre": "Roll-up", "icono": "↑",
        "que": "Subir un nivel de la jerarquía: agrupar los departamentos en su región.",
        "dims": "Territorio (departamento → región) × Año (periodo 2017–2022) × Evento. Medida: % de dengue grave (razón).",
        "nivel": "Antes: departamento. Después: región Caribe.",
        "sql": caribe.attrs["sql"],
        "tabla": {"cab": ["Departamento del Caribe, 2017–2022", "Dengue grave", "Dengue + dengue grave", "% de dengue grave"],
                  "filas": [[bonito(r.departamento), fm(r.num), fm(r.den), fp(r.valor, 2)] for r in dep.itertuples()]
                  + [["REGIÓN CARIBE (recalculado)", fm(cr.num), fm(cr.den), fp(cr.valor, 2)]]},
        "lectura": f"El porcentaje de la región se recalcula con la suma de casos de dengue grave sobre la suma de casos de dengue ({fm(cr.num)} / {fm(cr.den)} = {fp(cr.valor, 2)}). Promediar los porcentajes de los {len(dep)} departamentos daría {fp(ingenuo, 2)}, un valor distinto porque ignora cuántos casos aporta cada uno: por eso las razones nunca se suman ni se promedian al subir de nivel.",
        "enlace": ("gravedad", {"nivel_t": "region", "nivel_a": "periodo", "region": "Caribe"}),
    })

    # 3. SLICE: un valor de una dimension
    s = C.ranking("region", filtros={"evento": ["CHAGAS"]})
    ops.append({
        "id": "slice", "nombre": "Slice", "icono": "▮",
        "que": "Fijar UN valor de UNA dimensión para estudiar un subconjunto: aquí, solo el evento chagas.",
        "dims": "Evento (= CHAGAS) × Territorio (región). Medida: casos notificados.",
        "nivel": "Filtro: Evento = CHAGAS. Nivel de territorio: región natural.",
        "sql": s.attrs["sql"],
        "tabla": {"cab": ["Región natural", "Casos de chagas", "% de los casos de chagas"],
                  "filas": [[bonito(r.region), fm(r.valor), fp(r.pct, 1)] for r in s.itertuples()]},
        "lectura": f"El subconjunto tiene {fm(s.valor.sum())} casos de chagas. La Andina ({fp(s.iloc[0].pct, 1)}) y la Orinoquía ({fp(s.set_index('region').loc['Orinoquia', 'pct'], 1)}) reúnen casi tres cuartas partes; en el Pacífico casi no hay. El denominador es el total de chagas, no el total de casos.",
        "enlace": ("concentracion", {"nivel": "region", "evento": "CHAGAS"}),
    })

    # 4. DICE: filtros sobre 2+ dimensiones
    d = C.ranking("departamento", filtros={"region": ["Caribe"], "periodo": ["2017-2022"], "evento": ["DENGUE"]}).head(5)
    ops.append({
        "id": "dice", "nombre": "Dice", "icono": "▦",
        "que": "Seleccionar un subcubo combinando filtros de dos o más dimensiones.",
        "dims": "Territorio (región = Caribe) × Año (periodo = 2017–2022) × Evento (= dengue). Medida: casos.",
        "nivel": "Tres filtros simultáneos; nivel de territorio: departamento.",
        "sql": d.attrs["sql"],
        "tabla": {"cab": ["Departamento (Caribe · 2017–2022 · dengue)", "Casos", "% del subcubo"],
                  "filas": [[bonito(r.departamento), fm(r.valor), fp(r.pct, 1)] for r in d.itertuples()]},
        "lectura": f"El subcubo reúne {fm(C.total('casos', {'region': ['Caribe'], 'periodo': ['2017-2022'], 'evento': ['DENGUE']}))} casos de dengue del Caribe en 2017–2022. {bonito(d.iloc[0].departamento)} lidera con {fp(d.iloc[0].pct, 1)} del subcubo.",
        "enlace": ("ciclos", {"nivel_t": "departamento", "region": "Caribe", "evento": "DENGUE", "nivel_a": "periodo"}),
    })

    # 5. PIVOT
    m1 = C.matriz("region", "evento", "casos", modo="pct_col")
    m2 = C.matriz("evento", "region", "casos", modo="pct_fila")
    ops.append({
        "id": "pivot", "nombre": "Pivot", "icono": "⇄",
        "que": "Intercambiar filas y columnas de la matriz para leer los mismos datos desde otra perspectiva.",
        "dims": "Territorio (región) × Evento. Medida: casos; % de columna antes del pivot, % de fila después.",
        "nivel": "Misma información, distinta disposición; el denominador del porcentaje cambia con la orientación.",
        "sql": C.consulta(["region", "evento"], "casos").attrs["sql"],
        "tabla": {"cab": ["Antes: región (fila) × evento (columna), % de la columna"] + [c for c in m1["columnas"]],
                  "filas": [[bonito(f["etiqueta"])] + [fp(c["v"], 1) for c in f["celdas"]] for f in m1["filas"]]},
        "tabla2": {"cab": ["Después: evento (fila) × región (columna), % de la fila"] + [bonito(c) for c in m2["columnas"]],
                   "filas": [[f["etiqueta"]] + [fp(c["v"], 1) for c in f["celdas"]] for f in m2["filas"]]},
        "lectura": "En la primera matriz cada columna suma 100 % (reparto de un evento entre regiones). En la segunda cada fila suma 100 % (qué regiones componen cada evento). Son dos preguntas distintas con los mismos casos: el pivot cambia el denominador además de la disposición.",
        "enlace": ("concentracion", {"nivel": "region", "pivot": "1", "modo": "pct_col"}),
    })
    return {"ops": ops}
