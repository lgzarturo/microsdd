# PASOS: trabajo verificable

Orden TDD: pruebas RED, sellado humano, implementación mínima, renombrado y migración por el líder, documentación y verificación. Detalle en `plan.md` (hoy `diseño.md`).

## Pruebas (RED) — `tests/test_sdd.py`, `tests/test_migrar_plan_md.py`, `tests/test_limpiar_arnes.py`
- [ ] T01 (AC-07): antes de tocar `sdd.py`, calcular con el `spec_fingerprint` actual (commit `61bd1ee`) la huella de un `spec.json` y tres documentos de contenido fijo con LF, guardando el de diseño como `diseño.md`; anotar el valor como constante de la prueba, con un comentario sobre su origen.
- [ ] T02 (AC-05, AC-12): adaptar a `plan.md` en `tests/test_sdd.py`: `setUp`, `test_diff_files_non_ascii_paths`, `test_scope_ignores_uncommitted_task_design`, `test_spec_approval_and_fingerprint`, `test_spec_fingerprint_ignores_crlf_conversion`, `test_diff_files_returns_literal_non_ascii_paths`, `test_reviewer_git_allowlist` y `test_allows_changes_in_spec_and_memory` (conservar `notas-año.md`).
- [ ] T03 (AC-01, AC-02, AC-03, AC-06): añadir en `tests/test_sdd.py` las pruebas del conjunto literal de `new`, `Falta spec/<slug>/plan.md`, marcadores en `plan.md`, `notas-año.md` rechazado y `notas.md` tolerado, y regex del autor (`plan.md` permitido, `diseño.md` denegado).
- [ ] T04 (AC-07, AC-08, AC-09): crear `tests/test_migrar_plan_md.py`: migración correcta con evento y campos intactos; abortos sin escribir (plan alterado, `diseño.md` restante, falta `plan.md`); segunda ejecución sin cambios.
- [ ] T05 (AC-12): en `tests/test_limpiar_arnes.py`, `task()` y la aserción de archivado usan `plan.md`.
- [ ] T06: ejecutar `python -m unittest discover -s tests` y confirmar que las pruebas nuevas y adaptadas fallan (RED).
- [ ] T07: el humano revisa las pruebas y el líder registra `sh .microharness/python.sh .microharness/sdd.py seal spec-plan-md --by <humano>` (resellado autorizado de `tests/test_sdd.py` y sellado de `tests/test_migrar_plan_md.py`).

## Implementación (implementador; PRE-02 para `.microharness/` y `.claude/`)
- [ ] T08 (AC-01, AC-02, AC-03, AC-04): en `.microharness/sdd.py`, `TASK_FILES`, `new`, `spec_fingerprint` y `validate` con `plan.md`, y el error `Nombre de archivo no ASCII en spec/<slug>/: <nombre>`.
- [ ] T09 (AC-06): en `.claude/hooks/pretool.py`, regex del autor con `plan\.md`.
- [ ] T10 (AC-07, AC-08, AC-09): crear `scripts/migrar_plan_md.py <raíz>` con fase de verificación sin escrituras y fase de escritura única (evento `migración_plan_md` con `old` y `new`).
- [ ] T11 (AC-01..AC-09, AC-12): suite en verde (GREEN).

## Migración del repositorio (líder, PRE-03) — `spec/*/`, `.microharness/memory.json`
- [ ] T12 (AC-10): tras T08, renombrar `spec/<slug>/diseño.md` a `spec/<slug>/plan.md` en las 15 tareas (`git mv` en las versionadas, `mv` en `spec-plan-md` si no lo está), sin modificar contenido.
- [ ] T13 (AC-10): ejecutar `sh .microharness/python.sh scripts/migrar_plan_md.py .` y conservar su salida como evidencia; si aborta, no forzar: escalar al humano.

## Documentación (implementador) — `.claude/agents/autor.md`, `README.md`, `assets/proceso-versionado.md`
- [ ] T14 (AC-11): `autor.md` punto 3 con `plan.md`; `README.md` líneas 126 y 217 con `plan.md`, regla «nombres de archivo solo ASCII» junto al árbol de `spec/<slug>/` y nota breve de migración para repositorios instalados; API-04 de `assets/proceso-versionado.md` con `plan.md`.

## Verificación
- [ ] T15 (AC-12): `python -m unittest discover -s tests` con código 0 y `sh .microharness/python.sh .microharness/sdd.py check spec-plan-md --run` OK.
- [ ] T16 (AC-04, AC-10): `git grep -n "diseño\.md" -- .microharness/sdd.py` vacío; `ls spec/*/diseño.md` sin resultados; `ls spec/*/plan.md` lista 15; `check <slug> --no-scope` OK en las 15 tareas; ningún nombre no ASCII en `git -c core.quotePath=false ls-files --cached --others --exclude-standard`; 15 eventos `migración_plan_md`; `git diff HEAD -- .microharness/memory.json | grep -E '^-.*"(review_fingerprint|by|evidence|at)"'` vacío.
- [ ] T17 (AC-11): `git grep -n "diseño\.md" -- . ':!spec/*' ':!.microharness/memory.json' ':!docs/*'` limitado a lo permitido por AC-11; `git status` solo muestra archivos de `scope.allowed_paths`, `spec/` y `.microharness/memory.json`.
