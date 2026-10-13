# PASOS: trabajo verificable

Orden: T00 (líder) → T01-T10 (implementador) → T11 (líder, antes de la revisión) → T12.

- [ ] T00 (AC-10, líder): `git mv docs/convensiones.md docs/convenciones.md` y `git mv docs/specificaciones.md docs/especificaciones.md`; comprobar con `git status` que figuran como renombrados. Ejecutar la suite y confirmar que sigue en verde (no depende de `docs/` reales).
- [ ] T01 (AC-01, AC-02, AC-03, AC-04): en `tests/test_sdd.py`, pruebas rojas de `ensure_init()` en repositorio temporal: directorio vacío crea los cuatro nombres nuevos; con antiguos preexistentes no crea los nuevos, conserva bytes y emite las líneas `AVISO:` con los `git mv`; con antiguo y nuevo no cambia nada y avisa nombrando ambos; segunda ejecución idempotente; `main(['init'])` devuelve 0.
- [ ] T02 (AC-01..AC-04): en `.microharness/sdd.py` (por Bash), `DOCS` con nombres nuevos, `LEGACY_DOCS` y las tres ramas de `ensure_init()`; T01 en verde.
- [ ] T03 (AC-05): en `tests/test_limpiar_arnes.py`, `DOCS` con nombres nuevos y prueba nueva que archiva un repositorio con `docs/` en nombres antiguos y termina con los cuatro nombres nuevos iguales a `sdd.py init`; la prueba `test_unknown_doc_aborts` queda intacta. Rojo.
- [ ] T04 (AC-05): en `scripts/limpiar_arnes.py`, `DOCS` nuevos, `LEGACY_DOCS` aceptados en `validate()`; `archive()` compara con `DOCS`. T03 en verde.
- [ ] T05 (AC-06, AC-07, AC-08): en `tests/test_installer.py`, actualizar la aserción de AC-01 a los nombres nuevos y comprobar `docs/convenciones.md docs/especificaciones.md` en el `git add`; prueba nueva con `docs/convensiones.md` preexistente en el destino: no se crea el nuevo, el antiguo se conserva, la salida contiene `AVISO:` y el código es 0. Rojo.
- [ ] T06 (AC-06, AC-07, AC-08): en `src/microsdd/installer.py`, `INIT_FILES` con nombres nuevos y reenvío de las líneas `AVISO:` de la salida de `init`; sin tocar `MANIFEST` ni `pyproject.toml`. T05 y AC-10 del instalador en verde.
- [ ] T07 (AC-09): `.claude/agents/lider.md` línea 9 y `CLAUDE.md` línea 7 (por Bash): nombres nuevos más la alternativa a los antiguos si los nuevos no existen.
- [ ] T08 (AC-09): `README.md`: `git add` de ejemplo y árbol con nombres nuevos; nota «Migración de nombres de `docs/`» con los dos `git mv` junto a la nota de `plan.md`.
- [ ] T09 (AC-10): `assets/decisiones-diseno.md`: las cinco rutas de evidencia a `docs/convenciones.md` / `docs/especificaciones.md`.
- [ ] T10 (AC-10, AC-11): ejecutar `git grep -nw -e convensiones -e specificaciones -- ':!spec' ':!.microharness/memory.json'` y confirmar que solo quedan las excepciones de REQ-09; ejecutar `python -m unittest discover -s tests -v` completo en verde.
- [ ] T11 (AC-10, líder): añadir la fila de `renombrar-docs` al índice de `docs/especificaciones.md` (y, si procede, una línea de compatibilidad en `docs/arquitectura.md`) antes de solicitar la revisión.
- [ ] T12 (AC-01..AC-11): `sh .microharness/python.sh .microharness/sdd.py check renombrar-docs --run` y revisión independiente; ninguna edición posterior de `docs/` sin nueva revisión.
