# PASOS: trabajo verificable

- [ ] T01 (AC-05): releer la evidencia de cada fila D-01 a D-14 de `diseño.md` en las rutas indicadas; descartar cualquier afirmación sin respaldo en el repositorio. Sin cambios de archivos.
- [ ] T02 (AC-01, AC-02): crear `assets/decisiones-diseno.md` con título, propósito (incluye que `assets/` no forma parte de la instalación), sección «Fuentes» con nombres y enlaces, y sección «Convención de etiquetas».
- [ ] T03 (AC-03, AC-04, AC-05): redactar en `assets/decisiones-diseno.md` las decisiones `### D-01` a `### D-14`, en el orden de `diseño.md`, cada una con `**Decisión:**`, `**Motivo:**`, `**Evidencia:**` y `**Fuente:**` etiquetada; separar con `[PROYECTO]` las adaptaciones de la guía (D-03, D-04, D-12).
- [ ] T04 (AC-06): repasar `assets/decisiones-diseno.md` contra ambas fuentes y reescribir con redacción propia cualquier pasaje copiado; eliminar rutas locales.
- [ ] T05 (AC-01, AC-02, AC-03, AC-04, AC-05, AC-06): ejecutar el comando `python -c` de `spec.json` y confirmar la salida `OK estructura` con código 0.
- [ ] T06 (AC-07): ejecutar `python -m unittest discover -s tests` (código 0) y `git status --porcelain`; confirmar que fuera de `spec/fundamentos-diseno/` y `.microharness/memory.json` solo aparece `assets/decisiones-diseno.md`.
