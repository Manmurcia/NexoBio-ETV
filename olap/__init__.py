"""Paquete del analisis multidimensional (Etapa 5) de NexoBio-ETV."""
import importlib.util
import os
import sqlite3

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
DB = os.path.join(AQUI, "nexobio_olap.db")


def asegurar_bd():
    """Construye la base si falta o si todavía usa el esquema OLAP anterior."""
    if os.path.exists(DB):
        con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        try:
            tablas = {r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
            requeridas = {"dim_tiempo", "dim_territorio", "dim_evento", "dim_fuente", "fact_notificacion"}
            if requeridas.issubset(tablas):
                columnas_tiempo = {r[1] for r in con.execute("PRAGMA table_info(dim_tiempo)")}
                columnas_evento = {r[1] for r in con.execute("PRAGMA table_info(dim_evento)")}
                fuentes = {r[0] for r in con.execute("SELECT fuente FROM dim_fuente")}
                if (
                    {"periodo_analisis", "tipo_anio_sivigila"}.issubset(columnas_tiempo)
                    and {"enfermedad", "anio_primer_registro"}.issubset(columnas_evento)
                    and {"SIVIGILA Colombia", "SIVIGILA Cundinamarca", "OMS/HDX"}.issubset(fuentes)
                ):
                    return
        finally:
            con.close()

    ruta = os.path.join(RAIZ, "scripts", "olap", "cargar_modelo.py")
    spec = importlib.util.spec_from_file_location("cargar_modelo", ruta)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"No se pudo cargar el ETL de OLAP: {ruta}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _resultados, fallos = mod.construir()
    if fallos:
        raise RuntimeError(f"La construccion del modelo OLAP fallo en {fallos} validaciones.")
