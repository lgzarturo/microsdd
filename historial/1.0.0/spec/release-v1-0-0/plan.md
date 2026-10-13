# CÓMO: diseño mínimo

## Situación comprobada

Hechos observados el 2026-10-13 en `main` (`HEAD` = `5bd110e`):

- Sin tags (`git tag` vacío). No existen `CHANGELOG.md` ni `VERSION`.
- Declaraciones de versión del paquete: `.microharness/sdd.py:28` `__version__ = '0.1.0'` y `pyproject.toml:7` `version = "0.1.0"`. No hay otras: `src/microsdd/__init__.py` solo tiene docstring, `installer.py` no usa versión del paquete (solo `uv --version`), no hay `uv.lock`, y `README.md` no menciona versión (su título es «MicroSDD for Claude Opus 5.5»; la afirmación de `assets/proceso-versionado.md` sobre «MicroSDD 0.1» en el título ya era falsa).
- `sdd.py --version` usa `__version__` (argparse). `release propose` sin tags toma la versión de `__version__` (quitando `-rc.N`); tras el cambio propondrá `1.0.0` hasta que exista un tag.
- `release propose` (ejecutado sobre `5bd110e`): `Último tag: (ninguno)`, `Versión propuesta: 0.1.0`. 40 commits sin merge: Incompatible 2 (`289b996`, `64e4733`), Añadido 18, Corregido 9, Otros 11 (11 `docs`/`chore`, el último `5bd110e`); más 3 merges clasificados como «Otros».
- Pruebas que fijan `0.1.0`: solo `tests/test_sdd.py::VersionTests::test_version_flag_prints_microsdd_version` lee el script real. `ReleaseProposeTests` usa repos temporales con su propio `write_version('0.1.0')`: no cambia.
- `tests/test_api_publica.py` (de `api-publica-vigente`) solo exige que los nombres de subcomandos/opciones aparezcan en «API pública» y que «Incluido» coincida con el instalador; los cambios de redacción previstos no lo afectan.
- `tests/test_installer.py` construye el wheel con `uv` pero no comprueba la versión.
- `validate()` (`.microharness/sdd.py:462-464`) solo comprueba `mutation.command` contra la lista blanca si `mutation.enabled`; API-02 dice hoy que siempre («`testing.commands` y `mutation.command` deben empezar por un runner…»).
- «Excluido» dice «`CHANGELOG.md` (cuando exista)»: deja de ser condicional.
- Suite actual: `Ran 175 tests`, `OK (skipped=2)`.
- `testing.commands` solo admite runners de `TEST_COMMANDS`: lo observable se verifica con la suite o con evidencia manual.

## Decisión y justificación

Decisiones del programador registradas: D-01 fecha `2026-10-13`; D-02 prueba de coherencia `pyproject.toml`/`__version__` por regex; D-04 asuntos literales (erratas incluidas); D-05 mensaje de commit `chore(release): prepara CHANGELOG y versión 1.0.0`; `tests/test_sdd.py` no se sella en la serie.

1. **Versión.** Sustituir `0.1.0` por `1.0.0` en `.microharness/sdd.py:28` (por Bash) y en `pyproject.toml:7`. Dos literales más una aserción en vez de versión dinámica de hatch: cambio mínimo, sin tocar la configuración de build.
2. **Prueba.** En `test_version_flag_prints_microsdd_version`: `0.1.0` → `1.0.0` en la salida esperada y en la regex, y una aserción nueva que lea `pyproject.toml` con `re.search(r'^version = "([^"]+)"$', ..., re.M)` (sin `tomllib`, ausente en 3.10) y compare con el valor de `__version__`. Sin pruebas del CHANGELOG (YAGNI: se verifica en revisión con comandos Git).
3. **CHANGELOG.md** (nuevo):

   ```
   # Registro de cambios

   Formato y reglas: `assets/proceso-versionado.md` (R-04). Entradas derivadas de los asuntos de commit; se omiten los commits de merge, que no aportan cambios propios (su contenido figura en los commits integrados).

   ## [1.0.0] - 2026-10-13

   ### Incompatible
   - `spec`: renombra diseño.md a plan.md en las 15 tareas (289b996)
   - `docs`: renombra convensiones.md y specificaciones.md (64e4733)

   ### Añadido
   - definir espacio de memoria (bd91f95)
   ...
   ### Corregido
   ...
   ### Otros
   ...
   - `assets`: actualiza API pública e instalación del proceso de versionado (5bd110e)
   ```

   Reglas: una entrada por commit sin merge alcanzable desde `5bd110e`; grupo según `release propose`; orden de `git log --reverse` dentro del grupo; descripción literal tras `tipo(scope)!: `; scope como prefijo en código; hash corto de 7 caracteres. El implementador genera la lista con `git log --no-merges --reverse --format='%h %s' 5bd110e` y la contrasta con `release propose`.

   **Preparado para `bloquear-autoaprobacion`:** la sección `[1.0.0]` y sus cuatro grupos existen, de modo que esa tarea solo añade su línea al final del grupo que le corresponda (mismo formato, con el hash de su commit). No se crea `[Unreleased]`, ni marcadores, ni entradas anticipadas. Esa tarea debe incluir `CHANGELOG.md` en su `allowed_paths` (hoy no lo tiene).
4. **`assets/proceso-versionado.md`**, cambio mínimo en cinco puntos:
   - «Estado actual» (líneas 13-16): sin tags hasta crear `v1.0.0` tras `scripts/limpiar_arnes.py 1.0.0`; existe `CHANGELOG.md` (sección `[1.0.0]`) y no existe `VERSION`; `__version__` = `1.0.0`, expuesta con `--version`, replicada en `pyproject.toml`; no hubo release 0.y.z: el programador fijó 1.0.0 (2026-10-13). Se elimina la frase falsa sobre el título del README.
   - «Fase 0.y.z», línea 51: la frase «El primer tag será `v0.1.0`…» pasa a decir que el primer tag es `v1.0.0` por decisión del programador; la regla de la fase 0 queda intacta.
   - API-02: «salvo en `terminado`, `testing.commands` y `mutation.command` deben empezar…» → «salvo en `terminado`, `testing.commands` (y `mutation.command` si `mutation.enabled` es verdadero) deben empezar…». Solo esa frase.
   - «Excluido»: quitar «(cuando exista)» tras `CHANGELOG.md`.
   - «Herramienta de release», línea 127: eliminar «; tampoco existe `CHANGELOG.md`».
   - Menciones a `0.1` que pueden quedar: «MicroSDD 0.1» en la frase de «Fase 0.y.z» (histórica) y `assets/decisiones-diseno.md` («README 0.1» como fuente); ninguna es declaración de versión.
5. **`docs/**`**: solo el líder, tras el cierre, añade la fila de la tarea en `docs/especificaciones.md`.

## Evaluación de «Criterios para declarar 1.0.0»

| Criterio | ¿Se cumple? | Evidencia |
|---|---|---|
| C-01 API pública documentada y vigente | **Sí** | Tarea `api-publica-vigente` cerrada (commit `5bd110e`); `tests/test_api_publica.py` en verde. Esta tarea corrige además la condición de `mutation.command` de API-02 (AC-08). |
| C-02 Herramienta de release implementada | **Parcial** | `herramienta-release` está `terminado` con `close`; solo existe `propose` (R-01 pide también `prepare` y `tag`). Su `check --run` falla hoy (su comando histórico exige un árbol limpio fuera de su alcance) y, tras esta tarea, fallará siempre por la aserción `__version__ = '0.1.0'`. |
| C-03 Al menos un release 0.y.z | **No: desviación aceptada** | `git tag -l "v0.*"` vacío; el programador decidió publicar directamente v1.0.0 (decisión registrada en memoria). |
| C-04 Evaluación del MVP | **No: desviación aceptada** | Sin observaciones de resultados en `memory.json`; `assets/eval-esfuerzo.md` «no ejecutado». Aceptado por el programador (decisión registrada en memoria). |
| C-05 Defectos de instalación conocidos | **Sí** | `deteccion-python-multiplataforma` y `fix-quotepath-diff` en `terminado`. |
| C-06 `CHANGELOG.md` con entrada 1.0.0 | **Lo cumple esta tarea** | AC-04 a AC-06. |
| C-07 Suite completa en verde | **Sí hoy; a verificar en el commit candidato** | 175 pruebas, `OK (skipped=2)`; AC-09. |
| C-08 Decisión humana explícita | **Pendiente** | Se cumple con la aprobación `spec` de esta tarea (P-05). |

C-02 parcial no tiene decisión registrada específica; queda informado para la aprobación `spec`.

## Invariantes y riesgos

- Invariante: `__version__` es la fuente de verdad (`--version`, `release propose` sin tags); `pyproject.toml` la replica y la prueba lo vigila.
- Invariante: ningún tag, push ni ejecución de `limpiar_arnes` dentro de la tarea.
- Riesgo (efecto secundario): `check herramienta-release --run` fallará permanentemente por su aserción histórica de `0.1.0`. No se modifica una spec cerrada; anotarlo en el cierre.
- Riesgo: `bloquear-autoaprobacion` debe añadir `CHANGELOG.md` a su `allowed_paths`.
- Riesgo: si el tag se crea otro día, la fecha `2026-10-13` no coincidirá con la del tag (decisión D-01 registrada).
- Riesgo: commits posteriores a `5bd110e` (el de esta tarea, el de `bloquear-autoaprobacion`, el de `limpiar_arnes`) no figuran; cada tarea añade lo suyo. El commit `chore(release)` de esta tarea no se lista a sí mismo.
- Riesgo: `tests/test_sdd.py` no se sella (decisión del programador): la revisión debe comprobar que el cambio de la prueba se limita a `VersionTests`.

## Alternativas descartadas

- Versión dinámica en `pyproject.toml` con hatch: cambia la configuración de build; mayor superficie que una aserción.
- Archivo `VERSION`: tercera fuente; contradice «Fuente única de versión en el árbol».
- Generar el CHANGELOG con un script o `release prepare`: no existe y no se pidió.
- Sección `[Unreleased]` para la entrada futura de `bloquear-autoaprobacion`: anticipa contenido; esa tarea escribe directamente en `[1.0.0]`.
- Incluir los merges en «Otros»: no aportan cambios propios; se omiten con nota.

## Decisiones abiertas (para el líder)

Ninguna bloqueante.
