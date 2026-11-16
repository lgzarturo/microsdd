# PASOS: trabajo verificable

- [ ] T01 (AC-01, AC-03): bump a `1.6.0` en `sdd.py`, `metrics.py`
  y `pyproject.toml`; regenerar `uv.lock`; actualizar pins en
  `test_model_profiles.py` y `test_sdd.py`; tests enfocados.
- [ ] T02 (AC-02): redactar `## [1.6.0]` en `CHANGELOG.md`
  (Añadido + Corregido desde `v1.5.3`).
- [ ] T03 (AC-04): ejecutar `check release-v1-6-0 --run` y suite
  completa; registrar evidencia para revisión y cierre.
- [ ] T04: commit `chore(release): v1.6.0`; limpiar arnés a
  `historial/1.6.0` y commitear; PR, merge, tag, push y release.
