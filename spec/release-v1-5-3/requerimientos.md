# QUÉ: release de corrección 1.5.3

## Objetivo

Publicar MicroSDD 1.5.3: el tag `v1.5.2` se publicó sobre el commit
de archivado sin bump (código en `1.5.1`) y, como un tag publicado
no se mueve, el contenido se publica como PATCH `1.5.3`. Bump
coherente de la fuente de versión, entrada `## [1.5.3]` en
`CHANGELOG.md` (R-04) con el fix del hook Windows y regeneración
de `uv.lock`. Orden del programador: spec, bump, commit, limpiar
arnés, commit, tag y release.

## Precondiciones

- Rama `main`, HEAD `bba0259` (archival `historial/1.5.2`
  commiteado y pusheado), árbol limpio, CI en verde.
- Último tag `v1.5.2` (publicado, inmutable); `release propose`
  indica «sin incremento»; el humano confirma PATCH `1.5.3`.
- Sin tareas en `proceso`.

## Requisitos EARS

- REQ-01: WHEN se aplique el bump, THE `__version__` en
  `.microharness/sdd.py`, `HARNESS_VERSION` en
  `.microharness/metrics.py` y `version` en `pyproject.toml`
  SHALL ser `1.5.3`.
- REQ-02: WHEN se ejecute `sdd.py --version`, THE salida SHALL ser
  `MicroSDD 1.5.3`.
- REQ-03: WHEN se lea `CHANGELOG.md`, THE sección `[1.5.3]` SHALL
  describir el fix del hook bajo `Corregido` y documentar el tag
  prematuro `v1.5.2`.
- REQ-04: WHEN se ejecute la suite, THE pins de versión SHALL
  exigir `1.5.3` y el test de coherencia SHALL seguir pasando.

## Criterios de aceptación

- AC-01: `sdd.py --version` imprime `MicroSDD 1.5.3`,
  `pyproject.toml` declara `version = "1.5.3"` y `metrics.py`
  declara `HARNESS_VERSION = '1.5.3'`.
- AC-02: `CHANGELOG.md` contiene `## [1.5.3]` con el fix del hook
  en `Corregido` y la nota del tag `v1.5.2`.
- AC-03: pins en `1.5.3`, `uv.lock` regenerado y tests enfocados
  en verde.
- AC-04: `check release-v1-5-3 --run` pasa y la suite completa está
  en verde en el commit candidato.

## Fuera de alcance

- Mover o borrar el tag publicado `v1.5.2` (prohibido).
- Cambios de API, instalador, agentes, bench o hook.
- `git push` y release de GitHub (autorizaciones independientes,
  ya otorgadas por el programador en este flujo).
