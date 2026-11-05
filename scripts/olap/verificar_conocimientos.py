"""
verificar_conocimientos.py - Recalcula con consultas al modelo estrella las cifras citadas en los ocho
conocimientos multidimensionales (olap/conocimientos.py) y las compara con el texto.

USO (desde la raiz):  python scripts/olap/verificar_conocimientos.py
Sale con codigo 1 si alguna cifra no coincide.
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)
from olap import consultas as C  # noqa: E402

fallos = []


def chk(nombre, obtenido, esperado, dec=1):
    ok = round(obtenido, dec) == round(esperado, dec) if isinstance(esperado, float) else obtenido == esperado
    print(("OK   " if ok else "FALLA"), "|", nombre, "| obtenido:", obtenido if not isinstance(obtenido, float) else round(obtenido, 3), "| texto:", esperado)
    if not ok:
        fallos.append(nombre)


def celda(m, fila, col):
    j = m["columnas"].index(col)
    f = next(f for f in m["filas"] if f["etiqueta"] == fila)
    return f["celdas"][j]["v"]


# ---------------- 1.1
m = C.matriz("region", "evento", "casos", modo="pct_col")
chk("1.1 Andina % dengue grave", celda(m, "Andina", "DENGUE GRAVE"), 59.7)
chk("1.1 Andina % dengue", celda(m, "Andina", "DENGUE"), 46.6)
chk("1.1 Orinoquia % chagas", celda(m, "Orinoquia", "CHAGAS"), 33.5)
chk("1.1 Pacifica % chik", celda(m, "Pacifica", "CHIKUNGUNYA"), 23.5)
chk("1.1 Pacifica % dengue", celda(m, "Pacifica", "DENGUE"), 16.6)
chk("1.1 Pacifica % chagas", celda(m, "Pacifica", "CHAGAS"), 0.8)
rk = C.ranking("region")
chk("1.1 Andina % total", float(rk.set_index("region").loc["Andina", "pct"]), 46.45, 2)
chk("1.1 Orinoquia % total", float(rk.set_index("region").loc["Orinoquia", "pct"]), 11.09, 2)
m2 = C.matriz("region", "evento", "casos")
chk("1.1 casos Andina dengue grave", celda(m2, "Andina", "DENGUE GRAVE"), 25964.0)
chk("1.1 casos Orinoquia chagas", celda(m2, "Orinoquia", "CHAGAS"), 1631.0)
chk("1.1 total chagas", m2["total_columna"][m2["columnas"].index("CHAGAS")], 4871.0)
chk("1.1 total dengue grave", m2["total_columna"][m2["columnas"].index("DENGUE GRAVE")], 43461.0)
# ---------------- 1.2
esp = {"DENGUE GRAVE": (14, 820, "BUCARAMANGA (Santander)", 9.6), "CHAGAS": (16, 404, "VALLEDUPAR (Cesar)", 10.3),
       "DENGUE": (23, 1072, "CALI (Valle del Cauca)", 9.6), "CHIKUNGUNYA": (39, 875, "CALI (Valle del Cauca)", 5.7)}
for ev, (n50, n, lider, pct) in esp.items():
    r = C.ranking("municipio", filtros={"evento": [ev]})
    chk(f"1.2 {ev} municipios al 50 %", int((r.acum < 50).sum() + 1), n50)
    chk(f"1.2 {ev} unidades", len(r), n)
    chk(f"1.2 {ev} lider", r.iloc[0].municipio, lider)
    chk(f"1.2 {ev} % lider", float(r.iloc[0].pct), pct)
r = C.ranking("municipio")
chk("1.2 todos: unidades al 50 %", int((r.acum < 50).sum() + 1), 25)
chk("1.2 todos: unidades", len(r), 1078)
chk("1.2 10 % de unidades", float(r.pct.head(107).sum()), 73.56, 2)
# ---------------- 2.1
d = C.consulta(["departamento", "anio"]).pivot(index="departamento", columns="anio", values="valor").fillna(0)
pk = d.idxmax(axis=1)
chk("2.1 departamentos", len(pk), 33)
chk("2.1 años pico distintos", int(pk.nunique()), 10)
for y, n in {2010: 6, 2019: 9, 2014: 4, 2015: 4, 2016: 3, 2022: 3, 2008: 1, 2018: 1, 2020: 1, 2021: 1}.items():
    chk(f"2.1 departamentos con pico en {y}", int((pk == y).sum()), n)
chk("2.1 año pico nacional", int(d.sum().idxmax()), 2010)
# ---------------- 2.2
m = C.matriz("region", "tipo_anio", "casos", modo="pct_col")
chk("2.2 Andina % en años epidémicos", celda(m, "Andina", "Epidemico"), 50.9)
chk("2.2 Andina % en no epidémicos", celda(m, "Andina", "No epidemico"), 39.1)
chk("2.2 Caribe % epidémicos", celda(m, "Caribe", "Epidemico"), 18.4)
chk("2.2 Caribe % no epidémicos", celda(m, "Caribe", "No epidemico"), 28.3)
m = C.matriz("region", "anio", "casos", modo="pct_col")
chk("2.2 Caribe 2021", celda(m, "Caribe", 2021), 50.9)
chk("2.2 Caribe 2022", celda(m, "Caribe", 2022), 51.1)
chk("2.2 Andina 2021", celda(m, "Andina", 2021), 18.6)
chk("2.2 Andina 2022", celda(m, "Andina", 2022), 18.5)
m = C.matriz("region", "anio", "casos")
chk("2.2 Andina 2019", celda(m, "Andina", 2019), 52911.0)
chk("2.2 Andina 2022 casos", celda(m, "Andina", 2022), 12463.0)
chk("2.2 Caribe 2019", celda(m, "Caribe", 2019), 32496.0)
chk("2.2 Caribe 2022 casos", celda(m, "Caribe", 2022), 34321.0)
chk("2.2 Andina variación", 100 * (12463 / 52911 - 1), -76.4)
chk("2.2 Caribe variación", 100 * (34321 / 32496 - 1), 5.6)
chk("2.2 promedio anual usado para definir años epidémicos (Etapa 4: 79.334)", round(C.cobertura()["casos_totales"] / 16), 79334)
# ---------------- 3.1
F = {"evento": ["DENGUE"]}
nac, _, _ = C.indice_estacional(None, "trimestre", F)
v = [round(float(x), 1) for x in nac.iloc[0]]
chk("3.1 Colombia trimestres", v, [25.2, 25.4, 23.7, 25.8])
chk("3.1 amplitud Colombia", C.amplitud(nac.iloc[0]), 2.1)
r, _, _ = C.indice_estacional("region", "trimestre", F)
chk("3.1 Caribe T4", float(r.loc["Caribe"].iloc[3]), 34.7)
chk("3.1 Caribe T2", float(r.loc["Caribe"].iloc[1]), 16.9)
chk("3.1 Caribe amplitud", C.amplitud(r.loc["Caribe"]), 17.9)
chk("3.1 Orinoquia T2", float(r.loc["Orinoquia"].iloc[1]), 33.8)
chk("3.1 Orinoquia T4", float(r.loc["Orinoquia"].iloc[3]), 17.7)
chk("3.1 Orinoquia amplitud", C.amplitud(r.loc["Orinoquia"]), 16.1)
chk("3.1 Andina amplitud", C.amplitud(r.loc["Andina"]), 1.8)
for reg, sem in {"Caribe": 46, "Orinoquia": 21}.items():
    s, _, _ = C.indice_estacional("region", "semana", {"evento": ["DENGUE"], "region": [reg]})
    chk(f"3.1 semana pico {reg}", int(s.iloc[0].idxmax()), sem)
s, _, _ = C.indice_estacional(None, "semana", F)
chk("3.1 semana 49 nacional (Etapa 4: 2,13)", float(s.iloc[0][49]), 2.13, 2)
chk("3.1 semana 12 nacional (Etapa 4: 1,68)", float(s.iloc[0][12]), 1.68, 2)
# ---------------- 3.2
d, cs, _ = C.indice_estacional("departamento", "trimestre", F, min_casos=20000)
chk("3.2 unidades con >= 20.000", len(d), 17)
amp = d.apply(C.amplitud, axis=1)
chk("3.2 Atlántico amplitud", float(amp["Atlántico"]), 27.2)
chk("3.2 Atlántico T4", float(d.loc["Atlántico"].iloc[3]), 40.3)
chk("3.2 Atlántico T2", float(d.loc["Atlántico"].iloc[1]), 13.2)
chk("3.2 Casanare amplitud", float(amp["Casanare"]), 20.1)
chk("3.2 Casanare T2", float(d.loc["Casanare"].iloc[1]), 36.6)
chk("3.2 Casanare T4", float(d.loc["Casanare"].iloc[3]), 16.5)
chk("3.2 Magdalena amplitud", float(amp["Magdalena"]), 18.3)
chk("3.2 Bolívar amplitud", float(amp["Bolívar"]), 17.8)
chk("3.2 Cundinamarca amplitud", float(amp["Cundinamarca"]), 4.2)
chk("3.2 Cundinamarca trimestres", [round(float(x), 1) for x in d.loc["Cundinamarca"].iloc[:4]], [26.4, 25.4, 22.2, 26.0])
chk("3.2 Quindío amplitud", float(amp["Quindío"]), 2.9)
chk("3.2 amplitud mínima es Quindío", amp.idxmin(), "Quindío")
# ---------------- 4.1
p = C.ranking("periodo", "pct_grave").set_index("periodo").valor
chk("4.1 nacional 2007-2010", float(p["2007-2010"]), 9.69, 2)
chk("4.1 nacional 2011-2016", float(p["2011-2016"]), 2.08, 2)
chk("4.1 nacional 2017-2022", float(p["2017-2022"]), 1.34, 2)
m = C.matriz("region", "periodo", "pct_grave")
chk("4.1 Andina 2007-2010", celda(m, "Andina", "2007-2010"), 11.42, 2)
chk("4.1 Andina 2017-2022", celda(m, "Andina", "2017-2022"), 1.10, 2)
chk("4.1 Caribe 2007-2010", celda(m, "Caribe", "2007-2010"), 5.32, 2)
chk("4.1 Caribe 2017-2022", celda(m, "Caribe", "2017-2022"), 2.12, 2)
chk("4.1 razón Andina/Caribe 2007-2010", celda(m, "Andina", "2007-2010") / celda(m, "Caribe", "2007-2010"), 2.1)
chk("4.1 razón Andina/Caribe 2017-2022", celda(m, "Andina", "2017-2022") / celda(m, "Caribe", "2017-2022"), 0.5)
md = C.matriz("departamento", "periodo", "pct_grave")
den = C.consulta(["departamento", "periodo"], "pct_grave").pivot(index="departamento", columns="periodo", values="den")
elig = [f["etiqueta"] for f in md["filas"] if (den.loc[f["etiqueta"], "2007-2010"] or 0) >= 2000]
chk("4.1 departamentos con >= 2.000 casos de dengue en 2007-2010", len(elig), 23)
bajan = [u for u in elig if celda(md, u, "2017-2022") < celda(md, u, "2007-2010")]
chk("4.1 bajan 2007-2010 -> 2017-2022", len(bajan), 22)
chk("4.1 única excepción", [u for u in elig if u not in bajan], ["Atlántico"])
for u, a_, b_ in [("Santander", 20.99, 0.67), ("Huila", 22.36, 2.29), ("Atlántico", 1.57, 2.40)]:
    chk(f"4.1 {u} 2007-2010", celda(md, u, "2007-2010"), a_, 2)
    chk(f"4.1 {u} 2017-2022", celda(md, u, "2017-2022"), b_, 2)
top4 = sorted(elig, key=lambda u: -celda(md, u, "2017-2022"))[:4]
chk("4.1 cuatro más altos en 2017-2022", sorted(top4), sorted(["Bolívar", "La Guajira", "Magdalena", "Atlántico"]))
chk("4.1 Bolívar 2017-2022", celda(md, "Bolívar", "2017-2022"), 2.52, 2)
chk("4.1 La Guajira 2017-2022", celda(md, "La Guajira", "2017-2022"), 2.51, 2)
chk("4.1 Magdalena 2017-2022", celda(md, "Magdalena", "2017-2022"), 2.42, 2)
# ---------------- 4.2
ma = C.matriz("departamento", "anio", "pct_grave")
for u, y, v_ in [("Antioquia", 2007, 26.9), ("Antioquia", 2008, 6.8), ("Norte de Santander", 2009, 23.9), ("Norte de Santander", 2010, 10.6),
                 ("Norte de Santander", 2011, 4.1), ("Santander", 2009, 27.0), ("Santander", 2010, 12.0), ("Santander", 2011, 5.1),
                 ("Huila", 2009, 27.9), ("Huila", 2010, 16.3), ("Huila", 2011, 12.4), ("Huila", 2012, 2.8)]:
    chk(f"4.2 {u} {y}", celda(ma, u, y), v_)
at = [celda(ma, "Atlántico", y) for y in range(2007, 2023)]
chk("4.2 Atlántico mínimo", min(at), 0.6)
chk("4.2 Atlántico máximo", max(at), 3.5)

print(f"\n{'TODAS LAS CIFRAS COINCIDEN' if not fallos else str(len(fallos)) + ' cifras NO coinciden: ' + ', '.join(fallos)}")
sys.exit(1 if fallos else 0)
