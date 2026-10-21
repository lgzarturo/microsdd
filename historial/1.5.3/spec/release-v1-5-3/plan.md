# CÓMO: bump de corrección a 1.5.3 (orden spec-bump-commit-limpiar)

## Situación comprobada

- `git log v1.5.2..HEAD` vacío: `release propose` responde «Commits
  sin incremento»; el humano confirma PATCH → `1.5.3` (R-03, tag
  publicado inmutable).
- El árbol está en `1.5.1` (`__version__`, `HARNESS_VERSION`,
  `pyproject.toml`, `uv.lock`, pins en `test_model_profiles.py` y
  `test_sdd.py`); el fix del hook Windows (commit `6564207`, CI en
  verde) aún no tiene release versionado.
- `CHANGELOG.md` sigue R-04 (`assets/proceso-versionado.md`).

## Decisión y justificación

Bump atómico mínimo KISS, sin tocar comportamiento, en el orden
dictado por el programador:

1. `.microharness/sdd.py`: `__version__ = '1.5.3'`.
2. `.microharness/metrics.py`: `HARNESS_VERSION = '1.5.3'`.
3. `pyproject.toml`: `version = "1.5.3"`.
4. `uv.lock`: regenerar con `uv lock`.
5. Pins a `1.5.3` en `test_model_profiles.py` (+ docstring) y
   `test_sdd.py` (pin `--version` + regex `__version__`).
6. `CHANGELOG.md`: sección `## [1.5.3] - 2026-10-21` con
   `### Corregido` (fix hook Windows) y nota del tag `v1.5.2`.
7. Commit `chore(release): v1.5.3` (tras aprobación de cierre).
8. `limpiar_arnes.py 1.5.3` + commit de archivado; tag anotado
   `v1.5.3` sobre el archivado (su árbol ya lleva el bump);
   push y release de GitHub (autorizados).

## Invariantes y riesgos

- Invariante: `sdd.py`, `metrics.py`, `pyproject.toml`, `uv.lock`,
  pins y `CHANGELOG.md` dicen `1.5.3`; el tag apunta a un árbol
  con el bump (a diferencia de `v1.5.2`).
- Riesgo: fechar mal la entrada. Mitigación: fecha UTC del día del
  commit (`2026-10-21`).
- Estrategia `after`: implementación mínima y luego verificación
  (`check --run` + suite completa); sin tests nuevos (el de
  coherencia es agnóstico a la versión).
