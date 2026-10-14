"""
dimensiones_calidad.py

Calcula las 6 dimensiones de calidad (completitud, exactitud, consistencia, unicidad,
validez, actualidad) sobre los 6 datasets del proyecto NexoBio-ETV y guarda
reporte_perfilamiento/dimensiones_calidad.json con cada metrica y su formula.

Reutiliza la configuracion y el tratamiento de nulos de perfilamiento_etapa2.py
("SD", "SIN INFORMACION", etc. cuentan como faltantes).

USO:  python dimensiones_calidad.py   (despues de perfilamiento_etapa2.py)
"""
import json, os
import pandas as pd
import perfilamiento_etapa2 as p

EDAD_MIN, EDAD_MAX = p.EDAD_MIN, p.EDAD_MAX
CFG = {c.nombre: c for c in p.CONFIG}


def pct(parte, total):
    """Porcentaje con 2 decimales; si no es exactamente 100 nunca se muestra como 100,00."""
    if not total:
        return None
    v = round(100 * parte / total, 2)
    if v == 100 and parte != total:
        v = round(100 * parte / total, 4)
        if v >= 100:
            v = 99.9999
    return v


def cargar(nombre):
    cfg = CFG[nombre]
    crudo = p.cargar_dataset(cfg)
    return crudo, p.normalizar_nulos(crudo, cfg)


def metrica(dimension, variable, formula, valor, detalle):
    return {"dimension": dimension, "variable": variable, "formula": formula,
            "resultado_pct": valor, "detalle": detalle}


def main():
    out = {}

    # ---------------- sivigila_dengue ----------------
    crudo, df = cargar("sivigila_dengue")
    n = len(df)
    celdas = df.size
    nulos = int(df.isna().sum().sum())
    nulos_crudo_sin_sd = int(crudo.eq("").sum().sum())
    edad = pd.to_numeric(df["edad_"], errors="coerce")
    fuera = int(((edad < EDAD_MIN) | (edad > EDAD_MAX)).sum())
    sexo_ok = int(df["sexo_"].isin(["M", "F"]).sum())
    out["sivigila_dengue"] = [
        metrica("Completitud", "toda la tabla", "(1 - celdas faltantes / celdas totales) x 100",
                pct(celdas - nulos, celdas),
                f"{nulos:,} celdas faltantes de {celdas:,} contando 'SD' y 'SIN INFORMACION' como faltantes; "
                f"sin contarlos solo habria {nulos_crudo_sin_sd:,} celdas vacias (el 100% anterior)"),
        metrica("Completitud", "cod_mun_d", "(valores distintos de SD / total) x 100",
                pct(n - int(df['cod_mun_d'].isna().sum()), n),
                f"{int(df['cod_mun_d'].isna().sum()):,} filas con 'SD'"),
        metrica("Exactitud", "edad_", f"(edades entre {EDAD_MIN} y {EDAD_MAX} / edades con valor) x 100",
                pct(int(edad.notna().sum()) - fuera, int(edad.notna().sum())),
                f"{fuera} edades fuera de rango: {sorted(edad[(edad < EDAD_MIN) | (edad > EDAD_MAX)].astype(int).tolist())}"),
        metrica("Validez", "sexo_", "(valores M o F / total) x 100", pct(sexo_ok, n),
                f"{n - sexo_ok} filas con valor distinto de M/F (SD)"),
        metrica("Unicidad", "fila completa", "(filas unicas / total) x 100",
                pct(n - int(df.duplicated().sum()), n), f"{int(df.duplicated().sum())} duplicados exactos"),
    ]
    anos = pd.to_numeric(df["year_"], errors="coerce")
    out["sivigila_dengue"].append(metrica("Actualidad", "year_", "periodo cubierto", None,
                                          f"anios {int(anos.min())} a {int(anos.max())}"))

    # ---------------- perfil epidemiologico ----------------
    crudo, df = cargar("perfil_epidemiologico_anual")
    n = len(df)
    edad = pd.to_numeric(df["EDAD"], errors="coerce")
    fuera = int(((edad < EDAD_MIN) | (edad > EDAD_MAX)).sum())
    res = []
    res.append(metrica("Unicidad", "fila completa", "(filas unicas / total) x 100",
                       pct(n - int(df.duplicated().sum()), n),
                       f"{int(df.duplicated().sum()):,} filas duplicadas ({pct(int(df.duplicated().sum()), n)}%)"))
    est = crudo.copy()
    for c in est.columns:
        est[c] = est[c].str.strip().str.upper()
    dup_est = int(est.duplicated().sum())
    res.append(metrica("Unicidad", "fila completa (tras estandarizar texto)", "(filas unicas despues de TRIM + UPPER / total) x 100",
                       pct(n - dup_est, n),
                       f"{dup_est:,} filas duplicadas ({pct(dup_est, n)}%): {dup_est - int(df.duplicated().sum()):,} adicionales estaban ocultas por diferencias de mayusculas/espacios"))
    for col in ["REGIMEN DE AFILIACION", "NACIONALIDAD"]:
        s = crudo[col]
        canon = s.str.strip().str.upper()
        res.append(metrica("Consistencia", col, "(filas ya escritas en forma canonica MAYUSCULA / total) x 100",
                           pct(int((s == canon).sum()), n),
                           f"{s.nunique()} variantes de escritura para {canon.nunique()} categorias reales; "
                           f"{int((s != canon).sum()):,} filas requieren estandarizacion"))
    res.append(metrica("Exactitud", "EDAD", f"(edades entre {EDAD_MIN} y {EDAD_MAX} / total) x 100",
                       pct(n - fuera, n), f"minimo {int(edad.min())}, maximo {int(edad.max())}, promedio {edad.mean():.2f}"))
    ciclo = crudo["CICLO DE VIDA"].str.upper()
    meses = {"ENERO","FEBRERO","MARZO","ABRIL","MAYO","JUNIO","JULIO","AGOSTO","SEPTIEMBRE","OCTUBRE","NOVIEMBRE","DICIEMBRE"}
    res.append(metrica("Validez", "CICLO DE VIDA", "(filas con un ciclo de vida real / total) x 100",
                       pct(int((~ciclo.isin(meses)).sum()), n),
                       f"{int(ciclo.isin(meses).sum()):,} filas contienen un nombre de mes (columnas CICLO DE VIDA y MES desalineadas)"))
    res.append(metrica("Validez", "SEXO", "(valores M o F / total) x 100", pct(int(df['SEXO'].isin(['M','F']).sum()), n), "dominio M/F"))
    res.append(metrica("Completitud", "CODIGO CIE10", "(valores no nulos / total) x 100",
                       pct(n - int(df['CODIGO CIE10'].isna().sum()), n), f"{int(df['CODIGO CIE10'].isna().sum())} nulo"))
    res.append(metrica("Actualidad", "MES / fecha", "existe variable temporal util", None,
                       "el archivo no trae fecha ni anio utilizable (la columna MES es constante); no es posible medir actualidad"))
    out["perfil_epidemiologico_anual"] = res

    # ---------------- SALUD Cundinamarca ----------------
    crudo, df = cargar("salud_cundinamarca")
    n = len(df)
    num = pd.to_numeric(df["DATO_NUMERICO"], errors="coerce")
    corrupto = int((num > 1e6).sum())
    anio = pd.to_numeric(df["YEAR"], errors="coerce")
    no_mun = int((~crudo["COD_MUN"].str.startswith("25")).sum() + (crudo["COD_DEP"] == "26").sum())
    tasa = num[crudo["INDICADOR"].str.contains("TASA DE INCIDENCIA DENGUE", na=False)]
    out["salud_cundinamarca"] = [
        metrica("Completitud", "toda la tabla", "(1 - celdas faltantes / celdas totales) x 100",
                pct(df.size - int(df.isna().sum().sum()), df.size),
                f"{int(df.isna().sum().sum()):,} celdas faltantes; CUALITATIVO {int(df['CUALITATIVO'].isna().sum()):,}, DATO_NUMERICO {int(df['DATO_NUMERICO'].isna().sum())}"),
        metrica("Exactitud", "DATO_NUMERICO", "(valores numericos plausibles <= 1.000.000 / valores numericos) x 100",
                pct(int(num.notna().sum()) - corrupto, int(num.notna().sum())),
                f"{corrupto} valores del indicador de mortalidad infantil con el decimal perdido (ej. 99009900990099008)"),
        metrica("Exactitud", "TASA DE INCIDENCIA DENGUE", "valores > 1.000 por 100.000 hab.",
                pct(len(tasa.dropna()) - int((tasa > 1000).sum()), len(tasa.dropna())),
                f"{int((tasa > 1000).sum())} valores sobre 1.000; maximo {tasa.max():,.2f}"),
        metrica("Validez", "YEAR", "(anios <= 2024, anio de la publicacion / total) x 100",
                pct(int((anio <= 2024).sum()), n),
                f"{int((anio > 2024).sum())} filas con anio posterior a 2024; {int((anio > 2026).sum())} con anio imposible (2027-2038)"),
        metrica("Consistencia", "COD_DEP / COD_MUN", "(filas de nivel municipal / total) x 100",
                pct(n - no_mun, n), f"{no_mun} filas son agregados no municipales (COLOMBIA, CUNDINAMARCA cod 26)"),
        metrica("Unicidad", "fila completa", "(filas unicas / total) x 100", pct(n - int(df.duplicated().sum()), n),
                f"{int(df.duplicated().sum())} duplicados exactos"),
        metrica("Actualidad", "YEAR", "periodo cubierto", None, f"{int(anio.min())} a 2024 (valores posteriores se consideran error)"),
    ]

    # ---------------- HDX ----------------
    crudo, df = cargar("disease_outbreaks_hdx")
    n = len(df)
    anio = pd.to_numeric(df["Year"], errors="coerce")
    out["disease_outbreaks_hdx"] = [
        metrica("Completitud", "toda la tabla", "(1 - celdas faltantes / celdas totales) x 100",
                pct(df.size - int(df.isna().sum().sum()), df.size),
                f"{int(df.isna().sum().sum())} celdas faltantes (who_region {int(df['who_region'].isna().sum())}, Definition {int(df['Definition'].isna().sum())}, unsd_region/subregion {int(df['unsd_region'].isna().sum())}, iso2 {int(df['iso2'].isna().sum())})"),
        metrica("Validez", "iso2", "(iso2 con 2 letras / total) x 100",
                pct(int(df['iso2'].astype(str).str.fullmatch(r'[A-Z]{2}').sum()), n),
                "los 6 nulos no cumplen el estandar ISO 3166"),
        metrica("Unicidad", "fila completa", "(filas unicas / total) x 100", pct(n - int(df.duplicated().sum()), n), "sin duplicados exactos"),
        metrica("Actualidad", "Year", "periodo cubierto", None, f"anios {int(anio.min())} a {int(anio.max())}"),
    ]

    # ---------------- Vigilancia Colombia ----------------
    crudo, df = cargar("vigilancia_colombia")
    n = len(df)
    sin_coma = crudo["ANO"].str.replace(",", "", regex=False)
    desc = int(df["Municipio_ocurrencia"].isna().sum())
    dep = crudo["Departamento_ocurrencia"].str.upper()
    no_geo = int(dep.str.contains("EXTERIOR|DESCONOCIDA", regex=True).sum())
    sem = pd.to_numeric(crudo["SEMANA"], errors="coerce")
    anio = pd.to_numeric(sin_coma, errors="coerce")
    out["vigilancia_colombia"] = [
        metrica("Validez", "ANO / COD_MUN_O", "(valores directamente numericos / total) x 100",
                pct(int(pd.to_numeric(crudo['ANO'], errors='coerce').notna().sum()), n),
                f"{int(crudo['ANO'].str.contains(',').sum()):,} filas con separador de miles ('2,012'); tras quitarlo {pct(int(anio.notna().sum()), n)}% es convertible"),
        metrica("Completitud", "Municipio_ocurrencia", "(municipios reales / total) x 100", pct(n - desc, n),
                f"{desc:,} filas con 'MUNICIPIO DESCONOCIDO'"),
        metrica("Validez", "Departamento_ocurrencia", "(departamentos geograficos / total) x 100", pct(n - no_geo, n),
                f"{no_geo:,} filas con categorias no geograficas (EXTERIOR, PROCEDENCIA DESCONOCIDA)"),
        metrica("Validez", "SEMANA", "(semanas entre 1 y 53 / total) x 100", pct(int(sem.between(1, 53).sum()), n), "rango epidemiologico"),
        metrica("Unicidad", "fila completa", "(filas unicas / total) x 100", pct(n - int(df.duplicated().sum()), n), "sin duplicados exactos"),
        metrica("Actualidad", "ANO", "periodo cubierto", None, f"anios {int(anio.min())} a {int(anio.max())}"),
    ]

    # ---------------- Ixodes ----------------
    crudo, df = cargar("ixodes_county_2023")
    n = len(df)
    out["ixodes_county_2023"] = [
        metrica("Completitud", "toda la tabla", "(1 - celdas faltantes / celdas totales) x 100",
                pct(df.size - int(df.isna().sum().sum()), df.size), "sin celdas vacias en las 7 hojas de datos"),
        metrica("Validez", "FIPSCode", "(codigos de 5 digitos / total) x 100",
                pct(int(df['FIPSCode'].str.fullmatch(r'\d{5}').sum()), n), "codigo FIPS como texto para conservar ceros iniciales"),
        metrica("Unicidad", "FIPSCode + anio_hoja", "(combinaciones unicas / total) x 100",
                pct(n - int(df.duplicated(['FIPSCode', 'anio_hoja']).sum()), n), "un registro por condado y por anio"),
        metrica("Actualidad", "hojas", "anios publicados", None, "2022, 2021, 2020, 2019, 2018, 2016 y 1996"),
    ]

    os.makedirs(p.OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(p.OUTPUT_DIR, "dimensiones_calidad.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    for ds, ms in out.items():
        print("==", ds)
        for m in ms:
            print(f"  {m['dimension']:<12} {m['variable']:<28} {m['resultado_pct']}  | {m['detalle'][:110]}")


if __name__ == "__main__":
    main()
