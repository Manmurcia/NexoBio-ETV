"""
tratamiento_etapa2.py

Aplica el plan de tratamiento de la Etapa 2 sobre los datasets y mide ANTES y DESPUES con las
mismas metricas de dimensiones_calidad.py. Guarda reporte_perfilamiento/antes_despues.json.

Decisiones (justificadas en la web, seccion 7):
  - Duplicados exactos: se eliminan (se conserva la primera fila).
  - Categorias: TRIM + UPPER y mapeo a categorias estandar.
  - "SD" / "SIN INFORMACION": se convierten a nulo real; NO se imputan.
  - Columnas con mas de 40 % de nulos: se excluyen del analisis (no se imputan).
  - Valores fuera de rango/plausibilidad (edad, DATO_NUMERICO, YEAR): NO se eliminan ni se imputan;
    se separan en una tabla de revision conservando el valor original.
  - Filas agregadas no municipales: se separan a otra tabla (no se borran).

USO:  python tratamiento_etapa2.py   (despues de perfilamiento_etapa2.py)
"""
import json, os
import pandas as pd
import perfilamiento_etapa2 as p

CFG = {c.nombre: c for c in p.CONFIG}
UMBRAL_NULOS = 0.40


def comp(df):
    v = round(100 * (1 - df.isna().sum().sum() / df.size), 2)
    if v == 100 and df.isna().sum().sum() > 0:   # nunca mostrar 100 % si queda algun faltante
        v = round(100 * (1 - df.isna().sum().sum() / df.size), 4)
    return v


def main():
    r = {}

    # --- sivigila_dengue
    cfg = CFG["sivigila_dengue"]
    df = p.normalizar_nulos(p.cargar_dataset(cfg), cfg)
    antes = comp(df)
    pct_nulos = df.isna().mean()
    excluir = pct_nulos[pct_nulos > UMBRAL_NULOS].index.tolist()
    df2 = df.drop(columns=excluir)
    edad = pd.to_numeric(df2["edad_"], errors="coerce")
    rev = (edad < p.EDAD_MIN) | (edad > p.EDAD_MAX)
    r["sivigila_dengue"] = {
        "completitud_antes_pct": antes, "completitud_despues_pct": comp(df2),
        "columnas_excluidas": excluir, "n_columnas_excluidas": len(excluir),
        "edades_a_revision": int(rev.sum()), "valores_edad_a_revision": sorted(edad[rev].astype(int).tolist()),
        "exactitud_edad_antes_pct": round(100 * (1 - rev.sum() / edad.notna().sum()), 4),
        "exactitud_edad_despues_pct": 100.0, "filas_tabla_final": int((~rev).sum()),
    }

    # --- perfil epidemiologico
    cfg = CFG["perfil_epidemiologico_anual"]
    crudo = p.cargar_dataset(cfg)
    n0 = len(crudo)
    # ORDEN IMPORTANTE: primero estandarizar texto y despues eliminar duplicados; si se deduplica antes,
    # filas que solo difieren en mayusculas/espacios quedan como "unicas" y reaparecen como duplicadas.
    est = crudo.copy()
    for c in est.columns:
        est[c] = est[c].str.strip().str.upper()
    dup_exactos = int(crudo.duplicated().sum())
    dup_tras_estandarizar = int(est.duplicated().sum())
    df = est.drop_duplicates()
    df = df.rename(columns={"CICLO DE VIDA": "mes_real"}).drop(columns=["MES", "SUBGRUPO CAUSAS DE MORBILIDAD", "GRAN CAUSA DE MORBILIDAD"])
    r["perfil_epidemiologico_anual"] = {
        "filas_antes": n0, "filas_despues": len(df), "duplicados_eliminados": n0 - len(df),
        "duplicados_exactos_sin_estandarizar": dup_exactos, "duplicados_tras_estandarizar": dup_tras_estandarizar,
        "unicidad_antes_pct": round(100 * (n0 - crudo.duplicated().sum()) / n0, 2),
        "unicidad_despues_pct": round(100 * (len(df) - df.duplicated().sum()) / len(df), 2),
        "unicidad_antes_estandarizar_pct": round(100 * (n0 - dup_tras_estandarizar) / n0, 2),
        "regimen_variantes_antes": int(crudo["REGIMEN DE AFILIACION"].nunique()),
        "regimen_categorias_despues": int(df["REGIMEN DE AFILIACION"].nunique()),
        "regimen_categorias": sorted(df["REGIMEN DE AFILIACION"].unique().tolist()),
        "nacionalidad_variantes_antes": int(crudo["NACIONALIDAD"].nunique()),
        "nacionalidad_categorias_despues": int(df["NACIONALIDAD"].nunique()),
        "meses_en_mes_real": int(df["mes_real"].nunique()),
        "columnas_constantes_eliminadas": 3,
    }
    canon = lambda s: (s == s.str.strip().str.upper()).mean() * 100
    r["perfil_epidemiologico_anual"]["consistencia_regimen_antes_pct"] = round(canon(crudo["REGIMEN DE AFILIACION"]), 2)
    r["perfil_epidemiologico_anual"]["consistencia_regimen_despues_pct"] = round(canon(df["REGIMEN DE AFILIACION"]), 2)

    # --- SALUD
    cfg = CFG["salud_cundinamarca"]
    crudo = p.cargar_dataset(cfg)
    df = p.normalizar_nulos(crudo, cfg)
    num = pd.to_numeric(df["DATO_NUMERICO"], errors="coerce")
    anio = pd.to_numeric(df["YEAR"], errors="coerce")
    no_mun = (~crudo["COD_MUN"].str.startswith("25")) | (crudo["COD_DEP"] == "26")
    revision = (num > 1e6) | (anio > 2024)
    final = df[~no_mun & ~revision].drop(columns=["CUALITATIVO"])
    r["salud_cundinamarca"] = {
        "filas_antes": len(df), "filas_no_municipales_separadas": int(no_mun.sum()),
        "filas_a_revision": int((revision & ~no_mun).sum()), "filas_tabla_final": len(final),
        "completitud_antes_pct": comp(df), "completitud_despues_pct": comp(final),
        "columna_excluida": "CUALITATIVO (48,43 % nulos)",
    }

    # --- vigilancia
    cfg = CFG["vigilancia_colombia"]
    crudo = p.cargar_dataset(cfg)
    df = p.normalizar_nulos(crudo, cfg)
    for c in ["ANO", "COD_MUN_O"]:
        df[c] = pd.to_numeric(crudo[c].str.replace(",", "", regex=False), errors="coerce")
    r["vigilancia_colombia"] = {
        "ano_convertible_pct": round(100 * df["ANO"].notna().mean(), 2),
        "cod_mun_convertible_pct": round(100 * df["COD_MUN_O"].notna().mean(), 2),
        "municipios_desconocidos_marcados": int(df["Municipio_ocurrencia"].isna().sum()),
    }

    os.makedirs(p.OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(p.OUTPUT_DIR, "antes_despues.json"), "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False, indent=2)
    print(json.dumps(r, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
