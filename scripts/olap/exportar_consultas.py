"""
exportar_consultas.py - Genera docs/olap/consultas.sql con las consultas SQL que ejecuta la aplicacion
para las cinco operaciones, las cuatro vistas y las validaciones.   USO: python scripts/olap/exportar_consultas.py
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)
from olap import consultas as C  # noqa: E402

bloques = []


def add(titulo, df):
    bloques.append(f"-- {titulo}\n{df.attrs['sql']};\n")


bloques.append("-- Consultas del analisis multidimensional (generadas por olap/consultas.py).\n"
               "-- Los filtros de territorio excluyen 'Exterior' y 'Procedencia desconocida'.\n")
add("OPERACION DRILL-DOWN: casos por departamento dentro de la region Andina",
    C.consulta(["departamento"], "casos", {"region": ["Andina"]}))
add("OPERACION ROLL-UP: % de dengue grave por region (razon recalculada)", C.consulta(["region", "periodo"], "pct_grave"))
add("OPERACION SLICE: casos de chagas por region", C.consulta(["region"], "casos", {"evento": ["CHAGAS"]}))
add("OPERACION DICE: Caribe x 2017-2022 x dengue, por departamento",
    C.consulta(["departamento"], "casos", {"region": ["Caribe"], "periodo": ["2017-2022"], "evento": ["DENGUE"]}))
add("OPERACION PIVOT: region x evento (la matriz se transpone en la aplicacion)", C.consulta(["region", "evento"], "casos"))
add("VISTA 1: concentracion por municipio y evento", C.consulta(["municipio", "evento"], "casos"))
add("VISTA 2: casos por departamento y anio", C.consulta(["departamento", "anio"], "casos"))
add("VISTA 2: casos por region y tipo de anio", C.consulta(["region", "tipo_anio"], "casos"))
add("VISTA 3: casos por region, anio y trimestre (dengue, semanas 1-52); el indice se calcula normalizando cada anio",
    C.consulta(["region", "anio", "trimestre"], "casos", {"evento": ["DENGUE"]}, semana_max=52))
add("VISTA 4: % de dengue grave por departamento y periodo", C.consulta(["departamento", "periodo"], "pct_grave"))
add("VISTA 4: % de dengue grave por departamento y anio", C.consulta(["departamento", "anio"], "pct_grave"))
bloques.append("""-- VALIDACIONES (ver scripts/olap/cargar_modelo.py, funcion validar)
SELECT COUNT(*), COUNT(DISTINCT territorio_key) FROM dim_territorio;                 -- unicidad de claves
SELECT COUNT(*) FROM fact_notificacion f LEFT JOIN dim_evento d USING(evento_key)
 WHERE d.evento_key IS NULL;                                                          -- integridad referencial
SELECT COUNT(*) FROM (SELECT 1 FROM fact_notificacion
 GROUP BY evento_key, territorio_key, anio_key, semana_key HAVING COUNT(*)>1);         -- duplicados en el grano
SELECT SUM(casos), COUNT(*) FROM fact_notificacion;                                   -- coherencia con el CSV
""")
destino = os.path.join(RAIZ, "docs", "olap", "consultas.sql")
os.makedirs(os.path.dirname(destino), exist_ok=True)
open(destino, "w", encoding="utf-8").write("\n".join(bloques))
print("escrito", destino)
