# CÓMO: diseño mínimo

## Situación comprobada
- `.microharness/bench.py`:
  - `check_openrouter_free_lock` (L143) compara `remaining` con un `n_total` que hoy se cuenta en celdas.
  - `ClaudeCodeProvider` (L398-568) no limita turnos y fija `calls`/`iterations` en 1.
  - `run_bench` (L581-707) relee la cuota solo entre tareas y corta con `remaining < 1`.
  - `cmd_bench` (L1007) repite el candado con `n * 5 * 2`.
- `.github/workflows/bench-baseline.yml`: el candado smoke (L61) usa `1` y el de pre-corrida (L218) usa `3 * 5 * 2`. El smoke `claude -p` (L76-80) no tiene `--max-turns`.
- `bench/config.json`: no tiene claves de presupuesto de solicitudes.
- `tests/test_bench.py`: las pruebas del candado pasan `n_total=10` con `remaining=100`. Dos pruebas de `run_bench` real usan `load_config()` + cheap (30 celdas) con `remaining=100`. Con 6 turnos (180 > 100) abortarían, así que hay que fijar su `cfg` (ver riesgos).
- `.claude/hooks/pretool.py`: `HARNESS_EDITABLE` (L26-31) no incluye `bench.py` ni `metrics.py`. La excepción de L725-727 exige `agent == 'implementador'`, `rel in HARNESS_EDITABLE` y la grafía exacta. Después aplica el alcance y la aprobación de la spec activa. L734 impide al implementador editar `.claude/`.
- La evidencia de `bench/baseline/bench-report.sanitized.json` es de 30 celdas: 14 `pending` y un máximo de ~986k tokens en una celda.

## Decisión y justificación
0. **Hook (decisión humana explícita, vía líder)**:
   - Se añaden `'.microharness/bench.py'` y `'.microharness/metrics.py'` a `HARNESS_EDITABLE` y no se toca nada más del hook.
   - Lo aplica el **líder**, no el implementador (L734), y queda registrado como decisión antes de T01.
   - La lógica existente (grafía exacta, alcance y aprobación) cubre REQ-11 sin código nuevo.
   - `metrics.py` solo se lista; esta tarea no lo edita.
   - Las pruebas de AC-14 las escribe el implementador después del cambio del líder, así que no hay fase RED observable para él. Se documenta y no se finge.
1. **Un solo helper de configuración/estimación** en `bench.py`:
   - `request_budget(cfg) -> tuple[int, int]` valida `maxTurnsPerCell` y `maxRequestsPerRun` (`type(x) is int and x >= 1`; si no, `BenchError`) y devuelve `(max_turns, max_requests)`.
   - `planned_requests(cfg, cells) -> int` calcula `cells × max_turns` y lanza `BenchError` si supera `max_requests`.
   - Lo usan `run_bench`, `cmd_bench` y los dos pasos del workflow (DRY: una sola fórmula).
2. **Candado existente sin cambio de firma**: `check_openrouter_free_lock(api_key, n_total, ...)` sigue igual. Solo cambia lo que pasan los llamadores (la estimación por turnos) y el docstring ("solicitudes estimadas"). Así las pruebas del candado no cambian.
3. **`ClaudeCodeProvider(model_id, *, claude_bin='claude', max_turns=DEFAULT_CONFIG['maxTurnsPerCell'])`**:
   - Añade `'--max-turns', str(self.max_turns)` al comando.
   - Lee `num_turns` (`type(v) is int and v >= 0`) y lo pone en `calls`/`iterations`; si no, `None`.
   - `subtype == 'error_max_turns'` no entra en la rama `pending` (cuenta como celda completada y la prueba del fixture decide `ok`/`fail`).
   - `cmd_bench` pasa `max_turns` desde la config.
4. **`run_bench`**:
   - Llama a `request_budget(cfg)` siempre (también con fake, para fallar cerrado ante config inválida).
   - En modo real calcula `estimated = planned_requests(cfg, len(schedule))` antes de `check_openrouter_free_lock(api_key, estimated, ...)` y guarda `remaining` inicial.
   - Antes de cada celda: si `min(max_requests - used, remaining) < max_turns`, marca la celda y todas las restantes como `pending`.
   - Después de cada celda real: `fetch_openrouter_key` → `assert_usage_unchanged(..., data=...)` → `remaining` fail-closed (falta `free_model_daily_requests` o `remaining` inválido → `BenchError`) → `used += max(prev - new, turns)` con `turns = calls if type(calls) is int else max_turns`.
   - Sustituye el bloque "candado entre tareas" (L637-659): la relectura por celda lo cubre.
   - Extrae `_pending_cell(task, variant, rep, model_id)` para las tres copias del dict pendiente (DRY, mismo contenido).
   - Añade al reporte `requestsUsed` (`None` con fake), `requestBudget`, `requestsEstimated` y `maxTurnsPerCell`, más un riesgo nuevo en `risks`.
5. **`format_report_md`**: una línea `- requests: {requestsUsed}/{requestBudget}`. `sanitize_report` no cambia (las claves de nivel superior no están en `forbidden`), pero se verifica con una prueba.
6. **Workflow**:
   - Candado smoke: `cfg = b.load_config(); est = b.planned_requests(cfg, 1)`. Exporta `BENCH_MAX_TURNS` a `$GITHUB_ENV`. El smoke `claude -p` añade `--max-turns "${BENCH_MAX_TURNS}"`.
   - Pre-corrida: `est = b.planned_requests(cfg, int(cfg['nCheap']) * 5 * 2)`.
7. **Throttle**: `MIN_INTERVAL_S` se mantiene; su comentario pasa a decir "pausa entre celdas; no controla el ritmo interno de Claude Code". No se promete cumplir 20 req/min.
8. **Config**: `bench/config.json` y `DEFAULT_CONFIG` reciben `maxTurnsPerCell: 6` y `maxRequestsPerRun: 200` (decisión humana), más una nota breve en `notes`. Con estos valores, la cheap estima 30 × 6 = 180 ≤ 200. La completa estima 50 × 6 = 300 > 200 y aborta antes de empezar (hecho aceptado, no bloqueante).

## Alternativas descartadas
- **Reserva porcentual (`requestReservePct`)**: YAGNI, y el humano pidió no añadir margen. El corte "falta una celda completa" ya reserva `maxTurnsPerCell`.
- **Throttle por solicitud o proxy local que cuente HTTP**: añade una capa nueva y no controla los reintentos de Claude Code. Fuera de proporción.
- **Contar solo con `num_turns`**: no ve las llamadas de fondo ni los reintentos. **Contar solo con el delta de `remaining`**: puede llegar con retraso. Se usa `max(delta, turnos)`, que es conservador.
- **Cambiar la firma de `check_openrouter_free_lock`**: rompería pruebas existentes sin aportar nada.
- **Cambiar `ANTHROPIC_DEFAULT_HAIKU_MODEL`**: no está verificado cuánto consume. Se documenta como riesgo.

## Invariantes y riesgos
- **Invariantes**:
  - El modo fake no hace red y produce el mismo veredicto que antes con la config por defecto.
  - Fail-closed ante config o `/api/v1/key` inválidos.
  - Nunca se inventa `calls = 1`.
  - Las celdas `pending` no entran en la estadística (sin cambios en `aggregate_report`).
- **Riesgo**: la superficie editable del implementador crece con dos archivos de `.microharness/`. Lo mitigan las condiciones que ya aplica el hook: `allowed_paths` de la spec activa, aprobación y grafía exacta. `memory.json`, `config.json`, `memory.lock` y el resto de `.microharness/` siguen denegados (AC-14).
- **Riesgo**: con un tope de 6 turnos, una celda que necesite más termina en `error_max_turns` y cuenta como `fail` (REQ-07). Esto puede bajar la tasa de éxito medida en ambas variantes.
- **Riesgo**: `iterations` pasa de 1 constante a `num_turns`. Cambian los datos que recibe la mediana de iteraciones (no la fórmula). El veredicto `efficiency` por iteraciones puede variar en corridas reales futuras.
- **Riesgo (no verificado)**: el comportamiento exacto de `--max-turns` y de `error_max_turns`/`is_error` en Claude Code 2.1.197. Si `num_turns` no aparece, se cuenta el tope (conservador).
- **Riesgo**: los reintentos internos de Claude Code ante 429 y las llamadas de fondo pueden superar `maxTurnsPerCell` en una celda. El delta de `remaining` lo detecta después, pero no lo evita.
- **Riesgo**: una relectura de `/api/v1/key` por celda añade ~30 GET por corrida cheap. Se asume que no cuentan en la cuota de modelos `:free` (no verificado).
- **Efecto secundario**: `remaining` ausente tras una celda pasa de tolerado a `BenchError` (coherente con §3.6 del candado inicial).
- **Efecto secundario**: dos pruebas existentes necesitan fijar `maxTurnsPerCell=1`/`maxRequestsPerRun=30` en su `cfg`. Solo se toca la preparación, no las aserciones.
