# Semana 9 — Presentación 1: informe técnico y diapositivas

Cumple la Tabla 1 y el Anexo A1 del reglamento del curso (P1: 10 min de exposición y 5 de preguntas; máximo
25 diapositivas).

## Archivos

| Archivo | Qué es |
|---|---|
| `docs/informe/informe_p1.tex` y `informe_p1.pdf` | Informe técnico en LaTeX (24 páginas), con las secciones I a XIII del Anexo A1.1 |
| `docs/informe/figuras/*.tex` y `.pdf` | Diagramas en TikZ: pictórico, metodología (normal y resaltada) y cronograma con colores |
| `docs/informe/img/` | Logo UNI, escenas del simulador y gráficos de resultados |
| `docs/presentacion/p1/img/` | Las imágenes que usa la presentación (diagramas, ecuaciones, gráficos) |
| `tools/render_escenas.py` | Regenera las cinco escenas del simulador de `docs/informe/img/` |

La presentación de 24 diapositivas está en Claude Design (artefacto privado). Se exporta a PPT o PDF desde su
menú Compartir › Exportar, y de ahí se entrega el PPT en la carpeta del Classroom.

## Compilar el informe

```bash
cd docs/informe
latexmk -pdf informe_p1.tex
```

Los diagramas se compilan por separado (`cd figuras && latexmk -pdf pictorico.tex`) y el informe incluye los PDF.
Las versiones `_resaltada` y `pictorico_resaltado` salen de la misma plantilla con `\resaltartrue`.

## Estructura de las diapositivas y tiempo (9:25 + 35 s de margen)

| # | Diapositiva | Tiempo |
|---|---|---|
| 1 | Carátula | 0:20 |
| 2 | Temas | 0:10 |
| 3-4 | Situación problemática; problema general e ingenieril | 1:05 |
| 5-6 | Estado del arte: productos y publicaciones | 1:10 |
| 7 | Justificación | 0:35 |
| 8-9 | Objetivo general; objetivos específicos con indicador | 0:50 |
| 10-12 | Diagrama pictórico, componentes y metodología | 1:35 |
| 13-15 | Marco teórico: MDP, SAC y planificación y métricas | 1:20 |
| 16 | Aplicaciones y usuarios | 0:15 |
| 17-18 | Viabilidad | 0:45 |
| 19-20 | Cronograma y presupuesto | 0:35 |
| 21-22 | Producto final: diagramas resaltados | 0:20 |
| 23 | Conclusiones | 0:25 |
| 24 | Referencias (respaldo) | 0:00 |

## Qué falta completar o confirmar

- **Código de Leonardo**, marcado en rojo en la carátula del informe. La carátula de las diapositivas no lleva códigos.
- **Profesor:** se supuso el Ing. José Oliden Martínez (el que firma el reglamento). Confirmarlo.
- **Impresión S/ 20:** es una estimación sin cotización; el resto del presupuesto es S/ 0 porque todo es prestado.
- **Semana de la P1:** el reglamento fija la P1 en las semanas 6-7 y el cronograma la pone en la semana 9, que es
  la actual. Confirmar con el profesor la fecha de entrega.
- Si el profesor exige el informe en Word, convertirlo desde el `.tex` (las ecuaciones y las figuras piden retoques).

## Origen de las cifras y reservas

| Cifra | Fuente | Reserva |
|---|---|---|
| 542 000 robots instalados y parque de 4 664 000 en 2024 | IFR, World Robotics 2025 (nota de prensa) | Ninguna |
| 74 000 empresas, 350 000 empleos, más del 9 % del PBI manufacturero | PRODUCE (OGEIEE), Estudio del sector metalmecánico 2024, citado por ProActivo el 16-jul-2025 | Se cita la nota de prensa, no el estudio |
| 48 robots en el Perú a fines de 2017 | IFR, citado por Aduana News | Fuente secundaria y antigua; no se halló cifra reciente |
| Integración que triplica el costo del robot | The Fabricator | Estimación de integradores, no estudio independiente |
| E6 a unos USD 6 995 | RobotLAB, consultada en octubre de 2026 | Precio de un vendedor; puede variar |
| RoboDK educativa USD 145/año | `docs/contexto-proyecto-rl-manipulador-6gdl.md` (sep. 2026) | Sin reverificar |
| Resultados de SAC y de la línea base | `results/*.csv` (ver `docs/presentacion/guion.md`) | Ninguna |

## Cómo se hizo

- Las escenas son renders de PyBullet con la cámara de `tools/video_semillas.py`, vista desde delante de la mesa.
- Las ecuaciones de las diapositivas son imágenes de matplotlib; las del informe son LaTeX.
- El informe no incluye código, solo diagramas y ecuaciones, como pide el Anexo A.
