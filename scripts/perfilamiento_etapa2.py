"""
perfilamiento_etapa2.py

Script reproducible de perfilamiento y diagnostico de calidad para el proyecto NexoBio-ETV.

Resuelve el hallazgo del profesor: "SD", "SIN INFORMACION" y otros placeholders se
tratan como NULO real (no como una categoria de texto valida) antes de calcular
completitud, por lo que la completitud de sivigila_dengue deja de salir en 100%.

Genera, para cada dataset:
  - perfil_<dataset>.csv   -> perfilamiento por variable (tipo, unicos, nulos, min/max/media)
  - resumen_global.csv     -> una fila por dataset (filas, columnas, duplicados, completitud)
  - resumen_global.md      -> la misma tabla en Markdown, lista para pegar en el informe/web

Como el PDF y la web se llenan a mano hoy, los numeros no coinciden entre si. Ejecutando
este script una sola vez y copiando su salida a ambos lugares, PDF y web quedan consistentes
por construccion.

USO:
    1. Ajusta las rutas en CONFIG (abajo) a donde tengas los archivos originales.
    2. pip install pandas openpyxl
    3. python perfilamiento_etapa2.py
    4. Revisa la carpeta ./reporte_perfilamiento/
"""

import json
import os
from dataclasses import dataclass, field

import pandas as pd

# ---------------------------------------------------------------------------
# CONFIGURACION
# ---------------------------------------------------------------------------

OUTPUT_DIR = "reporte_perfilamiento"

# Tokens que deben tratarse como NULO real, sin importar mayusculas/espacios.
# Agrega aqui cualquier otro placeholder que encuentres en tus archivos.
NULL_TOKENS_GLOBAL = [
    "SD", "S.D", "S.D.", "SIN DATO", "SIN INFORMACION", "SIN INFORMACIÓN",
    "NO REPORTA", "NO REPORTADO", "N/A", "NA", "NULL", "",
]
# OJO: "SD" tambien es el codigo ISO2 de Sudan y "NA" el de Namibia. Por eso las columnas de
# codigos de pais se excluyen del reemplazo con `columnas_sin_tokens` en cada dataset.

# Rango biologico valido para variables de edad (ajusta si tu criterio es otro).
EDAD_MIN, EDAD_MAX = 0, 110


@dataclass
class DatasetConfig:
    nombre: str
    ruta: str
    tipo: str  # "csv" | "excel"
    sheet_name: object = 0          # solo para excel; usa el nombre o indice de hoja
    header_row: int = 0             # fila (0-indexed) donde esta el encabezado real
    encoding: str = "utf-8"         # codificacion del CSV (los archivos del proyecto son UTF-8)
    sep: str = ","
    header_busca: str = ""          # si se indica, el encabezado real es la fila cuya 1a celda == este texto
    hojas_prefijo: str = ""         # si se indica (excel), solo se leen hojas cuyo nombre empiece asi
    columnas_sin_tokens: list = field(default_factory=list)  # columnas donde NO se reemplazan tokens (p. ej. iso2)
    patrones_nulo: dict = field(default_factory=dict)        # {columna: regex} -> coincidencias se tratan como nulo
    descartar_hxl: bool = False     # descarta filas de etiquetas HXL (primera celda empieza con '#')
    columnas_edad: list = field(default_factory=list)       # columnas de edad a validar 0-110
    null_tokens_extra: list = field(default_factory=list)   # placeholders adicionales por archivo


# Ajusta estas rutas a donde tengas los 6 archivos originales de la Etapa 2.
CONFIG = [
    DatasetConfig(
        nombre="sivigila_dengue",
        ruta="data/sivigila_dengue.csv",
        tipo="csv",
        encoding="utf-8",  # el archivo es UTF-8; leerlo como latin1 genera mojibake (EspaÃ±ol)
        columnas_edad=["edad_"],
    ),
    DatasetConfig(
        nombre="perfil_epidemiologico_anual",
        ruta="data/PERFIL_EPIDEMIOLOGICO_ANUAL.csv",
        tipo="csv",
        encoding="utf-8",  # el archivo es UTF-8; leerlo como latin1 genera mojibake (EspaÃ±ol)
        columnas_edad=["EDAD"],
    ),
    DatasetConfig(
        nombre="salud_cundinamarca",
        ruta="data/SALUD.xlsx",
        tipo="excel",
        header_busca="COD_DEP",  # el encabezado real esta en la fila 12; se detecta solo
    ),
    DatasetConfig(
        nombre="disease_outbreaks_hdx",
        ruta="data/disease_outbreaks_HDX.xlsx",
        tipo="excel",
        columnas_sin_tokens=["iso2", "iso3"],  # "SD" = Sudan, no es un nulo
        descartar_hxl=True,  # la fila 2 son etiquetas HXL (#Year+iso3...), no es un registro
    ),
    DatasetConfig(
        nombre="vigilancia_colombia",
        ruta="data/Datos_de_Vigilancia_en_Salud_Publica_de_Colombia.csv",
        tipo="csv",
        patrones_nulo={"Municipio_ocurrencia": r"DESCONOCIDO"},
    ),
    DatasetConfig(
        nombre="ixodes_county_2023",
        ruta="data/Public_Use_Ixodes_County_Table_2023.xlsx",
        tipo="excel",
        sheet_name=None,  # None = lee varias hojas y las concatena
        columnas_sin_tokens=["State"],  # "SD" = South Dakota, no es un nulo
        hojas_prefijo="Ixodes records",  # las 7 hojas de datos (2022,2021,2020,2019,2018,2016,1996)
        header_busca="FIPSCode",
    ),
]


# ---------------------------------------------------------------------------
# CARGA
# ---------------------------------------------------------------------------

def _leer_hoja(ruta, hoja, cfg):
    """Lee una hoja de Excel. Si cfg.header_busca esta definido, localiza la fila de encabezado."""
    if cfg.header_busca:
        crudo = pd.read_excel(ruta, sheet_name=hoja, header=None, dtype=str, keep_default_na=False)
        primera = crudo.iloc[:, 0].astype(str).str.strip()
        idx = primera[primera == cfg.header_busca].index
        if len(idx) == 0:
            raise ValueError(f"No encontre el encabezado '{cfg.header_busca}' en la hoja '{hoja}'")
        h = int(idx[0])
        df = crudo.iloc[h + 1:].copy()
        df.columns = crudo.iloc[h].tolist()
        return df.reset_index(drop=True)
    return pd.read_excel(ruta, sheet_name=hoja, header=cfg.header_row, dtype=str, keep_default_na=False)


def cargar_dataset(cfg: DatasetConfig) -> pd.DataFrame:
    if not os.path.exists(cfg.ruta):
        raise FileNotFoundError(
            f"No encontre '{cfg.ruta}' para el dataset '{cfg.nombre}'. "
            f"Ajusta la ruta en CONFIG antes de ejecutar."
        )

    if cfg.tipo == "csv":
        df = pd.read_csv(cfg.ruta, encoding=cfg.encoding, sep=cfg.sep, dtype=str, keep_default_na=False)
    elif cfg.tipo == "excel":
        if cfg.sheet_name is None:
            # Varias hojas (p. ej. Ixodes: una por anio) -> concatenar con columna 'anio_hoja'
            nombres = pd.ExcelFile(cfg.ruta).sheet_names
            nombres = [n for n in nombres if n.startswith(cfg.hojas_prefijo)]
            partes = []
            for nombre_hoja in nombres:
                df_hoja = _leer_hoja(cfg.ruta, nombre_hoja, cfg).copy()
                df_hoja["anio_hoja"] = nombre_hoja
                partes.append(df_hoja)
            df = pd.concat(partes, ignore_index=True)
        else:
            df = _leer_hoja(cfg.ruta, cfg.sheet_name, cfg)
        if cfg.descartar_hxl:
            primera = df.iloc[:, 0].astype(str)
            df = df[~primera.str.startswith("#")].reset_index(drop=True)
    else:
        raise ValueError(f"Tipo de archivo no soportado: {cfg.tipo}")

    return df


def normalizar_nulos(df: pd.DataFrame, cfg: DatasetConfig) -> pd.DataFrame:
    """Reemplaza placeholders de nulo (SD, SIN INFORMACION, etc.) por NaN real.

    - Las columnas de `cfg.columnas_sin_tokens` se dejan intactas (codigos de pais como iso2).
    - `cfg.patrones_nulo` permite marcar como nulo valores que *contienen* un patron
      (ej. "* [DEPARTAMENTO]. MUNICIPIO DESCONOCIDO").
    """
    tokens = set(t.strip().upper() for t in NULL_TOKENS_GLOBAL + cfg.null_tokens_extra)
    df = df.copy()
    for col in df.columns:
        if col in cfg.columnas_sin_tokens:
            df[col] = df[col].replace(r"^\s*$", None, regex=True)  # solo vacios reales
            continue
        serie = df[col].astype("object")
        es_token = serie.map(lambda v: isinstance(v, str) and v.strip().upper() in tokens)
        if col in cfg.patrones_nulo:
            es_token = es_token | serie.astype(str).str.contains(cfg.patrones_nulo[col], case=False, regex=True, na=False)
        df[col] = serie.mask(es_token | serie.isna(), None)
    return df


# ---------------------------------------------------------------------------
# PERFILAMIENTO
# ---------------------------------------------------------------------------

def _es_codigo(nombre: str) -> bool:
    n = str(nombre).strip().lower()
    return n == "id" or n.startswith(("cod", "fips")) or n.endswith("_id")


def perfilar_columna(serie: pd.Series) -> dict:
    """Perfil de una variable: tipo inferido, valores unicos, nulos y estadisticas."""
    n = len(serie)
    no_nulos = serie.dropna()
    n_nulos = n - len(no_nulos)
    perfil = {
        "valores_unicos": int(no_nulos.nunique()),
        "nulos": int(n_nulos),
        "pct_nulos": round(100 * n_nulos / n, 2) if n else 0.0,
    }

    numerica = pd.to_numeric(no_nulos, errors="coerce")
    es_num = len(no_nulos) > 0 and numerica.notna().mean() > 0.95
    es_fecha = len(no_nulos) > 0 and no_nulos.astype(str).str.match(r"^\d{4}-\d{2}-\d{2}").mean() > 0.95

    if es_fecha:
        perfil["tipo_dato"] = "fecha"
    elif es_num and _es_codigo(serie.name):
        perfil["tipo_dato"] = "codigo numerico"
    elif es_num:
        perfil["tipo_dato"] = "entero" if (numerica.dropna() % 1 == 0).all() else "decimal"
        perfil["minimo"] = float(numerica.min())
        perfil["maximo"] = float(numerica.max())
        perfil["promedio"] = round(float(numerica.mean()), 2)
    else:
        perfil["tipo_dato"] = "texto"
    return perfil


def perfilar_dataset(df: pd.DataFrame, cfg: DatasetConfig) -> dict:
    n_filas, n_columnas = df.shape
    duplicados = int(df.duplicated().sum())
    total_celdas = n_filas * n_columnas
    total_nulos = int(df.isna().sum().sum())
    completitud = round(100 * (1 - total_nulos / total_celdas), 2) if total_celdas else 0.0
    if completitud == 100 and total_nulos > 0:   # nunca mostrar 100 % si queda algun faltante
        completitud = round(100 * (1 - total_nulos / total_celdas), 4)

    perfil_columnas = {col: perfilar_columna(df[col]) for col in df.columns}

    exactitud_edad = {}
    for col_edad in cfg.columnas_edad:
        if col_edad in df.columns:
            edad_num = pd.to_numeric(df[col_edad], errors="coerce")
            validas = edad_num.dropna()
            fuera_rango = ((validas < EDAD_MIN) | (validas > EDAD_MAX)).sum()
            exactitud_edad[col_edad] = {
                "registros_con_valor": int(validas.shape[0]),
                "fuera_de_rango_0_110": int(fuera_rango),
                "exactitud_pct": round(
                    100 * (1 - fuera_rango / max(validas.shape[0], 1)), 2
                ),
            }

    return {
        "dataset": cfg.nombre,
        "filas": n_filas,
        "columnas": n_columnas,
        "duplicados": duplicados,
        "total_nulos": total_nulos,
        "completitud_pct": completitud,
        "exactitud_edad": exactitud_edad,
        "perfil_columnas": perfil_columnas,
    }


# ---------------------------------------------------------------------------
# SALIDA
# ---------------------------------------------------------------------------

def guardar_reporte(resultados: list[dict]):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1) Perfil por variable -> un CSV por dataset
    for r in resultados:
        filas = []
        for col, perfil in r["perfil_columnas"].items():
            fila = {"variable": col, **perfil}
            filas.append(fila)
        pd.DataFrame(filas).to_csv(
            os.path.join(OUTPUT_DIR, f"perfil_{r['dataset']}.csv"), index=False
        )

    # 2) Resumen global -> un CSV con una fila por dataset
    resumen = pd.DataFrame(
        [
            {
                "dataset": r["dataset"],
                "filas": r["filas"],
                "columnas": r["columnas"],
                "duplicados": r["duplicados"],
                "total_nulos": r["total_nulos"],
                "completitud_pct": r["completitud_pct"],
            }
            for r in resultados
        ]
    )
    resumen.to_csv(os.path.join(OUTPUT_DIR, "resumen_global.csv"), index=False)

    # 3) Resumen global en Markdown, listo para pegar en el informe/web
    with open(os.path.join(OUTPUT_DIR, "resumen_global.md"), "w", encoding="utf-8") as f:
        f.write(resumen.to_markdown(index=False))

    # 4) JSON completo (incluye exactitud de edad), por si se necesita en la app Flask
    with open(os.path.join(OUTPUT_DIR, "reporte_completo.json"), "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)

    print(f"Reporte generado en ./{OUTPUT_DIR}/")
    print(resumen.to_string(index=False))


def main():
    resultados = []
    for cfg in CONFIG:
        print(f"Procesando {cfg.nombre} ...")
        df = cargar_dataset(cfg)
        df = normalizar_nulos(df, cfg)
        resultados.append(perfilar_dataset(df, cfg))
    guardar_reporte(resultados)


if __name__ == "__main__":
    main()
