# Guía de commits y pull request — Etapa 5

Rama: `feature/etapa-5`, integrada a `main` mediante pull request (como en las etapas anteriores).
Requisito: cada integrante realiza **al menos tres commits** relacionados con la actividad. Cada commit debe corresponder a trabajo que esa persona haya
revisado y pueda explicar (cada integrante debe ejecutar la carga y las verificaciones en su equipo antes de hacer push).

```bash
git checkout main && git pull
git checkout -b feature/etapa-5
```

## Reparto sugerido (9 commits)

| Integrante | Commit | Archivos | Mensaje sugerido |
|---|---|---|---|
| **Manuel Felipe Murcia Suárez** | 1 | `scripts/olap/crear_modelo.sql`, `docs/olap/modelo_estrella.md`, `static/img/olap_estrella.svg` | `Etapa 5: diseño del modelo estrella, diccionario y diagrama` |
| | 2 | `scripts/olap/cargar_modelo.py`, `.gitignore` | `Etapa 5: ETL del modelo estrella y 29 validaciones` |
| | 3 | `scripts/olap/verificar_conocimientos.py`, `scripts/olap/exportar_consultas.py`, `docs/olap/consultas.sql` | `Etapa 5: verificación de cifras y consultas exportadas` |
| **Carlos Julio Pérez Rodríguez** | 4 | `olap/__init__.py`, `olap/consultas.py` | `Etapa 5: motor de consultas multidimensionales (drill, roll, slice, dice, pivot)` |
| | 5 | `olap/vistas.py`, `olap/rutas.py`, `app.py` | `Etapa 5: vistas interactivas y blueprint en Flask` |
| | 6 | `templates/layout.html` | `Etapa 5: menú Análisis multidimensional y corrección del id del menú de la Etapa 4` |
| **José Daniel Gómez Rodríguez** | 7 | `olap/conocimientos.py` | `Etapa 5: ocho conocimientos multidimensionales` |
| | 8 | `templates/etapa 5/` | `Etapa 5: plantillas de las vistas y secciones` |
| | 9 | `README.md`, `docs/olap/GUIA_COMMITS_ETAPA5.md` | `Etapa 5: documentación, instrucciones de carga y ejecución` |

```bash
git add <archivos del commit> && git commit -m "<mensaje>"
git push -u origin feature/etapa-5
```

Luego: pull request `feature/etapa-5 → main` en GitHub, revisión por otro integrante y *merge*. Después de integrar, publicar de nuevo en Render y comprobar
que el menú **Análisis multidimensional** abre las seis páginas.

## Lista de verificación antes del pull request

- [ ] `python scripts/olap/cargar_modelo.py` termina con 29/29 comprobaciones correctas
- [ ] `python scripts/olap/verificar_conocimientos.py` imprime «TODAS LAS CIFRAS COINCIDEN»
- [ ] La aplicación arranca y las cuatro vistas responden con y sin filtros
- [ ] Capturas de pantalla de la versión final para el informe PDF
