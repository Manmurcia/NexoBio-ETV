"""
generar_plantillas_etapa2.py

Genera las plantillas Flask de perfilamiento (3) y dimensiones de calidad (4) a partir del
reporte producido por perfilamiento_etapa2.py y dimensiones_calidad.py, de modo que la web
muestre exactamente los mismos numeros que el informe.

USO (desde la raiz del repositorio):
    python scripts/perfilamiento_etapa2.py
    python scripts/dimensiones_calidad.py
    python scripts/generar_plantillas_etapa2.py
"""
import html, json, os
import pandas as pd

REPORTE = "reporte_perfilamiento"
SALIDA = os.path.join("templates", "etapa 2")

NOMBRES = {
    "sivigila_dengue": ("SIVIGILA Dengue", "sivigila_dengue.csv"),
    "perfil_epidemiologico_anual": ("Perfil Epidemiológico Anual", "PERFIL_EPIDEMIOLOGICO_ANUAL.csv"),
    "salud_cundinamarca": ("Indicadores de Salud Cundinamarca", "SALUD.xlsx"),
    "disease_outbreaks_hdx": ("Disease Outbreaks (HDX / OMS)", "disease_outbreaks_HDX.xlsx"),
    "vigilancia_colombia": ("Vigilancia en Salud Pública Colombia", "Datos_de_Vigilancia_en_Salud_Publica_de_Colombia.csv"),
    "ixodes_county_2023": ("Ixodes County (CDC, 7 hojas)", "Public_Use_Ixodes_County_Table_2023.xlsx"),
}
NOTAS = {
    "ixodes_county_2023": "Las 7 hojas de datos (2022, 2021, 2020, 2019, 2018, 2016 y 1996) se concatenaron; "
                          "'anio_hoja' es una columna agregada para identificar la hoja, por eso aparecen 8 columnas (7 originales + 1).",
    "salud_cundinamarca": "El encabezado real está en la fila 12 del Excel; las 11 filas previas son títulos institucionales y no se cuentan como registros.",
    "disease_outbreaks_hdx": "La fila 2 del Excel contiene etiquetas HXL (#Year+iso3+icd4...) y no es un registro; por eso son 3.566 registros y no 3.567.",
    "sivigila_dengue": "'SD' y 'SIN INFORMACION' se cuentan como valores faltantes (ver NULL_TOKENS_GLOBAL en el script).",
    "perfil_epidemiologico_anual": "Los nombres de mes están en la columna CICLO DE VIDA y la columna MES contiene el texto 'ENFERMEDADES INFECCIOSAS Y PARASITARIAS' en todas las filas (columnas desalineadas).",
    "vigilancia_colombia": "El municipio 'DESCONOCIDO' se cuenta como faltante (patrón en la columna Municipio_ocurrencia).",
}


def e(x):
    return html.escape(str(x))


def fmt(n):
    return f"{int(n):,}".replace(",", ".")


def num(v):
    if pd.isna(v):
        return "—"
    v = float(v)
    if abs(v) >= 1e6:
        return f"{v:.3e}"
    return f"{v:,.2f}".rstrip("0").rstrip(".").replace(",", "_").replace(".", ",").replace("_", ".") if v % 1 else fmt(v)


def pct_txt(v):
    """Porcentaje con coma decimal; usa 4 decimales si esta muy cerca de 100 pero no es 100."""
    txt = f"{v:.4f}" if 99.99 <= v < 100 else f"{v:.2f}"
    return txt.replace(".", ",") + "%"


def badge(p):
    if p is None:
        return "bg-info text-dark"
    return "bg-success" if p >= 98 else ("bg-warning text-dark" if p >= 90 else "bg-danger")


def pagina_perfilamiento(resumen, perfiles):
    tot_reg = int(resumen["filas"].sum())
    tot_dup = int(resumen["duplicados"].sum())
    tot_nul = int(resumen["total_nulos"].sum())
    o = []
    o.append("{% extends 'layout.html' %}\n\n{% block content %}")
    o.append('<h1 class="page-title">3. Perfilamiento del Conjunto de Datos</h1>')
    o.append(f'<p class="text-muted mt-2 mb-4">Resultados generados por <code>scripts/perfilamiento_etapa2.py</code> sobre {fmt(tot_reg)} registros de 6 fuentes. '
             'Los valores "SD", "SIN INFORMACION" y "MUNICIPIO DESCONOCIDO" se cuentan como faltantes.</p>')
    o.append('<div class="row g-3 mb-4">')
    for val, txt, cls in [(fmt(tot_reg), "Registros evaluados", "primary"), (fmt(tot_dup), "Duplicados exactos", "danger"),
                          (fmt(tot_nul), "Celdas faltantes", "warning"), ("6", "Fuentes analizadas", "info")]:
        o.append(f'<div class="col-6 col-md-3"><div class="p-3 border rounded text-center bg-white"><div class="fs-3 fw-bold text-{cls}">{val}</div><div class="small text-muted">{txt}</div></div></div>')
    o.append("</div>")

    o.append('<h5 class="fw-bold mb-3">Resumen por dataset</h5><div class="table-responsive mb-4"><table class="table table-bordered align-middle table-sm">')
    o.append('<thead class="table-light"><tr><th>Archivo</th><th>Registros</th><th>Variables</th><th>Duplicados</th><th>Celdas faltantes</th><th>Completitud</th></tr></thead><tbody>')
    for _, r in resumen.iterrows():
        nom, arch = NOMBRES[r["dataset"]]
        o.append(f'<tr><td><strong>{e(nom)}</strong><br><code class="small">{e(arch)}</code></td><td>{fmt(r["filas"])}</td><td>{int(r["columnas"])}</td>'
                 f'<td>{fmt(r["duplicados"])}</td><td>{fmt(r["total_nulos"])}</td><td><span class="badge {badge(r["completitud_pct"])}">{pct_txt(r["completitud_pct"])}</span></td></tr>')
    o.append("</tbody></table></div>")

    o.append('<h5 class="fw-bold mb-3">Perfilamiento por variable</h5>')
    o.append('<p class="text-muted small">Para cada variable: tipo de dato inferido, valores únicos, valores nulos (incluye placeholders) y estadísticas mínimo / máximo / promedio cuando la variable es numérica.</p>')
    o.append('<ul class="nav nav-pills mb-3" role="tablist">')
    for i, ds in enumerate(NOMBRES):
        o.append(f'<li class="nav-item"><button class="nav-link {"active" if i == 0 else ""}" data-bs-toggle="pill" data-bs-target="#perf-{ds}" type="button">{e(NOMBRES[ds][0])}</button></li>')
    o.append('</ul><div class="tab-content">')
    for i, ds in enumerate(NOMBRES):
        p = perfiles[ds]
        o.append(f'<div class="tab-pane fade {"show active" if i == 0 else ""}" id="perf-{ds}">')
        if ds in NOTAS:
            o.append(f'<div class="alert alert-light border small">{e(NOTAS[ds])}</div>')
        o.append('<div class="table-responsive"><table class="table table-bordered table-sm align-middle"><thead class="table-light"><tr>'
                 '<th>Variable</th><th>Tipo</th><th>Únicos</th><th>Nulos</th><th>% nulos</th><th>Mínimo</th><th>Máximo</th><th>Promedio</th></tr></thead><tbody>')
        for _, r in p.iterrows():
            cls = ' class="table-warning"' if r["pct_nulos"] >= 5 else ""
            o.append(f'<tr{cls}><td><code>{e(r["variable"])}</code></td><td>{e(r["tipo_dato"])}</td><td>{fmt(r["valores_unicos"])}</td><td>{fmt(r["nulos"])}</td>'
                     f'<td>{r["pct_nulos"]:.2f}%</td><td>{num(r.get("minimo"))}</td><td>{num(r.get("maximo"))}</td><td>{num(r.get("promedio"))}</td></tr>')
        o.append("</tbody></table></div></div>")
    o.append("</div>")
    o.append("{% endblock %}")
    return "\n".join(o)


def pagina_dimensiones(dim):
    o = ["{% extends 'layout.html' %}\n\n{% block content %}",
         '<h1 class="page-title">4. Evaluación de Dimensiones de Calidad por Dataset</h1>',
         '<p class="text-muted mt-2 mb-4">Seis dimensiones (completitud, exactitud, consistencia, unicidad, validez y actualidad) medidas con '
         '<code>scripts/dimensiones_calidad.py</code>. Cada tarjeta muestra la fórmula, el resultado y el detalle verificable.</p>',
         '<ul class="nav nav-pills mb-4" role="tablist">']
    for i, ds in enumerate(NOMBRES):
        o.append(f'<li class="nav-item"><button class="nav-link {"active" if i == 0 else ""}" data-bs-toggle="pill" data-bs-target="#dim-{ds}" type="button">{e(NOMBRES[ds][0])}</button></li>')
    o.append('</ul><div class="tab-content">')
    for i, ds in enumerate(NOMBRES):
        o.append(f'<div class="tab-pane fade {"show active" if i == 0 else ""}" id="dim-{ds}"><div class="row g-3">')
        for m in dim[ds]:
            p = m["resultado_pct"]
            etiqueta = "N/A" if p is None else f"{str(p).replace('.', ',')}%"
            o.append('<div class="col-md-6"><div class="p-3 border rounded h-100 bg-white">'
                     f'<div class="d-flex justify-content-between align-items-center mb-2"><h6 class="fw-bold mb-0">{e(m["dimension"])} — <code>{e(m["variable"])}</code></h6>'
                     f'<span class="badge {badge(p)} fs-6">{etiqueta}</span></div>'
                     f'<p class="mb-1 text-muted small"><strong>Métrica:</strong> <code>{e(m["formula"])}</code></p>'
                     f'<p class="mb-0 text-secondary small">{e(m["detalle"])}</p></div></div>')
        o.append("</div></div>")
    o.append("</div>\n{% endblock %}")
    return "\n".join(o)


def main():
    resumen = pd.read_csv(os.path.join(REPORTE, "resumen_global.csv"))
    perfiles = {ds: pd.read_csv(os.path.join(REPORTE, f"perfil_{ds}.csv")) for ds in NOMBRES}
    with open(os.path.join(REPORTE, "dimensiones_calidad.json"), encoding="utf-8") as f:
        dim = json.load(f)
    os.makedirs(SALIDA, exist_ok=True)
    with open(os.path.join(SALIDA, "3_perfilamiento.html"), "w", encoding="utf-8") as f:
        f.write(pagina_perfilamiento(resumen, perfiles))
    with open(os.path.join(SALIDA, "4_dimensiones.html"), "w", encoding="utf-8") as f:
        f.write(pagina_dimensiones(dim))
    print("Plantillas 3_perfilamiento.html y 4_dimensiones.html generadas en", SALIDA)


if __name__ == "__main__":
    main()
