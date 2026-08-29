from flask import Flask, render_template, abort

app = Flask(__name__)

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

@app.route('/')
def inicio():
    return render_template('etapa 1/inicio.html', slug_activo=None)

@app.route('/etapa1/<seccion>')
def etapa1_seccion(seccion):
    plantilla = RUTAS_ETAPA1.get(seccion)
    if not plantilla:
        abort(404)
    return render_template(f'etapa 1/{plantilla}', slug_activo=seccion)

if __name__ == '__main__':
    app.run(debug=True)