"""
Consolidación de datos - Proyecto NexoBio (ETV: global, nacional, regional-Cundinamarca)
Materia: Minería de Datos - Etapa 1

Fuentes de entrada (carpeta data/ del repositorio):
  1. Datos_de_Vigilancia_en_Salud_Publica_de_Colombia.csv   -> nacional / regional (Cundinamarca)
  2. SALUD.xlsx                                             -> regional (indicadores oficiales Cundinamarca)
  3. disease_outbreaks_HDX.xlsx                              -> global (brotes OMS)
  4. Public_Use_Ixodes_County_Table_2023.xlsx                -> global (vigilancia de vector, EE.UU.)
  5. PERFIL_EPIDEMIOLOGICO_ANUAL.csv                          -> complementaria (perfil clínico nacional)

Salidas (en ./salida/):
  - nacional_colombia_etv.csv
  - regional_cundinamarca_etv.csv   <- dataset principal para el nivel regional
  - global_brotes_etv.csv
  - global_vector_ticks_us.csv
  - perfil_clinico_etv.csv
  - resumen_consolidacion.txt
"""

import pandas as pd
import os

CARPETA_BASE = os.path.dirname(os.path.abspath(__file__))
RAIZ_REPO = os.path.dirname(CARPETA_BASE)
CARPETA_ENTRADA = os.path.join(RAIZ_REPO, "data")      # archivos originales
CARPETA_SALIDA = os.path.join(RAIZ_REPO, "salida")     # resultados consolidados
os.makedirs(CARPETA_SALIDA, exist_ok=True)

# Lista de enfermedades transmitidas por vectores (para filtrar fuentes globales/complementarias)
PALABRAS_ETV = [
    "DENGUE", "MALARIA", "PALUDISMO", "CHIKUNGUNYA", "ZIKA",
    "LEISHMANIASIS", "CHAGAS", "YELLOW FEVER", "FIEBRE AMARILLA",
    "WEST NILE", "RIFT VALLEY", "MOSQUITO-BORNE", "VECTOR",
]

resumen = []


def log(mensaje):
    print(mensaje)
    resumen.append(mensaje)


# ---------------------------------------------------------------------------
# 1) NACIONAL + REGIONAL: Datos de Vigilancia en Salud Pública de Colombia
# ---------------------------------------------------------------------------
def procesar_nacional():
    ruta = os.path.join(CARPETA_ENTRADA, "Datos_de_Vigilancia_en_Salud_Publica_de_Colombia.csv")
    df = pd.read_csv(ruta)

    # ANO viene como texto con separador de miles ("2,007") -> convertir a entero
    df["ANO"] = df["ANO"].str.replace(",", "", regex=False).astype(int)

    # COD_MUN_O también trae separador de miles ("25,754") -> convertir a entero
    df["COD_MUN_O"] = df["COD_MUN_O"].str.replace(",", "", regex=False).astype(int)

    # Limpieza de texto: mayúsculas y espacios consistentes
    for col in ["Nombre_evento", "Departamento_ocurrencia", "Municipio_ocurrencia"]:
        df[col] = df[col].str.strip().str.upper()

    # Filtrar municipios "desconocidos" a una bandera aparte (no se descartan, se marcan)
    df["municipio_desconocido"] = df["Municipio_ocurrencia"].str.contains("DESCONOCIDO", na=False)

    df = df.rename(columns={
        "COD_EVE": "cod_evento",
        "Nombre_evento": "evento",
        "SEMANA": "semana",
        "ANO": "anio",
        "COD_DPTO_O": "cod_departamento",
        "COD_MUN_O": "cod_municipio",
        "Departamento_ocurrencia": "departamento",
        "Municipio_ocurrencia": "municipio",
    })

    ruta_nacional = os.path.join(CARPETA_SALIDA, "nacional_colombia_etv.csv")
    df.to_csv(ruta_nacional, index=False)
    log(f"[NACIONAL] {len(df):,} registros guardados en {ruta_nacional}")
    log(f"           Eventos: {sorted(df['evento'].unique())}")
    log(f"           Periodo: {df['anio'].min()}-{df['anio'].max()}")

    # Subconjunto Cundinamarca (cod_departamento == 25)
    cund = df[df["cod_departamento"] == 25].copy()
    log(f"[REGIONAL] Cundinamarca: {len(cund):,} registros (cod_departamento=25)")
    return df, cund


# ---------------------------------------------------------------------------
# 2) REGIONAL: SALUD 2024 - Gobernación de Cundinamarca (indicador ETV)
# ---------------------------------------------------------------------------
def procesar_salud_cundinamarca():
    ruta = os.path.join(CARPETA_ENTRADA, "SALUD.xlsx")
    df = pd.read_excel(ruta, header=11)  # el encabezado real está en la fila 12 del Excel

    etv = df[df["SUBCATEGORIA"] == "ENFERMEDADES TRANSMITIDAS POR VECTORES"].copy()
    etv = etv.rename(columns={
        "COD_DEP": "cod_departamento",
        "DEPARTAMENTO": "departamento",
        "COD_MUN": "cod_municipio",
        "MUNICIPIO": "municipio",
        "INDICADOR": "indicador",
        "DATO_NUMERICO": "valor",
        "YEAR": "anio",
        "FUENTE": "fuente_original",
        "UNIDAD_DE_MEDIDA": "unidad",
    })
    etv["municipio"] = etv["municipio"].str.strip().str.upper()

    ruta_salida = os.path.join(CARPETA_SALIDA, "regional_cundinamarca_indicadores.csv")
    etv.to_csv(ruta_salida, index=False)
    log(f"[REGIONAL] SALUD 2024 (indicadores ETV Cundinamarca): {len(etv):,} registros guardados en {ruta_salida}")
    log(f"           Indicadores: {sorted(etv['indicador'].unique())}")
    return etv


# ---------------------------------------------------------------------------
# 3) Cruce del nivel regional: conteo de casos + indicador oficial, por municipio/año
# ---------------------------------------------------------------------------
def combinar_regional(cund_conteo, cund_indicadores):
    # Agregamos el conteo de casos por municipio-año (todas las semanas)
    conteo_agg = (
        cund_conteo.groupby(["cod_municipio", "municipio", "anio", "evento"], as_index=False)["conteo"]
        .sum()
    )

    # Pivot del indicador oficial para tener una fila por municipio-año
    indicadores_pivot = cund_indicadores.pivot_table(
        index=["cod_municipio", "municipio", "anio"],
        columns="indicador",
        values="valor",
        aggfunc="first",
    ).reset_index()

    regional = conteo_agg.merge(
        indicadores_pivot,
        on=["cod_municipio", "municipio", "anio"],
        how="left",
    )

    ruta_salida = os.path.join(CARPETA_SALIDA, "regional_cundinamarca_etv.csv")
    regional.to_csv(ruta_salida, index=False)
    log(f"[REGIONAL] Dataset combinado (conteo + indicadores oficiales): {len(regional):,} filas -> {ruta_salida}")
    return regional


# ---------------------------------------------------------------------------
# 4) GLOBAL: WHO Disease Outbreak News (HDX)
# ---------------------------------------------------------------------------
def procesar_global_hdx():
    ruta = os.path.join(CARPETA_ENTRADA, "disease_outbreaks_HDX.xlsx")
    df = pd.read_excel(ruta)
    df = df[df["Year"] != "#date+year"]  # quitar la fila de metadatos HXL

    patron = "|".join(PALABRAS_ETV)
    etv = df[df["Disease"].str.contains(patron, case=False, na=False)].copy()

    ruta_salida = os.path.join(CARPETA_SALIDA, "global_brotes_etv.csv")
    etv.to_csv(ruta_salida, index=False)
    log(f"[GLOBAL] Brotes OMS relacionados a ETV: {len(etv):,} de {len(df):,} registros totales -> {ruta_salida}")
    log(f"         Enfermedades: {sorted(etv['Disease'].unique())}")
    return etv


# ---------------------------------------------------------------------------
# 5) GLOBAL (vector): CDC ArboNET - Ixodes tick surveillance (EE.UU.)
# ---------------------------------------------------------------------------
def procesar_global_ticks():
    ruta = os.path.join(CARPETA_ENTRADA, "Public_Use_Ixodes_County_Table_2023.xlsx")
    xl = pd.ExcelFile(ruta)
    hojas = [s for s in xl.sheet_names if s.startswith("Ixodes records")]

    todas = []
    for hoja in hojas:
        anio = hoja.replace("Ixodes records ", "").strip()
        # El encabezado real (FIPSCode) no esta siempre en la primera fila: hay un titulo
        # (y en 2016 y 1996 una linea extra de cita) antes de el. Se detecta por contenido.
        crudo = xl.parse(hoja, header=None, dtype=str)
        fila_enc = crudo.index[crudo[0].astype(str).str.strip() == "FIPSCode"][0]
        tmp = crudo.iloc[fila_enc + 1:].copy()
        tmp.columns = [str(c).strip() for c in crudo.iloc[fila_enc]]
        tmp = tmp.reset_index(drop=True)
        tmp["anio"] = anio
        todas.append(tmp)

    df = pd.concat(todas, ignore_index=True)
    ruta_salida = os.path.join(CARPETA_SALIDA, "global_vector_ticks_us.csv")
    df.to_csv(ruta_salida, index=False)
    log(f"[GLOBAL-VECTOR] CDC ArboNET (Ixodes, EE.UU.): {len(df):,} registros en {len(hojas)} años -> {ruta_salida}")
    return df


# ---------------------------------------------------------------------------
# 6) COMPLEMENTARIA: Perfil Epidemiológico Anual (corrige desalineamiento de columnas)
# ---------------------------------------------------------------------------
def procesar_perfil_epidemiologico():
    ruta = os.path.join(CARPETA_ENTRADA, "PERFIL_EPIDEMIOLOGICO_ANUAL.csv")
    df = pd.read_csv(ruta, low_memory=False)

    # Corrección del desalineamiento detectado en el diagnóstico de calidad:
    # "CICLO DE VIDA" trae en realidad el mes, y "MES" trae el subgrupo de causas.
    df = df.rename(columns={
        "CICLO DE VIDA": "mes_real",
        "MES": "subgrupo_causas_real",
    })

    for col in ["REGIMEN DE AFILIACION", "NACIONALIDAD", "mes_real"]:
        df[col] = df[col].str.strip().str.upper()

    patron = "|".join(PALABRAS_ETV)
    etv = df[df["NOMBRE CIE10"].str.contains(patron, case=False, na=False)].copy()

    ruta_salida = os.path.join(CARPETA_SALIDA, "perfil_clinico_etv.csv")
    etv.to_csv(ruta_salida, index=False)
    log(f"[COMPLEMENTARIA] Perfil epidemiológico ETV (columnas corregidas): {len(etv):,} de {len(df):,} registros -> {ruta_salida}")
    return etv


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    log("=== Consolidación de datos - Proyecto NexoBio ===\n")

    nacional, cund_conteo = procesar_nacional()
    cund_indicadores = procesar_salud_cundinamarca()
    regional = combinar_regional(cund_conteo, cund_indicadores)
    global_brotes = procesar_global_hdx()
    global_ticks = procesar_global_ticks()
    perfil = procesar_perfil_epidemiologico()

    log("\n=== Resumen final ===")
    log(f"Nacional (Colombia):        {len(nacional):,} registros")
    log(f"Regional (Cundinamarca):    {len(regional):,} registros combinados")
    log(f"Global (brotes OMS):        {len(global_brotes):,} registros")
    log(f"Global (vector, EE.UU.):    {len(global_ticks):,} registros")
    log(f"Complementaria (perfil):    {len(perfil):,} registros")
    log(f"\nTOTAL general (todas las tablas): {len(nacional) + len(regional) + len(global_brotes) + len(global_ticks) + len(perfil):,} registros")

    with open(os.path.join(CARPETA_SALIDA, "resumen_consolidacion.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(resumen))

    print(f"\nListo. Revisa la carpeta '{CARPETA_SALIDA}/' para los CSV consolidados.")
