"""
verificar_etapa4.py

Calcula con pandas los valores que deben mostrar las medidas DAX del informe de Power BI (Etapa 4)
usando los cuatro archivos resultantes del ETL de la Etapa 3 (powerbi/datos/). Sirve para comprobar
que Power BI calcula bien. No genera archivos ni paginas.

USO (desde la raiz del repositorio):
    python scripts/verificar_etapa4.py
"""
import os
import pandas as pd

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(RAIZ, "powerbi", "datos")
rd = lambda f: pd.read_csv(os.path.join(D, f), dtype=str, keep_default_na=False)
n = lambda x: f"{x:,.0f}".replace(",", ".")
p = lambda x, d=2: f"{x:.{d}f}".replace(".", ",") + " %"


def titulo(t):
    print("\n" + "=" * 8, t, "=" * 8)


# ---------------------------------------------------------------- carga
cund = rd("Datos_de_Vigilancia_Colombia_Limpio.csv")
nac = rd("Datos_de_Vigilancia_ColombiaCompleto_Limpio.csv")
reg = rd("Regional_Cundinamarca_ETV_Limpio.csv")
hdx = pd.read_excel(os.path.join(D, "Disease_Outbreaks_HDX_Limpio.xlsx"), dtype=str, keep_default_na=False)
for df in (cund, nac):
    df["conteo"] = df["conteo"].astype(int); df["ano"] = df["ano"].astype(int); df["semana"] = df["semana"].astype(int)
reg["conteo"] = reg["conteo"].astype(int); reg["anio"] = reg["anio"].astype(int)
reg["tasa"] = pd.to_numeric(reg["tasa de incidencia dengue"])
hdx["year"] = hdx["year"].astype(int)
cls_ev = rd("clasificacion_evento_vigilancia.csv"); cls_hdx = rd("clasificacion_enfermedad_hdx.csv"); dep = rd("dim_departamento.csv")

# ---------------------------------------------------------------- integridad del modelo (relaciones sin huerfanos ni claves repetidas)
titulo("Integridad de las relaciones")
checks = [("clasificacion_evento_vigilancia[nombre_evento] unico", cls_ev.nombre_evento.is_unique),
          ("fact Cundinamarca sin eventos huerfanos", cund.nombre_evento.isin(cls_ev.nombre_evento).all()),
          ("dim_departamento[cod_dpto_o] unico", dep.cod_dpto_o.is_unique),
          ("fact nacional sin departamentos huerfanos", nac.cod_dpto_o.isin(dep.cod_dpto_o).all()),
          ("clasificacion_enfermedad_hdx[icd103n] unico", cls_hdx.icd103n.is_unique),
          ("fact HDX sin enfermedades huerfanas", hdx.icd103n.isin(cls_hdx.icd103n).all()),
          ("claves duplicadas en nacional (evento, semana, ano, municipio)", not nac.duplicated(["cod_eve", "semana", "ano", "cod_mun_o"]).any()),
          ("claves duplicadas en Cundinamarca", not cund.duplicated(["cod_eve", "semana", "ano", "cod_mun_o"]).any()),
          ("id_outbreak unico en HDX", hdx.id_outbreak.is_unique)]
for t, ok in checks:
    print(("OK   " if ok else "FALLA"), t)

# ---------------------------------------------------------------- Tablero 1
titulo("Tablero 1 - Composicion (Cundinamarca, todos los eventos)")
c = cund.merge(cls_ev, on="nombre_evento")
T = c.conteo.sum(); etv = c[c.grupo_evento == "ETV"]
print("Casos Cundinamarca:", n(T), "| filas:", n(len(c)), "| eventos:", c.nombre_evento.nunique(), "| municipios:", c.municipio_ocurrencia.nunique())
print("Casos ETV:", n(etv.conteo.sum()), "| % casos ETV:", p(100 * etv.conteo.sum() / T))
ev = c.groupby("nombre_evento").conteo.sum().sort_values(ascending=False)
print("Top 10 eventos (% de casos):", [(k, n(v), p(100 * v / T)) for k, v in ev.head(10).items()])
print("Los 3 primeros suman:", p(100 * ev.head(3).sum() / T, 1), "| eventos con menos de 1 %:", int((100 * ev / T < 1).sum()))
ee = etv.groupby("nombre_evento").conteo.sum().sort_values(ascending=False)
print("Composicion dentro de ETV:", [(k, n(v), p(100 * v / ee.sum())) for k, v in ee.head(6).items()])
y = c.groupby("ano").conteo.sum(); ye = etv.groupby("ano").conteo.sum()
print("% ETV por anio:", {int(k): p(100 * ye.get(k, 0) / v, 1) for k, v in y.items()})
print("Casos por anio:", {int(k): n(v) for k, v in y.items()})
print("Eventos que ya se notificaban en 2007:", c[c.ano == 2007].nombre_evento.nunique(), "de", c.nombre_evento.nunique())
mm = etv.groupby("municipio_ocurrencia").conteo.sum().sort_values(ascending=False)
print("Municipio con mas casos (todos los eventos):", c.groupby("municipio_ocurrencia").conteo.sum().sort_values(ascending=False).head(3).to_dict())

# ---------------------------------------------------------------- Tablero 2
titulo("Tablero 2 - Territorios (Colombia completo + municipios de Cundinamarca)")
nd = nac.merge(dep, on="cod_dpto_o"); g = nd[nd.es_departamento == "Si"]; TD = g.conteo.sum()
print("Casos Colombia (todas las filas):", n(nd.conteo.sum()), "| Casos en departamentos:", n(TD), "| Exterior y procedencia desconocida:", n(nd.conteo.sum() - TD))
dd = g.groupby("nombre_mostrar").conteo.sum().sort_values(ascending=False)
print("Top 10 departamentos:", [(k, n(v), p(100 * v / TD)) for k, v in dd.head(10).items()])
print("% en los 5 primeros:", p(100 * dd.head(5).sum() / TD), "| 10 primeros:", p(100 * dd.head(10).sum() / TD), "| departamentos:", len(dd))
print("Cundinamarca: puesto", list(dd.index).index("Cundinamarca") + 1, "|", n(dd["Cundinamarca"]), "casos |", p(100 * dd["Cundinamarca"] / TD), "| Bogota:", n(dd["Bogotá D.C."]))
pv = g.pivot_table(index="nombre_mostrar", columns="nombre_evento", values="conteo", aggfunc="sum", fill_value=0)
pv["dengue_total"] = pv["DENGUE"] + pv["DENGUE GRAVE"]; pv["pct_grave"] = 100 * pv["DENGUE GRAVE"] / pv["dengue_total"]
print("% dengue grave (departamentos):", p(100 * pv["DENGUE GRAVE"].sum() / pv["dengue_total"].sum()), "| todas las filas:", p(100 * nd[nd.nombre_evento == "DENGUE GRAVE"].conteo.sum() / nd[nd.nombre_evento.isin(["DENGUE", "DENGUE GRAVE"])].conteo.sum()))
q = pv[pv.dengue_total >= 10000].sort_values("pct_grave", ascending=False)
print("Departamentos con >= 10.000 casos de dengue:", len(q), "| mayores:", [(k, p(r.pct_grave), n(r.dengue_total)) for k, r in q.head(3).iterrows()],
      "| menores:", [(k, p(r.pct_grave), n(r.dengue_total)) for k, r in q.tail(3).iterrows()], "| razon:", f"{q.pct_grave.max() / q.pct_grave.min():.1f}".replace(".", ","))
rd_ = reg[reg.evento == "DENGUE"]
mc = rd_.groupby("municipio").conteo.sum().sort_values(ascending=False)
print("Cundinamarca - casos de dengue por municipio:", n(mc.sum()), "| municipios:", len(mc), "| top:", [(k, n(v), p(100 * v / mc.sum(), 1)) for k, v in mc.head(6).items()], "| 10 primeros:", p(100 * mc.head(10).sum() / mc.sum(), 1))
td = rd_[rd_.tasa > 0].groupby("municipio").agg(tasa=("tasa", "mean"), anios=("tasa", "size"))
print("Tasa promedio (solo filas con dato) - municipios con tasa:", len(td), "| mayores:", [(k, n(r.tasa), int(r.anios)) for k, r in td.sort_values("tasa", ascending=False).head(4).iterrows()],
      "| Girardot:", n(td.loc["GIRARDOT", "tasa"]), "puesto", list(td.sort_values("tasa", ascending=False).index).index("GIRARDOT") + 1)
print("Filas de dengue sin tasa (0,0 = faltante):", int((rd_.tasa == 0).sum()), "de", len(rd_), p(100 * (rd_.tasa == 0).mean(), 1),
      "| 2007-2010:", int((rd_[rd_.anio <= 2010].tasa == 0).sum()), "de", len(rd_[rd_.anio <= 2010]), "| 2011-2022:", int((rd_[rd_.anio >= 2011].tasa == 0).sum()), "de", len(rd_[rd_.anio >= 2011]))
print("Cundinamarca coincide entre archivos (Colombia completo vs regional):", int(nd[nd.nombre_mostrar == "Cundinamarca"].conteo.sum()), "vs", int(reg.conteo.sum()))

# ---------------------------------------------------------------- Tablero 3
titulo("Tablero 3 - Tiempo (Colombia completo)")
t = nac.groupby("ano").conteo.sum()
print("Casos:", n(t.sum()), "| promedio anual:", n(t.mean()), "| pico:", t.idxmax(), n(t.max()), "| minimo:", t.idxmin(), n(t.min()), "| razon:", f"{t.max() / t.min():.1f}".replace(".", ","))
sobre = [int(a) for a in t[t > t.mean()].index]
print("Anios sobre el promedio:", sobre, p(100 * t[sobre].sum() / t.sum(), 1), "| casos por anio:", {int(k): n(v) for k, v in t.items()})
print("Variaciones: 2016->2017", p(100 * (t[2017] / t[2016] - 1), 1), "| 2019->2020", p(100 * (t[2020] / t[2019] - 1), 1), "| 2019->2022", p(100 * (t[2022] / t[2019] - 1), 1))
yy = nac.pivot_table(index="ano", columns="nombre_evento", values="conteo", aggfunc="sum", fill_value=0)
gr = 100 * yy["DENGUE GRAVE"] / (yy["DENGUE"] + yy["DENGUE GRAVE"])
print("% dengue grave por anio:", {int(k): p(v) for k, v in gr.items()})
print("Chikungunya primer anio:", int(yy.index[yy.CHIKUNGUNYA > 0].min()), "pico:", int(yy.CHIKUNGUNYA.idxmax()), n(yy.CHIKUNGUNYA.max()), "| Chagas primer anio:", int(yy.index[yy.CHAGAS > 0].min()))
w = nac[(nac.nombre_evento == "DENGUE") & (nac.semana <= 52)].pivot_table(index="semana", columns="ano", values="conteo", aggfunc="sum", fill_value=0)
a = (100 * w / w.sum()).mean(axis=1)
print("% semanal promedio (dengue, sem 1-52): max sem", int(a.idxmax()), p(a.max()), "| min sem", int(a.idxmin()), p(a.min()), "| sem 12:", p(a[12]), "| sem 50:", p(a[50]))
print("Bloques de 13 semanas:", {k: p(a[(a.index >= lo) & (a.index <= hi)].sum(), 1) for k, (lo, hi) in {"1-13": (1, 13), "14-26": (14, 26), "27-39": (27, 39), "40-52": (40, 52)}.items()}, "| semanas pico distintas:", len(set(w.idxmax().tolist())))

# ---------------------------------------------------------------- Tablero 4
titulo("Tablero 4 - Multivariado (brotes globales HDX, 1996-2025)")
print("Brotes en el archivo:", n(len(hdx)), "| de 2026 (anio incompleto, se excluyen):", int((hdx.year == 2026).sum()))
h = hdx[hdx.year <= 2025].merge(cls_hdx, on="icd103n")
h["region"] = h.who_region.replace("", "Sin región")
h["periodo"] = h.year.map(lambda y: "1996-2008" if y <= 2008 else "2009-2019" if y <= 2019 else "2020-2025")
N = len(h); E = h[h.es_etv == "Si"]
print("Brotes:", n(N), "| Brotes ETV:", n(len(E)), "| % ETV:", p(100 * len(E) / N), "| grupos:", {k: p(100 * v / N, 1) for k, v in h.grupo_enfermedad.value_counts().items()})
print("Brotes por region:", {k: n(v) for k, v in h.region.value_counts().items()})
print("% ETV por region:", {k: p(v, 1) for k, v in (100 * h.groupby("region").apply(lambda x: (x.es_etv == "Si").mean(), include_groups=False)).sort_values(ascending=False).items()})
print("Brotes por periodo:", h.periodo.value_counts().sort_index().to_dict(), "| ETV por periodo:", E.periodo.value_counts().sort_index().to_dict(),
      "| % ETV por periodo:", {k: p(v, 1) for k, v in (100 * h.groupby("periodo").apply(lambda x: (x.es_etv == "Si").mean(), include_groups=False)).items()})
m = 100 * h.pivot_table(index="region", columns="periodo", values="es_etv", aggfunc=lambda s: (s == "Si").mean())
c_ = h.pivot_table(index="region", columns="periodo", values="es_etv", aggfunc="size")
print("Matriz % ETV (region x periodo):\n", m.round(1).to_string(), "\nBrotes:\n", c_.to_string())
cov = h[(h.periodo == "2020-2025") & (h.grupo_enfermedad == "COVID-19 y uso de emergencia")]
print("COVID-19 en 2020-2025:", len(cov), p(100 * len(cov) / (h.periodo == "2020-2025").sum(), 1), "| % ETV 2020-2025 sin COVID:", p(100 * (E.periodo == "2020-2025").sum() / ((h.periodo == "2020-2025").sum() - len(cov)), 1))
print("Brotes por anio (mayores):", h.year.value_counts().head(4).to_dict(), "| 2009 por grupo:", h[h.year == 2009].grupo_enfermedad.value_counts().to_dict())
print("Distribucion % por grupo y region:\n", (100 * pd.crosstab(h.region, h.grupo_enfermedad, normalize="index")).round(1).to_string())
sr = h[h.region == "Sin región"]
print("Sin region:", len(sr), p(100 * len(sr) / N, 2), "| en 2020-2025:", int((sr.periodo == "2020-2025").sum()), "| paises:", sr.country.value_counts().head(4).to_dict())
