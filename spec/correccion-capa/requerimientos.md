# QUÉ: requisitos

## Objetivo
Empujar las clases de error repetidas del arnés a compuertas deterministas: recibo de `check --run` antes de `review APROBADO`, señal de pases reales, rechazo de encogimiento del núcleo, tope RDD no negociable en prosa, rechazo de mezcla versión/función, docs sin placeholder, y un router de solo lectura (`correct` / `corrections`). Sin TLA+, Lean, capturas, generador de lint ni bump de `__version__`.

## Definiciones
- **Pases reales:** para un resumen unittest, el último `Ran N tests` menos `skipped` y `expected failures` del último `OK (...)`. Sin línea `OK`, los pases unittest son 0. Otros runners conservan su patrón actual de `tests_ran` (pytest `passed`, bun `pass`, etc.).
- **Recibo de verificación:** `tasks.<slug>.verification = {fingerprint, at}` escrito solo por un `check --run` exitoso (salida 0 y pases reales ≥ `min_tests`), con `fingerprint = code_fingerprint(allowed_paths)` y evento `verificación`.
- **Encogimiento del núcleo:** en el diff contra `HEAD`, para `.microharness/sdd.py` o `.claude/hooks/pretool.py`, `eliminadas − añadidas > 100` (líneas netas quitadas).
- **Nota rewrite-core:** `note --fact … --evidence '<cita>' --for-task <slug> --for-phase rewrite-core` cuyo `fact` o `evidence` nombra la ruta del archivo núcleo afectado; mismas reglas de `consume_note` (sin usar, misma tarea, misma fase, ≤ 30 min).
- **Rutas de release:** `CHANGELOG.md`, `historial/**`, `pyproject.toml`, `assets/proceso-versionado.md`.
- **Placeholder de docs:** cuerpo que, tras quitar el título `# …`, es solo `Pendiente de inspección.`

## Precondiciones
- Rama de trabajo sobre `main` con `.microharness/sdd.py` en versión 1.5.3.
- Suite en verde: 501 pruebas, 8 omitidas, con `sh .microharness/python.sh -m unittest discover -s tests`.
- El humano confirma este contrato al autorizar la implementación (esta tarea se ejecuta bajo el plan aprobado «Capa de corrección»).

## Requisitos EARS

### Recibo y señal
- REQ-01: WHEN `check --run` termina sin errores en una tarea no `terminado`, THE sistema SHALL escribir `tasks.<slug>.verification` con `fingerprint` igual a `code_fingerprint` del alcance y `at` de `now()`, y SHALL añadir un evento `verificación`.
- REQ-02: WHEN `review` recibe `APROBADO`, THE sistema SHALL exigir un recibo cuya `fingerprint` coincida con la huella actual; IF falta o no coincide, THEN SHALL fallar con `ERROR:`/`ValueError` nombrando la verificación, sin modificar la memoria. `RECHAZADO` no exige recibo.
- REQ-03: THE campo `verification` SHALL figurar en `INTEGRITY_FIELDS` justificado solo por el evento `verificación` (y, al reiniciar, por `aprobación_spec`). WHEN `approve spec`, THE sistema SHALL poner `verification` en `null`.
- REQ-04: WHEN `check --run` cuenta pruebas unittest, THE sistema SHALL usar pases reales (REQ definición). `evaluate_fixture` en `bench.py` SHALL llamar a la misma función de `sdd.py` (sin duplicar la resta de omitidos).

### Encogimiento, RDD y versión
- REQ-05: WHEN `check` (con alcance) ve encogimiento del núcleo > 100 líneas netas quitadas y no hay nota `rewrite-core` consumible que nombre ese archivo, THE sistema SHALL fallar nombrando archivo y delta. IF hay nota válida, THEN SHALL consumirla y no fallar por ese archivo.
- REQ-06: WHEN la tarea no está `terminado` y el alcance está activo, THE sistema SHALL sumar líneas añadidas del diff de alcance (`git diff --numstat` + archivos nuevos) y, IF el total supera `rdd_max_lines` de `config()`, THEN SHALL fallar. Una `decision` en `memory.json` no altera el resultado.
- REQ-07: IF la línea `__version__` de `.microharness/sdd.py` cambia respecto a `HEAD` y el mismo diff toca una ruta fuera de las rutas de release, THEN `check` SHALL fallar. Un diff solo de rutas de release + versión pasa.

### Docs y router
- REQ-08: WHEN cualquiera de `docs/AGENT.md`, `docs/arquitectura.md`, `docs/convenciones.md`, `docs/especificaciones.md` es solo placeholder, THEN `check` SHALL fallar nombrando el archivo. `ensure_init` SHALL dejar de plantar ese placeholder y escribir una tabla mínima `regla | capa | función`.
- REQ-09: THE CLI SHALL ofrecer `correct` (clasifica un mensaje de error o, sin argumento, el último fallo conceptual) y `corrections --since <rev>` (tasa de restauración en el historial git). Ambos son de solo lectura, entran en `SDD_ALLOWED`, no en `GATED_SUBCOMMANDS`, y documentan API-01. API-03 menciona `verification` y el evento `verificación`. `NOTE_PHASES` incluye `rewrite-core`.
- REQ-10: WHEN `correct` no reconoce la clase, THE capa SHALL ser `humano` y no propondrá prosa para AGENTS.md. Capas admitidas: `arquitectura`, `estatico`, `verificacion`, `humano`.

## Criterios de aceptación

- AC-01 (REQ-01, REQ-02): en raíz temporal con tarea en `proceso`, `review APROBADO` sin recibo falla; tras `check --run` OK, `review APROBADO` pasa; si se cambia un archivo de alcance tras el recibo, vuelve a fallar.
- AC-02 (REQ-02): `review RECHAZADO` sin recibo termina con éxito (mientras queden iteraciones).
- AC-03 (REQ-03): alterar solo `verification` sin evento `verificación` produce error de integridad; `approve spec` deja `verification` en `null`.
- AC-04 (REQ-04): `tests_ran('Ran 1 test in 0.0s\nOK (skipped=1)\n') == 0`; `tests_ran('Ran 0 tests in 0.0s\nOK\n') == 0`; `tests_ran('Ran 2 tests in 0.0s\nOK\n') == 2`; `evaluate_fixture` usa esa función (mismo resultado en el caso skipped).
- AC-05 (REQ-05): diff sintético que quita 770 líneas de `sdd.py` falla el check; un `fix` de −10 líneas pasa; con nota `rewrite-core` válida que nombra `.microharness/sdd.py`, el de 770 pasa y la nota queda consumida.
- AC-06 (REQ-06): con `rdd_max_lines=50` y 60 líneas añadidas en alcance, `check` falla; una `decision` que «acepta» el exceso no limpia el error.
- AC-07 (REQ-07): cambiar `__version__` y un archivo de función (p. ej. `tests/test_x.py`) falla; cambiar `__version__` solo con `CHANGELOG.md` pasa.
- AC-08 (REQ-08): docs solo con «Pendiente de inspección.» hacen fallar `check`; tras la tabla, pasan; `ensure_init` en destino vacío no escribe ese placeholder.
- AC-09 (REQ-09, REQ-10): `correct` con un error de recibo imprime JSON con capa `verificacion`; clase desconocida → capa `humano`; `corrections --since` sobre un repo fixture cuenta restauraciones; `--help` lista `correct` y `corrections`; el hook permite ambos a `lider`.
- AC-10: `python -m unittest discover -s tests` en verde; sin bump de `__version__`; `assets/proceso-versionado.md` y `assets/arnes-completo.md` actualizados; los cuatro `docs/` del repo tienen la tabla regla|capa|función.

## Fuera de alcance
- TLA+, Lean, screenshots, property-based tests, generador automático de reglas.
- Eventos nuevos en `harness-telemetry.v1.json`.
- Partir `sdd.py` en módulos; reactivar CI en push/PR; `symbol-map`.
- Bump de versión o carpeta `historial/` nueva.
