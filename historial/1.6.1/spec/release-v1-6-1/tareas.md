# PASOS: trabajo verificable

- [ ] T01 (AC-01, AC-02): bump a `1.6.1` en `sdd.py`, `metrics.py` y
  `pyproject.toml`; redactar `## [1.6.1]` en `CHANGELOG.md`; commit
  `chore(release): bump fuentes a 1.6.1`.
- [ ] T02 (AC-01, AC-03): regenerar `uv.lock` con `uv lock` y
  actualizar pins en `test_model_profiles.py` y `test_sdd.py`; commit
  `chore(release): pins y uv.lock a 1.6.1`.
- [ ] T03 (AC-04): ejecutar `check release-v1-6-1 --run` y suite
  completa; registrar `review` y `approve close`; commit de sello.
- [ ] T04: limpiar arnés a `historial/1.6.1` y commitear; PR, merge a
  `main`, tag `v1.6.1`, push del tag y release en GitHub.
