# PASOS: trabajo verificable

- [ ] T01 (AC-01, AC-03): bump `__version__` a `1.5.0` en
  `.microharness/sdd.py` y `version` en `pyproject.toml`;
  actualizar `test_version_is_1_4_0` → `test_version_is_1_5_0` y el
  pin `--version` en `tests/test_sdd.py` (ampliación aprobada).
- [ ] T02 (AC-02): redactar `## [1.5.0]` en `CHANGELOG.md`
  (4 Añadido + 9 Corregido desde asuntos, sin merges).
- [ ] T03 (AC-04): ejecutar `check release-v1-5-0 --run` y suite
  completa; registrar evidencia para revisión y cierre.
