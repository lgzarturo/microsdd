# QUÉ: requisitos

## Objetivo
Que la corrida real del bench (OpenRouter `:free` + Claude Code) mida y limite **solicitudes HTTP al modelo** (turnos agénticos), no celdas. Hoy el candado asume 1 solicitud por celda, Claude Code corre sin tope de turnos y la cuota solo se relee al cambiar de tarea. La cuota diaria se agotó en una corrida cheap: 16 celdas válidas, 14 `pending` con `exitCode: null` y una celda de ~986k tokens en `bench/baseline/bench-report.sanitized.json`.

## Hechos comprobados (código en la rama actual, sobre el PR #15)
- `check_openrouter_free_lock(api_key, n_total)` compara `free_model_daily_requests.remaining` con `n_total`. `run_bench` (L601) y `cmd_bench` (L1007) pasan `n * len(tasks) * 2` (30 en cheap). El workflow pasa `1` (smoke, L61) y `3 * 5 * 2` (pre-corrida, L218).
- `ClaudeCodeProvider.run_cell` (L474-480) no pasa `--max-turns`; solo usa `CELL_TIMEOUT_S = 900`.
- `MIN_INTERVAL_S = 3.1` espera solo entre celdas.
- `run_bench` (L637-659) relee `/api/v1/key` solo al cambiar de tarea y corta solo si `remaining < 1`.
- `calls: 1` e `iterations: 1` están fijos (L553-555). `num_turns` del JSON de Claude Code se descarta.
- `assert_usage_unchanged` protege dólares. En `:free`, `usage` no sube, así que no protege solicitudes.
- `.claude/hooks/pretool.py`: `HARNESS_EDITABLE` (L26-31) solo contiene `sdd.py` y los tres lanzadores, así que el hook deniega al implementador editar `.microharness/bench.py` (L725-729). El implementador tampoco puede editar `.claude/` (L734). El humano autorizó, vía el líder, añadir `.microharness/bench.py` y `.microharness/metrics.py` a `HARNESS_EDITABLE`.

## Supuestos (no verificados)
- Cada turno de `claude -p` equivale a, como mínimo, 1 solicitud a OpenRouter. Los reintentos internos de Claude Code (por ejemplo, ante un 429) y las llamadas de fondo pueden sumar solicitudes que `num_turns` no cuenta. `ANTHROPIC_DEFAULT_HAIKU_MODEL` apunta al modelo free.
- `--max-turns` existe en Claude Code 2.1.197 en modo `-p`. Al alcanzarse, el JSON trae `subtype: "error_max_turns"`; no se sabe si con `is_error: true`.
- `free_model_daily_requests.remaining` puede bajar con retraso respecto del consumo real.

## Precondiciones
- PRE-01: rama del PR #15 (bench m2) con `.microharness/bench.py`, `bench/config.json`, `.github/workflows/bench-baseline.yml` y `tests/test_bench.py` tal como están hoy.
- PRE-02: valores decididos por el humano (comunicados por el líder): `maxTurnsPerCell = 6` y `maxRequestsPerRun = 200`, sin margen ni reserva extra. Con estos valores, la corrida cheap estima 30 × 6 = 180 ≤ 200 y puede arrancar. La completa estima 50 × 6 = 300 > 200 y aborta antes de empezar (REQ-03); es un hecho aceptado, no un bloqueo.
- PRE-03: las pruebas no usan red ni la key real. Todo `/api/v1/key` y `subprocess` se simula con `mock`.

## Requisitos EARS
- REQ-01: THE bench SHALL leer `maxTurnsPerCell` y `maxRequestsPerRun` de la configuración, con valores por defecto 6 y 200 en `DEFAULT_CONFIG` y en `bench/config.json`. IF alguno no es `int` (se excluye `bool`) o es `< 1`, THEN SHALL lanzar `BenchError` antes de ejecutar ninguna celda, también con el proveedor fake.
- REQ-02: WHEN `ClaudeCodeProvider` lanza una celda, THE comando SHALL incluir `--max-turns <maxTurnsPerCell>`.
- REQ-03: WHEN se prepara una corrida real (no fake), THE bench SHALL calcular `estimación = celdas × maxTurnsPerCell`. IF `estimación > maxRequestsPerRun`, THEN SHALL abortar con `BenchError` antes de la primera celda. IF `estimación > remaining`, THEN SHALL abortar con `BenchError` antes de la primera celda (candado existente, alimentado con la estimación). Aplica tanto a `run_bench` como al candado previo de `cmd_bench`.
- REQ-04: WHEN termina cada celda de una corrida real, THE bench SHALL releer `/api/v1/key`, comprobar que `usage` no subió, leer `remaining` en modo fail-closed y sumar a `requestsUsed` las solicitudes de la celda: `max(remaining_previo − remaining_nuevo, turnos)`. `turnos` es el `calls` de la celda si es entero; si no, `maxTurnsPerCell`.
- REQ-05: WHILE quedan celdas, IF `min(maxRequestsPerRun − requestsUsed, remaining)` es menor que `maxTurnsPerCell`, THEN THE bench SHALL marcar esa celda y todas las restantes como `pending` sin ejecutarlas.
- REQ-06: WHEN el JSON de Claude Code trae `num_turns` entero `≥ 0` (se excluye `bool`), THE celda SHALL registrar `calls = iterations = num_turns`. IF falta o no es entero, THEN SHALL registrar `None` (nunca `1` inventado).
- REQ-07: WHEN el JSON de Claude Code trae `subtype == "error_max_turns"`, THE celda SHALL tratarse como completada (`ok` o `fail` según las pruebas del fixture), no como `pending`, aunque `is_error` sea `true`.
- REQ-08: THE reporte SHALL incluir `requestsUsed` (entero en corrida real; `None` con fake), `requestBudget` (`maxRequestsPerRun`), `requestsEstimated` y `maxTurnsPerCell`. El Markdown SHALL mostrar una línea `requests: <used>/<budget>`.
- REQ-09: THE workflow `bench-baseline.yml` SHALL calcular el candado smoke y el de pre-corrida con la misma estimación por turnos: `1 × maxTurnsPerCell` y `nCheap × 5 × 2 × maxTurnsPerCell`, leídos de `bench/config.json`. El smoke `claude -p` SHALL pasar `--max-turns` con el mismo valor.
- REQ-10: THE lista `risks` del reporte SHALL declarar que el ritmo interno de Claude Code (20 req/min) no está controlado y que las llamadas de fondo o los reintentos no medidos pueden consumir cuota (no verificado). El comentario de `MIN_INTERVAL_S` no SHALL afirmar que respeta 20 req/min.
- REQ-11: THE hook `.claude/hooks/pretool.py` SHALL permitir al implementador editar `.microharness/bench.py` y `.microharness/metrics.py` solo cuando estén en `allowed_paths` de la spec activa en estado `proceso`, con la spec aprobada y con la grafía exacta. THE hook SHALL seguir denegando `memory.json`, `config.json`, `memory.lock`, cualquier otro archivo de `.microharness/` y las variantes de mayúsculas. IF falta el alcance o la aprobación, THEN SHALL denegar.

## Criterios de aceptación
Las simulaciones de "corrida real" usan `skip_key_check=False`, `OPENROUTER_API_KEY` falsa, `urllib.request.urlopen` simulado y un stub de proveedor (no `FakeProvider`, que salta los candados). Los valores de `cfg` en las pruebas se fijan en memoria; no dependen de `bench/config.json`.

- AC-01: Con `maxTurnsPerCell` igual a `"8"`, `0`, `-1`, `True` o `None`, o con `maxRequestsPerRun` en esos mismos casos, `run_bench(provider=FakeProvider(...), skip_key_check=True)` lanza `BenchError`. Con los valores por defecto, la corrida fake sigue funcionando y `DEFAULT_CONFIG`/`bench/config.json` tienen 6 y 200 (REQ-01).
- AC-02: Con `subprocess.run` simulado, el `cmd` que recibe `ClaudeCodeProvider.run_cell` contiene `'--max-turns'` seguido de `str(maxTurnsPerCell)` (por ejemplo, `'5'` si se construye con 5) (REQ-02).
- AC-03: En una corrida real simulada (cheap, 30 celdas) con `cfg` fijado explícitamente a `maxTurnsPerCell = 8` y `maxRequestsPerRun = 200`, se lanza `BenchError` (240 > 200) y el stub no recibe ninguna llamada. Con los valores por defecto (6/200) y `remaining` suficiente (por ejemplo, 1000), la misma corrida cheap simulada **no** aborta por presupuesto (180 ≤ 200) y el stub recibe al menos una llamada (REQ-03).
- AC-04: En una corrida real simulada con `maxTurnsPerCell = 8`, `maxRequestsPerRun = 1000` y `remaining = 100` (< 240), se lanza `BenchError` y no se ejecuta ninguna celda (REQ-03).
- AC-05 (corte por `remaining`): stub con `calls = 4`, `maxTurnsPerCell = 4` y `maxRequestsPerRun = 1000`. `/api/v1/key` devuelve `remaining = 200` en el candado y después baja 10 por celda (200 − 10k tras la celda k). Resultado: el stub se llama exactamente 20 veces, las 10 celdas restantes son `pending` (aparecen en `pendingCells`) y `requestsUsed == 200` (REQ-04, REQ-05).
- AC-06 (corte por presupuesto de corrida): stub con `calls = 4`, `maxTurnsPerCell = 4`, `maxRequestsPerRun = 120` y `remaining` desde 1000 que baja 6 por celda. Resultado: 20 llamadas al stub, 10 `pending` y `requestsUsed == 120` (REQ-04, REQ-05).
- AC-07 (`calls` ausente cuenta el tope): `remaining` estable en 1000, stub con `calls = None`, `maxTurnsPerCell = 4` y `maxRequestsPerRun = 120`. Se ejecutan las 30 celdas y `requestsUsed == 120` (REQ-04).
- AC-08: `ClaudeCodeProvider.run_cell` con JSON `{"num_turns": 6, ...}` devuelve `calls == 6` e `iterations == 6`. Sin `num_turns`, o con `"6"` o `true`, devuelve `calls is None` e `iterations is None` (REQ-06).
- AC-09: Con JSON `subtype: "error_max_turns"`, `is_error: true` y la prueba del fixture fallida, el resultado tiene `pending is False` y `status == 'fail'` (REQ-07).
- AC-10: El reporte de una corrida real simulada contiene `requestsUsed` (int), `requestBudget`, `requestsEstimated` y `maxTurnsPerCell`. `sanitize_report` los conserva y `format_report_md` incluye `requests:` (REQ-08).
- AC-11: `bench-baseline.yml` ya no contiene `check_openrouter_free_lock(key, 1,` ni `3 * 5 * 2`. Ambos candados usan el helper de estimación con `bench/config.json` y el smoke `claude -p` incluye `--max-turns` (revisión estática con `grep`) (REQ-09).
- AC-12: `report['risks']` incluye un texto que dice que el ritmo interno de Claude Code no está controlado (REQ-10).
- AC-13: `python -m unittest tests.test_bench`, `python -m unittest tests.test_bloquear_autoaprobacion` y `python -m unittest discover -s tests` pasan. Las pruebas existentes de `check_openrouter_free_lock` pasan sin cambios. Las dos pruebas existentes de `run_bench` real (`test_run_bench_invalidates_when_usage_rises` y `test_run_bench_records_usage_before_when_stable`) solo cambian para fijar `maxTurnsPerCell`/`maxRequestsPerRun` en su `cfg`, sin tocar sus aserciones (REQ-01..REQ-11).
- AC-14: En `tests/test_bloquear_autoaprobacion.py`, siguiendo el patrón de `test_ac07_implementer_edits_only_harness_files_in_scope` / `_denied_without_scope` / `_denied_without_approval` (L208-234), hay pruebas nuevas que verifican lo siguiente. Con `.microharness/bench.py` y `.microharness/metrics.py` en el alcance y la spec aprobada, `edit('implementador', tool, path)` devuelve `None` para cada `tool` de `EDIT_TOOLS`. Para `.microharness/otro.py`, `.MicroHarness/bench.py`, `.microharness/memory.json` y `.microharness/config.json`, devuelve un mensaje de denegación. Con `bench.py` fuera del alcance (`['src/**']`) deniega, y sin aprobación (`approved=False`) también. Las pruebas existentes de AC-07 pasan sin cambios (REQ-11).

## Fuera de alcance
- Cambiar la estadística, los umbrales, el veredicto, las tareas del suite, `n`/`nCheap` o el modelo.
- Ejecutar el workflow real o usar la key real.
- Controlar el ritmo interno de solicitudes de Claude Code (20 req/min), sus reintentos o su modelo de fondo. `ANTHROPIC_DEFAULT_HAIKU_MODEL` no cambia.
- Reserva porcentual o margen extra (`requestReservePct`): descartado por decisión humana (KISS). El corte por celda completa ya basta.
- Corregir `retries: 0` y `firstTry` del proveedor real (quedan como están).
- Regenerar `bench/baseline/*` o actualizar docs generales.
- Editar `.microharness/metrics.py`: solo se añade a `HARNESS_EDITABLE` (REQ-11); esta tarea no lo modifica.
- Cualquier otro cambio en `.claude/hooks/pretool.py` aparte de las dos entradas de `HARNESS_EDITABLE`.
