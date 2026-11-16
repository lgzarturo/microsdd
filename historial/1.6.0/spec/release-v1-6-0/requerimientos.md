# QUÉ: release menor 1.6.0

## Objetivo

Publicar MicroSDD 1.6.0: `release propose` indica MINOR por los
`feat` desde `v1.5.3` (seal monotónico, puerta fitness, compuertas
de corrección y bench T-034) y el humano confirma `1.6.0`. Bump
coherente de la fuente de versión, entrada `## [1.6.0]` en
`CHANGELOG.md` (R-04) y regeneración de `uv.lock`. Orden del
programador: spec, bump, commit, limpiar arnés, commit, tag y
release.

## Precondiciones

- Rama `chore/release-1-6-0` sobre `main` (`47ccd59`, merge PR #19),
  árbol limpio, suite en verde.
- Último tag `v1.5.3` (publicado, inmutable); `release propose`
  indica MINOR; el humano confirma `1.6.0`.
- Sin tareas en `proceso`: `correccion-capa` cerrada
  administrativamente (código en `main` vía PR #19) y `symbol-map`
  pausada apartada a `spec-pausadas/`.

## Requisitos EARS

- REQ-01: WHEN se aplique el bump, THE `__version__` en
  `.microharness/sdd.py`, `HARNESS_VERSION` en
  `.microharness/metrics.py` y `version` en `pyproject.toml`
  SHALL ser `1.6.0`.
- REQ-02: WHEN se ejecute `sdd.py --version`, THE salida SHALL ser
  `MicroSDD 1.6.0`.
- REQ-03: WHEN se lea `CHANGELOG.md`, THE sección `[1.6.0]` SHALL
  listar los feats y fixes desde `v1.5.3` bajo `Añadido` y
  `Corregido`.
- REQ-04: WHEN se ejecute la suite, THE pins de versión SHALL
  exigir `1.6.0` y el test de coherencia SHALL seguir pasando.

## Criterios de aceptación

- AC-01: `sdd.py --version` imprime `MicroSDD 1.6.0`,
  `pyproject.toml` declara `version = "1.6.0"` y `metrics.py`
  declara `HARNESS_VERSION = '1.6.0'`.
- AC-02: `CHANGELOG.md` contiene `## [1.6.0]` con feats en
  `Añadido` y fixes en `Corregido`.
- AC-03: pins en `1.6.0`, `uv.lock` regenerado y tests enfocados
  en verde.
- AC-04: `check release-v1-6-0 --run` pasa y la suite completa está
  en verde en el commit candidato.

## Fuera de alcance

- Mover o borrar tags publicados (prohibido).
- Cambios de API, instalador, agentes, bench o hook.
- `git push` y release de GitHub (autorizaciones independientes,
  ya otorgadas por el programador en este flujo).
