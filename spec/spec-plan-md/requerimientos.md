# QUÉ: requisitos

## Objetivo
Renombrar el documento de diseño de cada tarea MicroSDD de `diseño.md` a `plan.md` en todo el arnés (controlador, hook, contrato del autor, README, proceso de versionado y pruebas); migrar las 15 tareas existentes en `spec/` recalculando sus huellas de aprobación `spec` con un script puntual y auditable que no «lava» specs alteradas; y adoptar la regla de que los nombres de archivo del arnés y de `spec/<slug>/` sean solo ASCII, con una comprobación mínima en `sdd.py check`.

Motivo comprobado: `diseño.md` es el único nombre de archivo no ASCII del repositorio (`git -c core.quotePath=false ls-files` solo lista los 14 `spec/*/diseño.md` versionados) y ya motivó dos tareas correctivas (`fix-sdd-rutas-unicode`, `fix-quotepath-diff`) y un fallo del hook del autor al decodificar stdin en cp1252.

## Precondiciones
- PRE-01: decisiones humanas registradas en `.microharness/memory.json` (`project.decisions`): 2026-10-13T05:46:43Z (renombrar también las tareas existentes; modificar y resellar `tests/test_sdd.py`; nombres solo ASCII) y 2026-10-13T05:55:35Z (Q-01 opción b: recalcular huellas con script puntual auditable, sin etiqueta histórica en el código; Q-02: nota de migración en README; Q-03: excepción de edición y commit con `!`).
- PRE-02: según la decisión 2026-10-13T05:55:35Z (Q-03), en esta tarea el implementador puede editar solo `.microharness/sdd.py`, `.claude/hooks/pretool.py` y `.claude/agents/autor.md` dentro de `.claude/` y `.microharness/`. Si la guardia lo deniega, el líder entrega el parche al humano. No se planean rodeos.
- PRE-03: el renombrado `spec/<slug>/diseño.md` → `spec/<slug>/plan.md` y la ejecución del script de migración los realiza el líder (puede editar `spec/` y `.microharness/memory.json`), no el implementador. El implementador escribe el script y sus pruebas.
- PRE-04: línea base comprobada: `sdd.py check <slug>` devuelve OK para las 14 tareas `terminado`.
- PRE-05: Python ≥3.10 y `git` disponibles; solo biblioteca estándar.

## Requisitos EARS
- REQ-01: WHEN se ejecute `sdd.py new <slug>`, THE controlador SHALL crear en `spec/<slug>/` exactamente `spec.json`, `requerimientos.md`, `plan.md` y `tareas.md`.
- REQ-02: WHEN se ejecute `sdd.py check <slug>`, THE controlador SHALL exigir `spec/<slug>/plan.md` y aplicar sobre él la detección de marcadores de plantilla; IF falta, THEN SHALL informar `Falta spec/<slug>/plan.md` y terminar con código 1.
- REQ-03: IF `spec/<slug>/` contiene alguna entrada cuyo nombre tiene caracteres no ASCII, THEN `sdd.py check <slug>` SHALL informar un error que nombre esa entrada y terminar con código 1.
- REQ-04: THE huella de especificación (`spec_fingerprint`) SHALL leer `plan.md` y usar `plan.md` como nombre en el cálculo; `.microharness/sdd.py` SHALL NOT contener el literal `diseño.md`.
- REQ-05: IF el contenido de `plan.md` cambia después de la aprobación `spec`, THEN `sdd.py check <slug>` SHALL informar «Especificación alterada después de aprobación» (comportamiento actual, incluida la tolerancia LF/CRLF).
- REQ-06: WHILE el agente sea `autor`, THE hook `PreToolUse` SHALL permitir `Write`/`Edit` sobre `spec/<slug>/plan.md` y SHALL denegar `spec/<slug>/diseño.md`.
- REQ-07: WHEN se ejecute `scripts/migrar_plan_md.py <raíz>` y, para cada tarea con aprobación `spec`, la huella almacenada coincida con la huella del esquema antiguo (nombre `diseño.md`) calculada sobre el contenido actual de `plan.md`, THE script SHALL reescribir `approvals.spec.fingerprint` con la huella del esquema nuevo y SHALL añadir a esa tarea un evento `migración_plan_md` con la huella anterior y la nueva, sin modificar ningún otro campo.
- REQ-08: IF alguna tarea con aprobación `spec` tiene una huella almacenada que no coincide ni con el esquema antiguo ni con el nuevo, o carece de `plan.md`, o algún `spec/<slug>/` conserva `diseño.md`, THEN el script SHALL terminar con código 1 nombrando la tarea y SHALL NOT escribir nada en `memory.json`.
- REQ-09: WHEN el script se ejecute de nuevo sobre tareas ya migradas (huella almacenada igual al esquema nuevo), THE script SHALL omitirlas sin escribir ni añadir eventos y terminar con código 0.
- REQ-10: WHEN termine la migración del repositorio, THE repositorio SHALL contener `plan.md` y ningún `diseño.md` en cada una de las 15 tareas, y `sdd.py check <slug> --no-scope` SHALL devolver OK para todas ellas; las huellas cambiadas SHALL estar respaldadas por un evento `migración_plan_md` cada una.
- REQ-11: THE contrato del autor (`.claude/agents/autor.md`), `README.md` y `assets/proceso-versionado.md` (API-04) SHALL nombrar `plan.md` en lugar de `diseño.md`; `README.md` SHALL indicar que los nombres de archivo del arnés y de `spec/<slug>/` son solo ASCII y SHALL incluir una nota breve de migración para repositorios ya instalados.
- REQ-12: THE resto del comportamiento de `sdd.py` y del hook SHALL mantenerse sin cambios; la suite completa SHALL terminar con código 0.

## Criterios de aceptación
- AC-01 (REQ-01): una prueba ejecuta `sdd.new` en un directorio temporal y comprueba que el conjunto de nombres de `spec/<slug>/` es literalmente `{'spec.json', 'requerimientos.md', 'plan.md', 'tareas.md'}` (sin derivarlo de `TASK_FILES`).
- AC-02 (REQ-02): una prueba sustituye `plan.md` por un `diseño.md` en una tarea válida y comprueba que `validate` contiene `Falta spec/<slug>/plan.md`; otra deja en `plan.md` el marcador de plantilla que escribe `new` (la palabra PENDIENTE entre corchetes) y comprueba el error `plan.md conserva marcadores de plantilla`.
- AC-03 (REQ-03): una prueba añade `notas-año.md` a una tarea válida y comprueba que `validate` devuelve un error que contiene `notas-año.md` y `ASCII`; con un archivo extra `notas.md` no aparece ningún error de ASCII (los archivos extra ASCII se siguen tolerando como hoy).
- AC-04 (REQ-04): `git grep -n "diseño\.md" -- .microharness/sdd.py` no devuelve nada; las pruebas de AC-05 y AC-07 pasan con la huella calculada sobre `plan.md`.
- AC-05 (REQ-05): `test_spec_approval_and_fingerprint` y `test_spec_fingerprint_ignores_crlf_conversion`, adaptados a `plan.md`, pasan: la conversión LF→CRLF no invalida la aprobación y un cambio real en `plan.md` sí.
- AC-06 (REQ-06): una prueba invoca `hook.run` con `agent_type: 'autor'`, `tool_name: 'Write'` y `cwd` temporal: `spec/x/plan.md` devuelve `None` (permitido) y `spec/x/diseño.md` devuelve un motivo de denegación.
- AC-07 (REQ-07): en un repositorio temporal con dos tareas aprobadas cuya huella almacenada es una constante obtenida con el `spec_fingerprint` del commit `61bd1ee` sobre contenido fijo (LF) guardado como `diseño.md`, y una tercera tarea sin aprobación `spec`, tras renombrar a `plan.md` el script termina con código 0; cada tarea aprobada tiene `approvals.spec.fingerprint` igual a `sdd.spec_fingerprint` (código nuevo), `sdd.validate` no informa «alterada» y existe exactamente un evento `migración_plan_md` con `old` igual a la constante y `new` igual a la huella nueva; `by`, `evidence`, `at`, `close`, `review`, `review_fingerprint` y `sealed_tests` no cambian; la tarea sin aprobación queda intacta.
- AC-08 (REQ-08): con el mismo repositorio temporal, (a) si una de las tareas aprobadas tiene `plan.md` alterado, (b) si queda un `spec/<slug>/diseño.md`, o (c) si falta `plan.md` en una tarea aprobada, el script termina con código 1, la salida nombra la tarea y los bytes de `memory.json` no cambian (tampoco los de la tarea válida).
- AC-09 (REQ-09): una segunda ejecución del script tras AC-07 termina con código 0 y los bytes de `memory.json` no cambian (sin eventos nuevos).
- AC-10 (REQ-10): en el repositorio real, tras el renombrado y el script: `ls spec/*/diseño.md` no encuentra archivos; `ls spec/*/plan.md` lista 15; `check <slug> --no-scope` devuelve OK en las 15 tareas; `git -c core.quotePath=false ls-files --cached --others --exclude-standard | grep -P '[^\x00-\x7F]'` no devuelve nada; `memory.json` tiene un evento `migración_plan_md` por cada tarea con aprobación `spec` (15); `git diff HEAD -- .microharness/memory.json | grep -E '^-.*"(review_fingerprint|by|evidence|at)"'` no devuelve nada.
- AC-11 (REQ-11): `git grep -n "diseño\.md" -- . ':!spec/*' ':!.microharness/memory.json' ':!docs/*'` solo devuelve líneas de `scripts/migrar_plan_md.py` (esquema antiguo), de la nota de migración de `README.md` y de las pruebas de AC-02, AC-06, AC-07 y AC-08; el punto 3 de `.claude/agents/autor.md` empieza por `` `plan.md` ``; la línea API-04 de `assets/proceso-versionado.md` nombra `plan.md`; `README.md` contiene la regla de nombres solo ASCII y la nota de migración (actualizar el arnés, renombrar a `plan.md`, ejecutar el script desde una copia de MicroSDD o reaprobar las tareas no terminadas).
- AC-12 (REQ-12): `python -m unittest discover -s tests` termina con código 0 y `sh .microharness/python.sh .microharness/sdd.py check spec-plan-md --run` devuelve OK.

## Fuera de alcance
- Corregir la decodificación de stdin del hook (tarea `hook-stdin-utf8`) y cualquier release, tag o `CHANGELOG.md`.
- `docs/**` (`docs/arquitectura.md`, `docs/specificaciones.md`, `docs/convensiones.md` para la regla ASCII): los actualiza el líder.
- Distribuir el script con el instalador o exponerlo como subcomando de `sdd.py` (no pasa a la API pública).
- Recalcular `review_fingerprint` o sellos: no dependen del nombre del documento de diseño.
- Cambiar el título interno de la plantilla («# CÓMO: diseño mínimo») o el contenido de los documentos renombrados.
- Renombrar o editar `assets/decisiones-diseno.md`: ya es ASCII y no nombra el archivo `diseño.md`.
- Prohibir archivos extra con nombre ASCII en `spec/<slug>/` o comprobar automáticamente nombres fuera de `spec/<slug>/`.
- `scripts/limpiar_arnes.py`, `src/microsdd/installer.py`, `CLAUDE.md`, `.claude/skills/sdd/SKILL.md`, `.claude/settings.json`: comprobado que no nombran `diseño.md`.
