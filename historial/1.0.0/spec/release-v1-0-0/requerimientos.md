# QUÉ: requisitos

## Objetivo

Preparar el release 1.0.0 de MicroSDD en el árbol: crear `CHANGELOG.md` con una sección `[1.0.0]` derivada de los commits reales desde el inicio del repositorio, fijar la versión `1.0.0` en sus fuentes (`__version__` de `.microharness/sdd.py` y `version` de `pyproject.toml`, con prueba de coherencia) y corregir las frases de `assets/proceso-versionado.md` que dejen de ser ciertas o que ya no lo son (API-02 sobre `mutation.command`). No crea tags, no publica nada y no ejecuta `scripts/limpiar_arnes.py`.

La versión 1.0.0 la fija el programador (decisión registrada en `memory.json`, 2026-10-13), aunque `release propose` sugiera `0.1.0` por no haber tags. C-03 y C-04 de «Criterios para declarar 1.0.0» no se cumplen y el programador los acepta como desviación (decisión registrada en memoria); ver `plan.md`.

## Precondiciones

- P-01: rama `main`, sin tags (`git tag` vacío) y ninguna tarea en `proceso` (comprobado el 2026-10-13).
- P-02: último commit incluido en el CHANGELOG: `5bd110e` (`HEAD` al especificar). Si `HEAD` cambia antes de implementar, el líder debe reabrir la spec.
- P-03: suite en verde antes del cambio: `python -m unittest discover -s tests` → `Ran 175 tests`, `OK (skipped=2)` (comprobado el 2026-10-13 sobre `5bd110e`).
- P-04: la tarea `release-v1-0-0` se implementa antes que `bloquear-autoaprobacion`, que añadirá su propia entrada a la sección `[1.0.0]` en su tarea.
- P-05: aprobación humana `spec` de esta tarea, que además constituye la decisión explícita del criterio C-08.

## Requisitos EARS

- REQ-01: WHEN se ejecuta `.microharness/sdd.py --version`, THE CLI SHALL imprimir `MicroSDD 1.0.0` y salir con código 0.
- REQ-02: THE archivo `.microharness/sdd.py` SHALL contener exactamente una línea `__version__ = '1.0.0'`, y `pyproject.toml` SHALL declarar `version = "1.0.0"` en `[project]`; no SHALL quedar ninguna otra declaración de versión del paquete con `0.1.0` fuera de `tests/`, `spec/`, `historial/` y `.microharness/memory.json`.
- REQ-03: THE archivo `CHANGELOG.md` SHALL existir en la raíz con una única sección `## [1.0.0] - 2026-10-13` y, dentro de ella, solo los grupos «Incompatible», «Añadido», «Corregido» y «Otros», en ese orden, como encabezados `###`; SHALL NOT contener secciones `[Unreleased]`, marcadores ni entradas de tareas futuras.
- REQ-04: THE sección `[1.0.0]` SHALL contener exactamente una entrada por cada commit sin merge alcanzable desde `5bd110e` (40 commits), en el grupo que le asigna `release propose` (Incompatible 2, Añadido 18, Corregido 9, Otros 11), en orden cronológico dentro de cada grupo, y SHALL omitir los 3 commits de merge (`80facf8`, `d34ba63`, `fd39a92`) con una nota que lo justifique.
- REQ-05: Cada entrada SHALL tener la forma `- <descripción del asunto, sin el prefijo tipo(scope)!:> (<hash corto>)`, con el scope, si existe, como prefijo `` `scope`: ``, sin añadir contenido que no esté en el asunto del commit.
- REQ-06: WHEN una frase de `assets/proceso-versionado.md` deja de ser cierta por esta tarea o contradice el código, THE documento SHALL corregirse con el cambio mínimo, limitado a: «Estado actual»; la frase del primer tag en «Fase 0.y.z»; la frase «tampoco existe `CHANGELOG.md`» de «Herramienta de release»; «`CHANGELOG.md` (cuando exista)» en «Excluido»; y, en API-02, la condición de la lista blanca para `mutation.command`. El resto del documento SHALL quedar intacto.
- REQ-07: THE texto de API-02 SHALL indicar que, salvo en `terminado`, `testing.commands` se valida siempre contra la lista blanca y `mutation.command` solo cuando `mutation.enabled` es verdadero, como hace `validate()` en `.microharness/sdd.py` (líneas 462-464).
- REQ-08: WHEN se ejecuta la suite `python -m unittest discover -s tests -v`, THE suite SHALL terminar con código 0; `test_version_flag_prints_microsdd_version` SHALL exigir `1.0.0` y SHALL comprobar con regex que `version` de `pyproject.toml` coincide con `__version__`.
- REQ-09: IF el wheel se construye con `uv build --wheel`, THEN su nombre y metadatos SHALL llevar la versión `1.0.0`.
- REQ-10: THE tarea SHALL NOT crear tags, hacer push, crear releases de GitHub, ejecutar `scripts/limpiar_arnes.py` ni modificar `historial/`.

## Criterios de aceptación

- AC-01: `sh .microharness/python.sh .microharness/sdd.py --version` imprime exactamente `MicroSDD 1.0.0` con código 0; `test_version_flag_prints_microsdd_version` lo verifica y pasa.
- AC-02: `.microharness/sdd.py` contiene una sola línea que casa con `^__version__ = '1\.0\.0'$` y ninguna con `0.1.0`; `git grep -n "0\.1\.0" -- ':!tests' ':!spec' ':!historial' ':!.microharness/memory.json' ':!CHANGELOG.md'` no devuelve declaraciones de versión (solo menciones históricas enumeradas en `plan.md`).
- AC-03: `pyproject.toml` contiene `version = "1.0.0"` en `[project]` y ningún otro campo cambia; `VersionTests` falla si `pyproject.toml` y `__version__` divergen (comprobable cambiando uno de los dos temporalmente) y pasa con ambos en `1.0.0`.
- AC-04: `CHANGELOG.md` existe; tiene exactamente un encabezado `## [1.0.0] - 2026-10-13` y bajo él `### Incompatible`, `### Añadido`, `### Corregido`, `### Otros` en ese orden; no contiene `[Unreleased]`, marcadores ni entradas de `bloquear-autoaprobacion`.
- AC-05: los hashes cortos de `CHANGELOG.md` son exactamente el conjunto de `git log --no-merges --format=%h 5bd110e` (40, sin repetidos, incluido `5bd110e` en «Otros») y ninguno de `git log --merges --format=%h 5bd110e`; cada hash está en el grupo que le asigna `release propose` (2/18/9/11) y en el orden de `git log --reverse` dentro del grupo.
- AC-06: cada entrada reproduce literalmente la descripción del asunto de su commit tras quitar `tipo(scope)!: ` (erratas incluidas), sin texto añadido salvo el prefijo de scope y el hash; `CHANGELOG.md` incluye una nota que explica la omisión de los 3 merges.
- AC-07: en `assets/proceso-versionado.md`, `git diff` solo muestra cambios en: «Estado actual», la frase del primer tag de «Fase 0.y.z», la frase sobre `CHANGELOG.md` de «Herramienta de release», «(cuando exista)» de «Excluido» y la frase de la lista blanca de API-02. El nuevo «Estado actual» refleja: sin tags hasta crear `v1.0.0`, existencia de `CHANGELOG.md`, `__version__` = `1.0.0` replicado en `pyproject.toml`, y que no hubo release 0.y.z por decisión del programador. `tests/test_api_publica.py` sigue en verde.
- AC-08: API-02 dice que `mutation.command` se valida contra la lista blanca solo si `mutation.enabled` es verdadero (y `testing.commands` siempre, salvo en `terminado`); el texto coincide con `validate()` de `.microharness/sdd.py`.
- AC-09: `python -m unittest discover -s tests -v` termina con código 0 y el recuento no baja de 175 pruebas; `check release-v1-0-0 --run` pasa.
- AC-10: `uv build --wheel --out-dir <directorio temporal>` produce `microsdd-1.0.0-py3-none-any.whl` cuyo `METADATA` contiene `Version: 1.0.0` (evidencia manual del implementador; la suite no lo comprueba).
- AC-11: `git status` y `git tag` tras la implementación muestran cambios solo dentro de `scope.allowed_paths` (más `.microharness/memory.json` del flujo) y ningún tag; `historial/` no existe o no cambia.

## Fuera de alcance

- Crear el tag `v1.0.0`, push, release de GitHub y ejecutar `scripts/limpiar_arnes.py 1.0.0` (pasos posteriores del líder, tras `bloquear-autoaprobacion`).
- La entrada de `bloquear-autoaprobacion` en el CHANGELOG (la añade esa tarea dentro de `[1.0.0]`).
- Implementar `release prepare` o `release tag`.
- Cualquier otro cambio de API-01 a API-09 o de «Instalación» distinto de los enumerados en REQ-06.
- Reescribir los asuntos de commit o corregir sus erratas.
- Cambiar `README.md` (no menciona ninguna versión del paquete; comprobado con `grep`), `src/**`, `scripts/**`, `.claude/**`, `CLAUDE.md`, `tests/test_api_publica.py` y las specs o la memoria de otras tareas, incluida la spec cerrada de `herramienta-release`.
