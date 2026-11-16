# CÓMO: bump menor a 1.6.0 (orden spec-bump-commit-limpiar)

## Situación comprobada

- `git log v1.5.3..HEAD` trae `feat` (seal, fitness, sdd, bench
  T-034 y bench previos): `release propose` responde MINOR →
  `1.6.0`, confirmado por el humano (el pedido inicial `1.5.4`
  se corrigió a `1.6.0` por las reglas de incremento).
- El árbol está en `1.5.3` (`__version__`, `HARNESS_VERSION`,
  `pyproject.toml`, `uv.lock`, pins en `test_model_profiles.py` y
  `test_sdd.py`).
- `CHANGELOG.md` sigue R-04 (`assets/proceso-versionado.md`):
  entradas derivadas de los asuntos de commit, sin merges.

## Decisión y justificación

Bump atómico mínimo KISS, sin tocar comportamiento, en el orden
dictado por el programador:

1. `.microharness/sdd.py`: `__version__ = '1.6.0'`.
2. `.microharness/metrics.py`: `HARNESS_VERSION = '1.6.0'`.
3. `pyproject.toml`: `version = "1.6.0"`.
4. `uv.lock`: regenerar con `uv lock`.
5. Pins a `1.6.0` en `test_model_profiles.py` (+ docstring) y
   `test_sdd.py` (pin `--version` + regex `__version__`);
   `test_correccion_capa.py` usa `1.5.3`/`1.5.4` solo como datos
   de fixtures y no se toca.
6. `CHANGELOG.md`: sección `## [1.6.0] - 2026-11-16` con
   `### Añadido` (feats) y `### Corregido` (fixes).
7. Commit `chore(release): v1.6.0` (tras aprobación de cierre).
8. `limpiar_arnes.py 1.6.0` + commit de archivado; tag anotado
   `v1.6.0` sobre el archivado (su árbol ya lleva el bump);
   PR, merge, push y release de GitHub (autorizados).

## Invariantes y riesgos

- Invariante: `sdd.py`, `metrics.py`, `pyproject.toml`, `uv.lock`,
  pins y `CHANGELOG.md` dicen `1.6.0`; el tag apunta a un árbol
  con el bump.
- Riesgo: fechar mal la entrada. Mitigación: fecha UTC del día del
  commit (`2026-11-16`).
- Estrategia `after`: implementación mínima y luego verificación
  (`check --run` + suite completa); sin tests nuevos (el de
  coherencia es agnóstico a la versión).
