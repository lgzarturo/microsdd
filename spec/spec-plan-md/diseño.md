# CÓMO: diseño mínimo

## Situación comprobada
- `.microharness/sdd.py`:
  - Línea 17: `TASK_FILES = ('spec.json', 'requerimientos.md', 'diseño.md', 'tareas.md')`; `validate` la recorre para exigir los cuatro archivos (`Falta spec/<slug>/<nombre>`).
  - Línea 92 (`new`): escribe `diseño.md` con el título «# CÓMO: diseño mínimo».
  - Líneas 108-116 (`spec_fingerprint`): SHA-256 de `spec.json` canónico (sin `state`) seguido, por cada documento, de `nombre + b'\x00'` y su contenido con CRLF→LF. **El nombre `diseño.md` forma parte de la huella**: al renombrar, cambia la huella de las 15 tareas y sus aprobaciones `spec` darían «Especificación alterada después de aprobación».
  - Líneas 191 y 198 (`validate`): lee `diseño.md` y lo nombra en el error de marcadores de plantilla.
  - `review_fingerprint` (`code_fingerprint`) depende del diff de código, no del documento de diseño, y solo se compara en `approve close` de una tarea en `proceso`. `sealed_tests` solo se comparan mientras la tarea no está `terminado`. Ninguno de los dos requiere migración.
  - `validate` omite en la comprobación de alcance todo lo que empieza por `spec/`, `docs/`, `.microharness/` y `CLAUDE.md`: los renombrados en `spec/` no requieren `spec/**` en `allowed_paths`.
  - `approve ... spec` rechaza tareas `terminado` («La tarea terminó»): una tarea terminada no puede reaprobarse; por eso hace falta recalcular su huella.
- `.claude/hooks/pretool.py` línea 27: regex del autor `spec/[a-z][a-z0-9-]*/(spec\.json|requerimientos\.md|diseño\.md|tareas\.md)`. El implementador tiene denegado `.claude/`, `.microharness/`, `docs/` y `spec/`; el líder solo puede editar `docs/`, `spec/` y `memory.json` (sin restricción de Bash).
- `.claude/agents/autor.md` línea 12, `README.md` líneas 126 y 217 y `assets/proceso-versionado.md` línea 23 (API-04) nombran `diseño.md`. `assets/decisiones-diseno.md` solo usa «diseño» en prosa. `CLAUDE.md`, `.claude/skills/sdd/SKILL.md`, `scripts/limpiar_arnes.py` y `src/microsdd/installer.py` no lo nombran.
- `scripts/` no está en `MANIFEST` de `src/microsdd/installer.py` ni en API-01..API-08 de `assets/proceso-versionado.md`: no se instala ni es API pública. Precedente: `scripts/limpiar_arnes.py`, probado en `tests/test_limpiar_arnes.py` cargándolo con `importlib`.
- Pruebas que nombran `diseño.md`: `tests/test_sdd.py` líneas 40, 64-66, 72 (filtro `fix-sesiones/dise`), 100, 185-195, 221-223, 313, 661-667; `tests/test_limpiar_arnes.py` líneas 33 y 132.
- `git -c core.quotePath=false ls-files`: los únicos nombres no ASCII versionados son los 14 `spec/*/diseño.md` (más el de `spec-plan-md`, aún sin versionar).
- Línea base: `check <slug>` OK en las 14 tareas `terminado`.

## Decisión y justificación
1. **Controlador** (`.microharness/sdd.py`, PRE-02): `TASK_FILES` con `plan.md`; `new` escribe `plan.md` (se mantiene el título de plantilla, que es contenido); `spec_fingerprint` recorre `('requerimientos.md', 'plan.md', 'tareas.md')` y usa ese nombre en el hash (sin etiqueta histórica, decisión Q-01); `validate` lee `plan.md` y lo nombra en el error de marcadores.
2. **Regla ASCII mínima**: en `validate`, junto al bucle de archivos obligatorios, un error por cada entrada de `spec/<slug>/` con `not entry.name.isascii()`: `Nombre de archivo no ASCII en spec/<slug>/: <nombre>`. Se reporta junto con los archivos que faltan (un `diseño.md` sobrante produce ambos errores, lo que guía la migración). No se comprueban nombres fuera de `spec/<slug>/`: hoy ninguno es no ASCII y la regla queda documentada.
3. **Hook**: `diseño\.md` → `plan\.md` en la regex del autor.
4. **Script de migración `scripts/migrar_plan_md.py`** (lo escribe el implementador; lo ejecuta el líder).
   - Ubicación: `scripts/` porque no se instala ni forma parte de la API pública (no es subcomando de `sdd.py`), sigue el precedente de `limpiar_arnes.py` y puede borrarse cuando ya no haga falta (p. ej. con la limpieza de v1.0.0) sin cambio de versión.
   - Uso: `python scripts/migrar_plan_md.py <raíz>`; `<raíz>` es la raíz del repositorio con el arnés (permite migrar un repositorio instalado desde una copia de MicroSDD, nota de README).
   - Autónomo: implementa en una función `huella(path, spec, nombre)` el cálculo de `spec_fingerprint` con el nombre del documento de diseño como parámetro, leyendo siempre `plan.md`; esquema antiguo = `huella(..., 'diseño.md')`, nuevo = `huella(..., 'plan.md')`. No importa el `sdd.py` del destino, cuya versión puede ser antigua. La duplicación (unas 8 líneas) es aceptable en un script puntual; AC-07 comprueba que el esquema nuevo coincide con `sdd.spec_fingerprint` y que el antiguo coincide con una constante del código de `61bd1ee`.
   - Fase 1, solo lectura: aborta (código 1, nombra la tarea, sin escribir) si algún `spec/*/` contiene `diseño.md`; para cada tarea de `memory.json` con `approvals.spec` no nulo: carga `spec/<slug>/spec.json`; si falta `plan.md`, aborta; si la huella almacenada es igual a la nueva, la omite (idempotencia); si es igual a la antigua, la anota para migrar; si no coincide con ninguna, aborta (no «lava» specs alteradas).
   - Fase 2, solo si la fase 1 terminó sin errores y hay algo que migrar: por cada tarea anotada, `approvals.spec.fingerprint = nueva` y añade a `events` `{'at': <UTC ISO>, 'event': 'migración_plan_md', 'old': <antigua>, 'new': <nueva>}`; escribe `memory.json` una sola vez con el mismo formato que `sdd.dump` (`ensure_ascii=False`, `indent=2`, salto final). Imprime una línea por tarea migrada y un resumen. Sin nada que migrar: código 0 y no escribe.
   - No toca `by`, `evidence`, `at`, `close`, `review`, `review_fingerprint`, `sealed_tests`, `iterations` ni `spec.json`. No ejecuta git ni renombra archivos.
5. **Orden en el repositorio real**: (a) cambio de `sdd.py`; (b) el líder renombra las 15 tareas (`git mv` en las 14 versionadas; `mv` en `spec-plan-md` si aún no está versionada); (c) el líder ejecuta `sh .microharness/python.sh scripts/migrar_plan_md.py .`; (d) verificación AC-10. El script va después del renombrado porque exige `plan.md` y rechaza `diseño.md`, lo que evita un estado mixto; el esquema antiguo sobre el contenido de `plan.md` es equivalente al cálculo previo porque el contenido no cambia. Entre (a) y (c), `check` informa «alterada» en todas las tareas (transitorio esperado). La propia `spec-plan-md`, aprobada sobre `diseño.md`, se migra igual y conserva su aprobación.
6. **Documentación**: `autor.md` punto 3; `README.md` líneas 126 y 217, la regla «nombres de archivo solo ASCII» junto al árbol de `spec/<slug>/` y una nota breve de migración para repositorios instalados: actualizar el arnés, renombrar `spec/<slug>/diseño.md` a `plan.md` y ejecutar `python <copia de MicroSDD>/scripts/migrar_plan_md.py <raíz>`; como alternativa, reaprobar con `approve <slug> spec` las tareas no terminadas (las terminadas no admiten reaprobación). API-04 de `assets/proceso-versionado.md` con `plan.md`. La convención en `docs/convensiones.md` y el índice en `docs/` los actualiza el líder.
7. **Pruebas** (`tests/test_sdd.py` y `tests/test_migrar_plan_md.py` protegidos, requieren sellado humano; `tests/test_limpiar_arnes.py`):
   - Adaptar a `plan.md` en `tests/test_sdd.py`: `setUp` (l. 40), `test_diff_files_non_ascii_paths` (`spec/x/plan.md`; la ruta no ASCII sigue cubierta por `src/módulo.py`), `test_scope_ignores_uncommitted_task_design` (filtro `fix-sesiones/`), `test_spec_approval_and_fingerprint`, `test_spec_fingerprint_ignores_crlf_conversion` (tupla y comentario), `test_diff_files_returns_literal_non_ascii_paths` (sigue cubierto por `fuera/configuración.txt`), `test_reviewer_git_allowlist` (`git diff -- spec/x/plan.md`), `test_allows_changes_in_spec_and_memory` (l. 661/667; `notas-año.md` se conserva porque prueba `release propose`, no `check`).
   - Nuevas en `tests/test_sdd.py`: AC-01, AC-02, AC-03 y AC-06.
   - Nuevo `tests/test_migrar_plan_md.py` (carga el script con `importlib`, como `test_limpiar_arnes.py`, y apunta `sdd.ROOT`/`sdd.MEMORY` a un directorio temporal): AC-07 (migración correcta y evento), AC-08 (a, b, c: aborta sin escribir) y AC-09 (segunda ejecución sin cambios).
   - Constante de AC-07: calcularla antes de cambiar `sdd.py`, con el `spec_fingerprint` de `61bd1ee` sobre el contenido fijo guardado como `diseño.md`, y anotarla en la prueba con un comentario sobre su origen.
   - `tests/test_limpiar_arnes.py`: `task()` y la aserción de la l. 132 pasan a `plan.md` (no está sellado).

## Alternativas descartadas
- **Etiqueta histórica `diseño.md` fija en `spec_fingerprint`** (propuesta inicial): no tocaba `memory.json`, pero dejaba un literal no ASCII y heredado para siempre en el código. Descartada por decisión humana Q-01.
- **Subcomando `sdd.py migrate`**: lo convertiría en API pública permanente (API-01) y se instalaría en todos los destinos.
- **Que el script renombre los archivos**: mezclaría escritura de `spec/` y de memoria y perdería el `git mv` explícito; el renombrado queda como paso separado del líder.
- **Script en el scratchpad o sin pruebas**: no sería auditable ni reutilizable por repositorios instalados.
- **Importar el `sdd.py` del destino**: si el destino no está actualizado, el esquema «nuevo» saldría igual al antiguo.
- **Comprobar nombres ASCII en todo el repositorio**, **prohibir archivos extra ASCII en `spec/<slug>/`**, **cambiar el título de la plantilla**: no solicitados (YAGNI, diff mínimo).

## Invariantes y riesgos
- Invariante: ninguna huella cambia sin que su valor anterior coincida con el esquema antiguo sobre el contenido actual; cada cambio deja un evento `migración_plan_md` con `old` y `new`.
- Invariante: fallo en cualquier tarea ⇒ cero escrituras (fase 1 completa antes de escribir).
- Invariante: `by`, `evidence`, `at`, `close`, `review_fingerprint` y sellos no cambian (AC-07, AC-10).
- Riesgo: entre el cambio de `sdd.py` y la ejecución del script, `check` falla en todas las tareas; mitigación: pasos (b) y (c) inmediatamente después de (a).
- Riesgo: con cambios sin commit fuera de su alcance, `check <slug>` de tareas terminadas falla por scope (comportamiento existente); por eso AC-10 usa `--no-scope`. Tras el commit, `check` sin opciones debe volver a dar OK.
- Riesgo: la guardia deniega al implementador `.claude/` y `.microharness/`; ver PRE-02.
- Riesgo: si una tarea fue alterada después de su aprobación, el script aborta y bloquea la migración entera; es el comportamiento deseado y requiere decisión humana (reaprobar o restaurar).
- Efecto secundario (API pública): cambia API-04 de forma incompatible; los repositorios instalados deben renombrar y migrar (nota de README). Commit con `!` (decisión Q-03; en fase 0.y.z incrementa MINOR).
- Efecto secundario: `code_fingerprint`/`review_fingerprint` de esta tarea no cubren `spec/` ni `memory.json`; el revisor verifica renombrados y eventos con `git status`, `git diff` y AC-10.
- `docs/arquitectura.md` y `docs/specificaciones.md` (línea 3) quedan desactualizados hasta que el líder los edite.

## Preguntas abiertas para el líder
- Q-04 (no bloqueante): ¿se borra `scripts/migrar_plan_md.py` en la limpieza de v1.0.0 o se conserva para repositorios instalados rezagados? Esta spec no programa su eliminación.
