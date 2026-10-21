# QUÉ: release 1.5.0

## Objetivo

Publicar MicroSDD 1.5.0: bump de la fuente de versión, entrada de
`CHANGELOG.md` derivada de los asuntos de commit desde `v1.4.0`
(R-04, sin merges) y actualización del test que fija la versión.

## Precondiciones

- Rama `main`, HEAD `a6f07d6` (archival `historial/1.5.0`
  commiteado), árbol limpio.
- Último tag `v1.4.0`; `release propose` propone `1.5.0`.
- Sin tareas en `proceso`.

## Requisitos EARS

- REQ-01: WHEN se ejecute `release propose` en `main`, THE salida
  SHALL indicar `Versión propuesta: 1.5.0` desde `v1.4.0`.
- REQ-02: WHEN se aplique el bump, THE `__version__` en
  `.microharness/sdd.py` y `version` en `pyproject.toml` SHALL ser
  `1.5.0`.
- REQ-03: WHEN se lea `CHANGELOG.md`, THE sección `[1.5.0]` SHALL
  listar los `feat` bajo `Añadido` y los `fix`/`perf` bajo
  `Corregido`, omitiendo merges, `docs`, `test`, `refactor` y `chore`.
- REQ-04: WHEN se ejecute la suite, THE test de versión SHALL exigir
  `1.5.0` en `sdd.py` y `pyproject.toml`.

## Criterios de aceptación

- AC-01: `sdd.py --version` imprime `MicroSDD 1.5.0` y `pyproject.toml`
  declara `version = "1.5.0"`.
- AC-02: `CHANGELOG.md` contiene `## [1.5.0]` con 4 entradas en
  `Añadido` (sdd loop autónomo, bench provider, bench m2, metrics
  telemetry) y 9 en `Corregido` (fixes de bench, hook y metrics).
- AC-03: `tests/test_model_profiles.py` fija `1.5.0` y
  `python -m unittest tests.test_model_profiles` pasa.
- AC-04: `check release-v1-5-0 --run` pasa y la suite completa está
  en verde en el commit candidato.

## Fuera de alcance

- Crear o publicar el tag `v1.5.0` (requiere aprobación de cierre).
- `git push` y release de GitHub (autorizaciones independientes).
- Cambios de API, instalador, agentes o bench.
