# QUÉ: release 1.5.1 (fix HARNESS_VERSION)

## Objetivo

Publicar MicroSDD 1.5.1: corregir `HARNESS_VERSION` rezagado en
`1.4.0` en `.microharness/metrics.py`, bump coherente de la fuente de
versión a `1.5.1`, entrada `## [1.5.1]` en `CHANGELOG.md` (R-04) y
test de coherencia que impida la regresión.

## Precondiciones

- Rama `main`, HEAD `d90e7f5` (archival `historial/1.5.1`
  commiteado), árbol limpio.
- Último tag `v1.5.0`; `release propose` indica «sin incremento»
  (solo 2 `chore` desde el tag); el humano confirma PATCH `1.5.1`.
- Sin tareas en `proceso`.

## Requisitos EARS

- REQ-01: WHEN se lea `.microharness/metrics.py`, THE
  `HARNESS_VERSION` SHALL ser `1.5.1`, igual que `__version__` en
  `.microharness/sdd.py` y `version` en `pyproject.toml`.
- REQ-02: WHEN se ejecute `sdd.py --version`, THE salida SHALL ser
  `MicroSDD 1.5.1`.
- REQ-03: WHEN se lea `CHANGELOG.md`, THE sección `[1.5.1]` SHALL
  describir el fix bajo `Corregido`.
- REQ-04: WHEN se ejecute la suite, THE test de coherencia SHALL
  exigir `HARNESS_VERSION == __version__` y los pins de versión
  SHALL exigir `1.5.1`.

## Criterios de aceptación

- AC-01: `sdd.py --version` imprime `MicroSDD 1.5.1`,
  `pyproject.toml` declara `version = "1.5.1"` y `metrics.py`
  declara `HARNESS_VERSION = '1.5.1'`.
- AC-02: `CHANGELOG.md` contiene `## [1.5.1]` con 1 entrada en
  `Corregido` (HARNESS_VERSION rezagado en 1.4.0).
- AC-03: `tests/test_metrics.py` exige coherencia de versiones,
  los pins pasan a `1.5.1` y los tests enfocados pasan.
- AC-04: `check release-v1-5-1 --run` pasa y la suite completa está
  en verde en el commit candidato.

## Fuera de alcance

- Crear o publicar el tag `v1.5.1` (requiere aprobación de cierre).
- `git push` y release de GitHub (autorizaciones independientes).
- Cambios de API, instalador, agentes o bench.
