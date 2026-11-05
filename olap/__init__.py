"""Paquete del analisis multidimensional (Etapa 5) de NexoBio-ETV."""
import importlib.util
import os

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
DB = os.path.join(AQUI, "nexobio_olap.db")


def asegurar_bd():
    """Si la base del modelo no existe (p. ej. en un despliegue nuevo) la construye con el mismo ETL
    que se ejecuta manualmente: scripts/olap/cargar_modelo.py"""
    if os.path.exists(DB):
        return
    ruta = os.path.join(RAIZ, "scripts", "olap", "cargar_modelo.py")
    spec = importlib.util.spec_from_file_location("cargar_modelo", ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.construir()
