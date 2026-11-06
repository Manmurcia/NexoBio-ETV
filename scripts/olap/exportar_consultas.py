"""Exporta las consultas activas de vistas y operaciones al SQL de documentación."""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)
from olap import consultas as C  # noqa: E402

bloques = []


def add(titulo, df):
    bloques.append(f"-- {titulo}\n{df.attrs['sql']};\n")


bloques.append("-- Consultas del analisis multidimensional (generadas por olap/consultas.py).\n"
               "-- Los analisis de casos seleccionan una fuente SIVIGILA; los brotes OMS/HDX se consultan aparte.\n")
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
add("VISTA 4: Cundinamarca anual por departamento y periodo",
    C.consulta(["departamento", "periodo"], "casos", {"fuente": ["SIVIGILA Cundinamarca"]}))
bloques.append("""-- VISTA 5: brotes OMS/HDX por region OMS
SELECT t.region, SUM(f.brotes) AS brotes_reportados
FROM fact_notificacion f
JOIN dim_territorio t USING(territorio_key)
JOIN dim_fuente u USING(fuente_key)
WHERE u.fuente = 'OMS/HDX'
GROUP BY t.region
ORDER BY brotes_reportados DESC;

-- VALIDACIONES (scripts/olap/cargar_modelo.py, funcion validar)
SELECT COUNT(*), COUNT(DISTINCT tiempo_key) FROM dim_tiempo;
SELECT COUNT(*) FROM fact_notificacion f LEFT JOIN dim_tiempo d USING(tiempo_key) WHERE d.tiempo_key IS NULL;
SELECT COUNT(*) FROM fact_notificacion f LEFT JOIN dim_territorio d USING(territorio_key) WHERE d.territorio_key IS NULL;
SELECT COUNT(*) FROM fact_notificacion f LEFT JOIN dim_evento d USING(evento_key) WHERE d.evento_key IS NULL;
SELECT COUNT(*) FROM fact_notificacion f LEFT JOIN dim_fuente d USING(fuente_key) WHERE d.fuente_key IS NULL;
SELECT COUNT(*) FROM (
    SELECT 1 FROM fact_notificacion
    GROUP BY fuente_key, tiempo_key, territorio_key, evento_key, id_brote HAVING COUNT(*) > 1
);
SELECT u.fuente, COUNT(*) AS filas, SUM(f.casos) AS casos, SUM(f.brotes) AS brotes
FROM fact_notificacion f JOIN dim_fuente u USING(fuente_key)
GROUP BY u.fuente;
""")
destino = os.path.join(RAIZ, "docs", "olap", "consultas.sql")
os.makedirs(os.path.dirname(destino), exist_ok=True)
open(destino, "w", encoding="utf-8").write("\n".join(bloques))
print("escrito", destino)
