# CÓMO: bump mínimo y changelog derivado

## Situación comprobada

- `git log v1.4.0..HEAD` contiene 4 `feat` (sdd, bench ×2, metrics),
  9 `fix`, 1 `docs`, 2 `chore` y 2 merges. Regla de incremento:
  mayor = MINOR → `1.5.0`. `release propose` lo confirma.
- Fuente de versión: `__version__ = '1.4.0'` en
  `.microharness/sdd.py:28` + `version = "1.4.0"` en `pyproject.toml`.
- `tests/test_model_profiles.py::VersionBumpTests::test_version_is_1_4_0`
  fija ambas; debe pasar a `1.5.0` o la suite falla.
- `CHANGELOG.md` sigue R-04 (`assets/proceso-versionado.md`):
  entradas derivadas de asuntos, sin merges.

## Decisión y justificación

Bump atómico mínimo KISS, sin tocar API ni comportamiento:

1. `.microharness/sdd.py`: `__version__ = '1.5.0'`.
2. `pyproject.toml`: `version = "1.5.0"`.
3. `tests/test_model_profiles.py`: renombrar el test a
   `test_version_is_1_5_0` y exigir `1.5.0` en ambos lugares.
4. `CHANGELOG.md`: nueva sección `## [1.5.0] - 2026-10-21` con
   `### Añadido` (4 feats) y `### Corregido` (9 fixes), redactados
   desde los asuntos de commit; sin merges ni chores.
5. Commit `chore(release): v1.5.0` (tras aprobación de cierre);
   tag anotado y push/release quedan fuera de esta spec.

## Invariantes y riesgos

- Invariante: `sdd.py`, `pyproject.toml`, test de versión y
  `CHANGELOG.md` dicen la misma versión.
- Riesgo: fechar mal la entrada. Mitigación: fecha UTC del día del
  commit (`2026-10-21`).
- Estrategia `after`: implementación mínima y luego verificación
  (`check --run` + suite completa); sin tests nuevos.
