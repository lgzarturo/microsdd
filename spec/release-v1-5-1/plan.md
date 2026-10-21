# CÓMO: fix de versión + test de coherencia (TDD)

## Situación comprobada

- `git log v1.5.0..HEAD` contiene 2 `chore` (nota de publicación
  1.5.0, archivado `historial/1.5.1`). `release propose` responde
  «Commits sin incremento»; el humano confirma PATCH → `1.5.1` (R-03).
- Bug: `HARNESS_VERSION = '1.4.0'` en `.microharness/metrics.py:17`
  mientras `__version__ = '1.5.0'` en `.microharness/sdd.py:28` y
  `version = "1.5.0"` en `pyproject.toml`. Ningún test lo cubre.
- Pins a actualizar: `test_version_is_1_5_0` en
  `tests/test_model_profiles.py` (+ docstring) y pin `--version` +
  regex `__version__` en `tests/test_sdd.py`.
- `CHANGELOG.md` sigue R-04 (`assets/proceso-versionado.md`).

## Decisión y justificación

TDD mínimo KISS, sin tocar API ni comportamiento:

1. `tests/test_metrics.py`: test de coherencia
   `HARNESS_VERSION == sdd.__version__` (rojo: 1.4.0 vs 1.5.0).
2. `.microharness/metrics.py`: `HARNESS_VERSION = '1.5.1'`.
3. `.microharness/sdd.py`: `__version__ = '1.5.1'`.
4. `pyproject.toml`: `version = "1.5.1"`.
5. Pins a `1.5.1` en `test_model_profiles.py` y `test_sdd.py`.
6. `CHANGELOG.md`: sección `## [1.5.1] - 2026-10-21` con
   `### Corregido` (1 entrada).
7. Commit `chore(release): v1.5.1` (tras aprobación de cierre);
   tag anotado y push/release quedan fuera de esta spec.

## Invariantes y riesgos

- Invariante: `metrics.py`, `sdd.py`, `pyproject.toml`, pins y
  `CHANGELOG.md` dicen la misma versión.
- Riesgo: fechar mal la entrada. Mitigación: fecha UTC del día del
  commit (`2026-10-21`).
- Estrategia `tdd`: test de coherencia en rojo antes del bump;
  luego verificación (`check --run` + suite completa).
