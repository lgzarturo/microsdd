# CÓMO

## Enfoque
Extender `.microharness/sdd.py` con helpers deterministas y engancharlos en `validate`, `review`, `approve`, `main` y `ensure_init`. `bench.py` delega el conteo de pases a `sdd.tests_ran`. El hook solo añade dos tokens de lectura a `SDD_ALLOWED`. Los cuatro `docs/` del repo se rellenan con la tabla de reglas; no se inventan reglas sin función.

## Cambios por archivo
1. **`.microharness/sdd.py`**
   - `NOTE_PHASES += rewrite-core`; `INTEGRITY_FIELDS` + `verification` / `verificación`.
   - `tests_ran`: resta skipped/expected failures del último `OK (...)` unittest.
   - `record_verification(slug)` bajo lock; llamada tras `check --run` OK y desde `validate` cuando `run` y sin errores (tarea no terminado).
   - `review`: exige recibo si `APROBADO`.
   - `approve(spec)`: `verification = None`.
   - `core_shrink_errors`, `rdd_diff_line_errors`, `version_mix_errors`, `docs_placeholder_errors` → `validate` (con alcance / no terminado según REQ).
   - CLI `correct` / `corrections --since`; tabla fija de rutas de corrección.
   - `ensure_init`: plantilla de tabla, no placeholder.

2. **`.microharness/bench.py`**: `evaluate_fixture` importa/usa `tests_ran` de `sdd` (o carga del módulo hermano) para el conteo de pases.

3. **`.claude/hooks/pretool.py`**: `SDD_ALLOWED` incluye `correct`, `corrections`.

4. **`tests/test_correccion_capa.py`**: AC-01…AC-09 con diffs sintéticos y repo git fixture. Actualizar helpers de `review APROBADO` en tests existentes para escribir recibo.

5. **`docs/*.md`**: tabla regla | capa | función. **`assets/proceso-versionado.md`**: API-01/API-03. **`assets/arnes-completo.md`**: recibo, pases reales, `correct`/`corrections`, `rewrite-core`.

## Alternativas descartadas
- Partir `sdd.py`: mismo gesto que el monolito recortado; la compuerta va primero.
- Telemetría nueva: esquema compartido con `additionalProperties: false`.
- Generar lint desde historial: escribe reglas no ejecutadas.

## Riesgos
- Muchos tests llaman `review APROBADO` sin `check --run`: se añade helper `stamp_verification` en esos módulos.
- `tests_ran` cambia semántica unittest: actualizar `TestsRanTests` y alinear bench.
