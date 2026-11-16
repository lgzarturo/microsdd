# PASOS: trabajo verificable

Editar con Edit (diff), sin reescribir archivos. Los comandos exactos están en `requerimientos.md`.

- [ ] T01 (AC-01): en `.github/workflows/tests.yml`, sustituir las líneas 5-7 (`push`, `branches`, `pull_request`) por `  workflow_dispatch:`. Ejecutar AC-01.
- [ ] T02 (AC-02): en `.github/workflows/bench-baseline.yml`, borrar las líneas 11-13 (`push`, `branches`, rama). Ejecutar AC-02.
- [ ] T03 (AC-05): en `.github/workflows/bench-baseline.yml:2`, dejar el comentario como `# Solo workflow_dispatch.`
- [ ] T04 (AC-05): en `assets/arnes-completo.md:7`, aplicar la sustitución indicada en `plan.md`, sin tocar el resto de la línea. Ejecutar AC-05.
- [ ] T05 (AC-03): ejecutar el grep de AC-03 y comprobar salida vacía y código 1.
- [ ] T06 (AC-04, AC-07): ejecutar los comandos `git diff` de AC-04 y `git status --short`; comprobar los recuentos y el alcance.
- [ ] T07 (AC-06): ejecutar `sdd.py check workflows-manuales --run` (suite completa) y comprobar que termina en verde.
