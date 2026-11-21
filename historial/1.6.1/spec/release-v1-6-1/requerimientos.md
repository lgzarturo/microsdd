# QUÉ: release 1.6.1

## Objetivo

Publicar MicroSDD 1.6.1 conforme a la orden explícita del programador
(nota: `release propose` sugiere `1.7.0` por los `feat:` de la skill
bajo demanda `/sdd-security`, pero el programador fija `1.6.1`). Bump
coherente de la fuente de versión, entrada `## [1.6.1]` en
`CHANGELOG.md` (R-04) con los cambios desde `v1.6.0` y regeneración
de `uv.lock`.

## Precondiciones

- Rama `chore/release-1-6-1` sobre `main` (`83587d2`, merge PR #22),
  árbol limpio, suite en verde (510 OK, 4 omitidas).
- Último tag `v1.6.0` (publicado, inmutable); el programador ordena
  publicar `1.6.1`, tag `v1.6.1`, notas y release.
- Sin tareas en `proceso`.

## Requisitos EARS

- REQ-01: WHEN se aplique el bump, THE `__version__` en
  `.microharness/sdd.py`, `HARNESS_VERSION` en
  `.microharness/metrics.py` y `version` en `pyproject.toml`
  SHALL ser `1.6.1`.
- REQ-02: WHEN se ejecute `sdd.py --version`, THE salida SHALL ser
  `MicroSDD 1.6.1`.
- REQ-03: WHEN se lea `CHANGELOG.md`, THE sección `[1.6.1]` SHALL
  listar los cambios desde `v1.6.0` agrupados según R-04 (`Añadido`,
  `Corregido`, `Otros`).
- REQ-04: WHEN se ejecute la suite, THE pins de versión SHALL
  exigir `1.6.1` y el test de coherencia SHALL seguir pasando.

## Criterios de aceptación

- AC-01: `sdd.py --version` imprime `MicroSDD 1.6.1`,
  `pyproject.toml` declara `version = "1.6.1"` y `metrics.py`
  declara `HARNESS_VERSION = '1.6.1'`.
- AC-02: `CHANGELOG.md` contiene `## [1.6.1]` con los cambios desde
  `v1.6.0` bajo `Añadido`, `Corregido` y `Otros`.
- AC-03: pins en `1.6.1`, `uv.lock` regenerado y tests enfocados y
  suite completa en verde.
- AC-04: `check release-v1-6-1 --run` pasa y la suite completa está
  en verde en el commit candidato.

## Fuera de alcance

- Mover o borrar tags publicados (prohibido).
- Cambios de API, instalador, agentes, bench o hook.
