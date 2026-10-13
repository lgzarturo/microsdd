# CÓMO: diseño mínimo

## Situación comprobada
- `.microharness/sdd.py` (430 líneas) define subcomandos en `main()` con `argparse` y despacha con `if/elif`; los errores de dominio se lanzan como `ValueError` y `main()` los convierte en `ERROR: ...` + código 1. `argparse` termina con código 2 ante errores de uso.
- Utilidades existentes reutilizables: `ensure_init()` (crea `docs/`, `spec/`, los cuatro docs si faltan y `memory.json` con `{'schema_version': 1, 'project': {'observations': [], 'decisions': []}, 'tasks': {}}` si no existe; imprime «Contexto inicializado...»), `load()`, `dump()` (JSON UTF-8, `indent=2`, `ensure_ascii=False`, salto final) y `now()`.
- `approve()` y `review()` validan textos con `.strip()` antes de escribir; `note` seguirá ese patrón.
- `tests/test_sdd.py` redirige `sdd.ROOT` y `sdd.MEMORY` a un directorio temporal en `MicroSDDTests.setUp` (que ya ejecuta `sdd.new`, por lo que `memory.json` existe con una tarea) y `ReleaseProposeTests.run_main()` muestra el patrón para invocar `sdd.main()` con `sys.argv` parcheado y capturar stdout/stderr y código.
- `validate()` excluye `.microharness/` del control de alcance por diff, pero `code_fingerprint()` sí usa `allowed_paths`: por eso `.microharness/sdd.py` debe figurar en el alcance para que la huella de revisión cubra el cambio.
- `README.md` no tiene una sección titulada «comandos del CLI»; los comandos se muestran en la sección 5 «Ciclo operativo por tarea» (bloque `bash`).

## Decisión y justificación
1. Nueva función `note(fact, decision, by, evidence)` en `sdd.py`, junto a `approve`/`review`:
   - Validación completa **antes** de tocar disco: exactamente uno de `fact`/`decision` (no `None`); textos presentes no vacíos tras `.strip()`; `by` obligatorio y no vacío con `decision`; `by` prohibido con `fact`. Cada fallo lanza `ValueError` con mensaje en español.
   - Luego `ensure_init()` si `MEMORY` no existe (evita su salida «Contexto inicializado» cuando no hace falta y no crea `docs/`/`spec/` en el caso normal), `memory = load(MEMORY)`, `project = memory.setdefault('project', {})`, `project.setdefault('observations' | 'decisions', [])`, `append` del objeto con las claves en el orden de las entradas existentes y `dump(MEMORY, memory)`.
   - Imprime una confirmación que indique que es una declaración registrada, no autenticada.
2. En `main()`: `no = sub.add_parser('note')` con `--fact`, `--decision`, `--by` (opcionales, por defecto `None`) y `--evidence` (`required=True`, igual que en `approve`/`review`); rama `elif args.command == 'note': note(...)`.
   - La exclusión mutua se valida en `note()` y no con `add_mutually_exclusive_group`, para que el error devuelva código 1 (contrato pedido) y no 2.
   - La ausencia total de `--evidence` es error de uso de `argparse` (código 2), coherente con los demás subcomandos; `--evidence ""` o solo espacios da código 1.
3. JSON inválido: `load()` lanza `json.JSONDecodeError`, ya capturado por `main()` → código 1 sin escribir. No requiere código nuevo, solo prueba.
4. README, sección 5: dos ejemplos (`--fact`, `--decision`) y una frase: registrar una decisión es una declaración, no autenticación; el líder la usa en lugar de editar `memory.json` a mano.

## Alternativas descartadas
- Grupo mutuamente excluyente de `argparse`: devuelve código 2, contradice el contrato de código 1.
- Subcomandos separados (`note fact` / `note decision`): más superficie sin beneficio.
- Llamar siempre a `ensure_init()`: imprime un mensaje engañoso y crea `docs/`/`spec/` como efecto lateral en cada nota.
- Escritura atómica/lock y validación de esquema de `memory.json`: fuera de alcance (YAGNI).

## Invariantes y riesgos
- Invariante: con entrada inválida no se escribe ningún archivo (validación antes de `ensure_init`/`dump`).
- Invariante: `note` solo modifica `project.observations` o `project.decisions` (append); `tasks` y demás claves se reescriben con los mismos datos. `dump()` re-serializa todo el archivo: si el `memory.json` actual no tiene exactamente el formato de `dump`, el diff textual puede mostrar cambios de formato sin cambio de datos (riesgo bajo: el archivo ya se escribe con `dump`).
- Riesgo de proceso (bloqueante para implementar): `.claude/hooks/pretool.py` niega al implementador `Write/Edit` sobre `.microharness/`; el implementador no podrá editar `sdd.py` con esas herramientas. El líder debe resolver cómo se aplica el cambio (precedente: `herramienta-release` modificó `sdd.py`). Esta spec no cambia el hook.
- Riesgo: `--by` es texto libre; cualquiera puede declarar «Programador». Se documenta como declaración, no autenticación.
- Riesgo: sin lock, dos `note` simultáneos pueden perder una entrada (fuera de alcance).
- Efecto lateral aceptado: si `memory.json` no existe, `ensure_init()` también crea `docs/` y `spec/` con plantillas, igual que `new`.
- `memory.json` no debe entrar en `scope.allowed_paths`: las notas del líder posteriores a la revisión cambiarían la huella y bloquearían el cierre.
