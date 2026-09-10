from flask import Flask, render_template, abort

app = Flask(__name__)


# ==========================================
# RUTAS DE LA ETAPA 1
# ==========================================

RUTAS_ETAPA1 = {
    'problema': '1_problema.html',
    'preguntas': '2_preguntas.html',
    'necesidades': '3_necesidades.html',
    'fuentes': '4_fuentes.html',
    'dataset': '5_dataset.html',
    'diccionario': '6_diccionario.html',
    'calidad': '7_calidad.html',
    'limitaciones': '8_limitaciones.html',
}


# ==========================================
# RUTAS DE LA ETAPA 2
# CALIDAD DE DATOS
# ==========================================

RUTAS_ETAPA2 = {
    'descripcion-datos': '1_descripcion_datos.html',
    'requisitos-calidad': '2_requisitos_calidad.html',
    'perfilamiento': '3_perfilamiento.html',
    'dimensiones': '4_dimensiones.html',
    'problemas': '5_problemas.html',
    'causas': '6_causas.html',
    'estrategias': '7_estrategias.html',
}


# ==========================================
# PÁGINA DE INICIO
# ==========================================

@app.route('/')
def inicio():
    return render_template(
        'etapa 1/inicio.html',
        slug_activo=None
    )


# ==========================================
# RUTAS DE LA ETAPA 1
# ==========================================

@app.route('/etapa1/<seccion>')
def etapa1_seccion(seccion):

    plantilla = RUTAS_ETAPA1.get(seccion)

    if not plantilla:
        abort(404)

    return render_template(
        f'etapa 1/{plantilla}',
        slug_activo=seccion
    )


# ==========================================
# RUTAS DE LA ETAPA 2
# ==========================================

@app.route('/etapa2/<seccion>')
def etapa2_seccion(seccion):

    plantilla = RUTAS_ETAPA2.get(seccion)

    if not plantilla:
        abort(404)

    return render_template(
        f'etapa 2/{plantilla}',
        slug_activo=seccion
    )


# ==========================================
# EJECUTAR LA APLICACIÓN
# ==========================================

if __name__ == '__main__':
    app.run(debug=True)