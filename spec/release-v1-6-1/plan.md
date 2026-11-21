# CÓMO: bump a 1.6.1 (orden spec-bump-commit-limpiar)

## Situación comprobada

- `git log v1.6.0..HEAD` trae PR #21 (observación del release 1.6.0) y
  PR #22/#23 (skill bajo demanda `/sdd-security`, integración en
  `lider.md`/`revisor.md`, inclusión en `MANIFEST` y `pyproject.toml`,
  y documentación en `assets/`): `release propose` indica `1.7.0`,
  pero el programador ordena explícitamente `1.6.1`.
- El árbol está en `1.6.0` (`__version__`, `HARNESS_VERSION`,
  `pyproject.toml`, `uv.lock`, pins en `test_model_profiles.py` y
  `test_sdd.py`).
- `CHANGELOG.md` sigue R-04 (`assets/proceso-versionado.md`):
  entradas derivadas de los commits desde `v1.6.0`, sin merges.
- La compuerta `version_mix_errors` (AC-07) exige separar el cambio
  de `__version__` de `uv.lock` y `tests/` en dos commits.

## Decisión y justificación

Bump atómico mínimo KISS, sin tocar comportamiento:

1. `.microharness/sdd.py`: `__version__ = '1.6.1'`.
2. `.microharness/metrics.py`: `HARNESS_VERSION = '1.6.1'`.
3. `pyproject.toml`: `version = "1.6.1"`.
4. `CHANGELOG.md`: sección `## [1.6.1] - 2026-11-21` con
   `### Añadido`, `### Corregido` y `### Otros`.
5. Commit 1 `chore(release): bump fuentes a 1.6.1`.
6. Regenerar `uv.lock` con `uv lock` y actualizar pins a `1.6.1` en
   `tests/test_model_profiles.py` (+ docstring) y `tests/test_sdd.py`.
7. Commit 2 `chore(release): pins y uv.lock a 1.6.1`.
8. `check release-v1-6-1 --run`, `review`, `approve close`, commit 3
   `chore(release): sella tarea release-v1-6-1`.
9. `limpiar_arnes.py 1.6.1` + commit 4 `chore(release): archiva historial 1.6.1`;
   PR a `main` (protegida), merge, tag anotado `v1.6.1`, push tag,
   release en GitHub y registro de observación en `memory.json`.

## Invariantes y riesgos

- Invariante: `sdd.py`, `metrics.py`, `pyproject.toml`, `uv.lock`,
  pins y `CHANGELOG.md` dicen `1.6.1`; el tag `v1.6.1` apunta a un
  árbol con el bump.
- Riesgo: compuerta `version_mix_errors` si se mezclan `__version__` y
  `tests/`/`uv.lock` en el mismo commit. Mitigación: dividir en dos
  commits como en `1.6.0`.
- Estrategia `after`: implementación mínima y verificación
  (`check --run` + suite completa).
