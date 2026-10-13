# QUÉ: requisitos

## Objetivo

Dejar las secciones «API pública» e «Instalación» de `assets/proceso-versionado.md` coherentes con el código actual (`.microharness/sdd.py`, `src/microsdd/installer.py`, `.claude/hooks/pretool.py`), con cambio mínimo, para que el criterio C-01 («API pública documentada y vigente») pueda darse por cumplido en la revisión de `release-v1-0-0`. Añadir una prueba unittest que falle si la CLI o el manifiesto del instalador vuelven a divergir del documento.

No se modifica código de aplicación (`sdd.py`, instalador, hook, `pyproject.toml`, `README.md`).

## Precondiciones

- P-01: `HEAD` = `5caba80` en `main`, sin tags; suite en verde: `python -m unittest discover -s tests` → `Ran 171 tests`, `OK (skipped=2)` (comprobado el 2026-10-13).
- P-02: esta tarea se implementa y cierra antes que `release-v1-0-0`; esa tarea no se modifica aquí (el líder actualiza su spec después, ver `plan.md`).
- P-03: aprobación humana `spec` de esta tarea, incluidas las decisiones D-01 a D-05 de `plan.md`.

## Requisitos EARS

- REQ-01: THE sección «API pública» SHALL nombrar, entre comillas invertidas, cada subcomando del parser de `sdd.py` (`init`, `new`, `check`, `approve`, `review`, `seal`, `note`, `commit-check`, `release`), cada acción de `release` (`propose`) y la opción global `--version`.
- REQ-02: THE sección «API pública» SHALL nombrar, entre comillas invertidas, cada opción larga (`--…`, salvo `--help`) que acepta cada subcomando (`--run`, `--no-scope`, `--by`, `--evidence`, `--fact`, `--decision`).
- REQ-03: THE subsección «Instalación / Incluido» SHALL nombrar, entre comillas invertidas, cada ruta de origen y de destino de `MANIFEST` y cada ruta de `INIT_FILES` de `src/microsdd/installer.py`.
- REQ-04: IF un elemento de lista de «Instalación / Incluido» empieza por una ruta entre comillas invertidas, THEN esa ruta SHALL pertenecer al conjunto instalado (claves y valores de `MANIFEST`, `INIT_FILES` y `spec/`).
- REQ-05: THE API-02 SHALL documentar `testing.min_tests` (entero ≥ 1, opcional, 1 por defecto) y que `testing.commands` y `mutation.command` deben empezar por un runner de la lista blanca, ampliable con `project.allowed_test_commands`.
- REQ-06: THE API-03 SHALL documentar `project.allowed_test_commands`, la comprobación de integridad de `memory.json` frente a `HEAD` que realiza `check`, y el archivo de lock `.microharness/memory.lock` (no versionado; su contenido no es API).
- REQ-07: THE documento SHALL incluir `.microharness/config.json` en la API pública como API-09 (opcional, humano, claves `model` y `effort`, no lo crea el instalador), y la referencia «API-01 a API-08» de «Reglas de incremento» SHALL pasar a «API-01 a API-09».
- REQ-08: THE API-05 SHALL mencionar que el hook deniega `Write`, `Edit`, `MultiEdit`, `NotebookEdit`, `Bash` y `PowerShell` a cualquier agente que no sea `autor`, `implementador`, `revisor` o `lider` (fail-closed).
- REQ-09: THE sección «Instalación» SHALL describir lo que hace el instalador: copia solo `MANIFEST` (con `CLAUDE.md` del arnés como `CLAUDE.microsdd.md` y un bloque de registro anexado al `CLAUDE.md` destino), usa `.claude/settings.microsdd.json` si `.claude/settings.json` existe y difiere, genera con `sdd.py init` `docs/` (nombres `convenciones.md` y `especificaciones.md`, con aviso y sin mover archivos si existen los nombres antiguos), `spec/` y `.microharness/memory.json`; y «Excluido» SHALL listar lo versionado que no se instala.
- REQ-10: WHEN se ejecuta `python -m unittest discover -s tests -v`, THE suite SHALL terminar con código 0 e incluir la prueba nueva, que SHALL fallar si se elimina del documento cualquier nombre exigido por REQ-01 a REQ-03 o si se añade a «Incluido» una ruta no instalada.
- REQ-11: THE cambio en `assets/proceso-versionado.md` SHALL limitarse a «API pública», la viñeta de «Reglas de incremento» que cita «API-01 a API-08» e «Instalación»; «Estado actual», «Fase 0.y.z», «Criterios para declarar 1.0.0», «Tags y prereleases», «Release dentro del flujo MicroSDD» y «Herramienta de release» SHALL quedar intactas.

## Criterios de aceptación

- AC-01: `tests/test_api_publica.py` obtiene los subcomandos y `--version` de la salida real de `sdd.py --help` (y las acciones de `sdd.py release --help`) y comprueba que cada uno aparece como `` `nombre` `` en la sección «API pública»; pasa tras el cambio y falla con el documento actual (fase RED registrada).
- AC-02: la misma prueba obtiene las opciones largas de `sdd.py <subcomando> --help` (excluido `--help`) y comprueba que cada una aparece como `` `--opción` `` en «API pública».
- AC-03: la prueba carga `src/microsdd/installer.py` y comprueba que cada clave y valor de `MANIFEST` y cada elemento de `INIT_FILES` aparece como `` `ruta` `` en «Instalación / Incluido» (texto entre `### Incluido` y `### Excluido`).
- AC-04: la prueba comprueba que la primera ruta entre comillas invertidas de cada elemento de lista (`- `…) de «Incluido» pertenece al conjunto instalado; `README.md`, `.gitignore` y `tests/test_sdd.py` dejan de figurar como elementos de esa lista.
- AC-05: API-02 menciona `testing.min_tests` y la lista blanca de runners; API-03 menciona `project.allowed_test_commands`, la integridad frente a `HEAD` y `.microharness/memory.lock` (comprobación con `grep` en la revisión).
- AC-06: existe una viñeta **API-09** sobre `.microharness/config.json` (opcional, `model`/`effort`, no lo crea el instalador) y la viñeta de «Reglas de incremento» dice «API-01 a API-09».
- AC-07: API-05 menciona la denegación fail-closed a agentes sin rol MicroSDD; «Instalación» menciona `CLAUDE.microsdd.md` con el bloque de registro, `.claude/settings.microsdd.json`, los nombres `docs/convenciones.md` y `docs/especificaciones.md` y la compatibilidad con `docs/convensiones.md` y `docs/specificaciones.md`.
- AC-08: «Instalación» ya no afirma que se copia «todo el contenido versionado» ni que `assets/` es «la única exclusión» ni que `CHANGELOG.md` se incluirá; «Excluido» enumera al menos `assets/`, `scripts/`, `historial/`, `src/`, `tests/`, `pyproject.toml`, `README.md`, `LICENSE`, `.gitignore` y `CHANGELOG.md`, e indica que `.microharness/config.json` no se crea.
- AC-09: `git diff assets/proceso-versionado.md` solo muestra cambios dentro de «API pública», de la viñeta «El tipo es una señal…» de «Reglas de incremento» y de «Instalación».
- AC-10: `python -m unittest discover -s tests -v` termina con código 0 y `Ran` ≥ 172 pruebas; `sdd.py check api-publica-vigente --run` pasa.
- AC-11: `git status` tras la implementación muestra cambios solo en `scope.allowed_paths` (más `.microharness/memory.json` del flujo y las specs ajenas ya existentes sin confirmar); `.microharness/sdd.py`, `src/**`, `.claude/**`, `pyproject.toml` y `README.md` sin cambios.

## Fuera de alcance

- Cambiar `.microharness/sdd.py`, `src/microsdd/installer.py`, `.claude/**`, `pyproject.toml`, `README.md`, `scripts/**` o `CLAUDE.md`.
- Secciones de `assets/proceso-versionado.md` que corresponden a `release-v1-0-0`: «Estado actual», la frase del primer tag en «Fase 0.y.z» y la frase sobre `CHANGELOG.md` de «Herramienta de release»; ni el resto de secciones listadas en REQ-11.
- Evaluar C-02 a C-08, crear `CHANGELOG.md`, cambiar la versión o modificar la spec de `release-v1-0-0` u otras tareas.
- Documentar textos de mensajes de salida (no son API) o el instalador `microsdd install` como API (no figura en API-01..API-08; ver D-05).
- Probar automáticamente los requisitos en prosa REQ-05 a REQ-09 (se verifican en revisión).
