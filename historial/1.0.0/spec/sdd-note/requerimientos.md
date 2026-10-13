# QUÉ: requisitos

## Objetivo
Añadir a `.microharness/sdd.py` un subcomando `note` para que el líder registre hechos (observaciones) y decisiones del proyecto en `.microharness/memory.json` sin editar el archivo a mano. Es prerrequisito de una tarea posterior (no incluida aquí) que prohibirá a los agentes escribir en `.microharness/` y ejecutar `approve`/`seal`.

Decisión humana registrada (dato de entrada, no aprobación de esta spec): «El líder registrará observaciones y decisiones mediante un nuevo subcomando `sdd.py note`; approve y seal quedan solo para el humano.»

## Hechos comprobados
- `memory.json` guarda `project.observations` como objetos `{at, fact, evidence}` y `project.decisions` como `{at, by, decision, evidence}`; dos observaciones históricas usan la clave `observation` en lugar de `fact` (no se corrigen aquí).
- `sdd.py` ya ofrece `ensure_init()` (crea `memory.json` con `project.observations`/`decisions` vacíos si falta), `dump()`, `load()` y `now()` (ISO 8601 UTC con segundos).
- `main()` convierte `ValueError`, `OSError`, `KeyError`, `TypeError` y `json.JSONDecodeError` en `ERROR: ...` por stderr y código 1; los errores de uso de `argparse` (opción obligatoria ausente, opción desconocida) terminan con código 2.
- `approve` y `review` ya rechazan `--by`/`--evidence` vacíos o solo espacios con `ValueError`.

## Precondiciones
- Python 3.10+ solo con biblioteca estándar.
- Se ejecuta desde la raíz del repositorio con `.microharness/sdd.py` presente.

## Requisitos EARS
- REQ-01: WHEN se ejecuta `sdd.py note --fact TEXTO --evidence TEXTO` con textos no vacíos, THE CLI SHALL añadir al final de `project.observations` un objeto con exactamente las claves `at`, `fact`, `evidence`, imprimir una confirmación y terminar con código 0.
- REQ-02: WHEN se ejecuta `sdd.py note --decision TEXTO --by NOMBRE --evidence TEXTO` con textos no vacíos, THE CLI SHALL añadir al final de `project.decisions` un objeto con exactamente las claves `at`, `by`, `decision`, `evidence`, imprimir una confirmación y terminar con código 0.
- REQ-03: THE campo `at` SHALL generarse con `now()` (ISO 8601 UTC, precisión de segundos); los textos se guardan tal como se recibieron.
- REQ-04: IF se indican a la vez `--fact` y `--decision`, o ninguno de los dos, THEN THE CLI SHALL imprimir `ERROR:` por stderr, terminar con código 1 y no escribir ningún archivo.
- REQ-05: IF `--fact`, `--decision`, `--by` o `--evidence` se reciben vacíos o solo con espacios, THEN THE CLI SHALL imprimir `ERROR:` por stderr, terminar con código 1 y no escribir ningún archivo.
- REQ-06: IF se usa `--decision` sin `--by`, THEN THE CLI SHALL imprimir `ERROR:`, terminar con código 1 y no escribir ningún archivo.
- REQ-07: IF se usa `--by` junto con `--fact`, THEN THE CLI SHALL imprimir `ERROR:`, terminar con código 1 y no escribir ningún archivo (supuesto S1: se rechaza en lugar de ignorarse en silencio).
- REQ-08: WHEN `note` registra una entrada, THE CLI SHALL conservar sin cambios `tasks`, `schema_version`, las entradas previas de `project.observations`/`project.decisions` y cualquier otra clave de `memory.json`.
- REQ-09: WHEN `memory.json` no existe, o existe sin `project`, `project.observations` o `project.decisions`, THE CLI SHALL crear la estructura faltante (vía `ensure_init` para el archivo) antes de añadir la entrada.
- REQ-10: IF `memory.json` no es JSON válido, THEN THE CLI SHALL imprimir `ERROR:`, terminar con código 1 y dejar el archivo sin cambios.
- REQ-11: THE README SHALL documentar `note` (ambas formas) en español neutro dentro de la sección de comandos del ciclo operativo y aclarar que registrar una decisión es una declaración, no autenticación.

## Criterios de aceptación
- AC-01: Con un `memory.json` que tiene una observación y una decisión previas y una tarea en `tasks`, `note --fact "F" --evidence "E"` devuelve 0 y `project.observations[-1]` es `{"at": <ISO UTC>, "fact": "F", "evidence": "E"}` (solo esas tres claves); la longitud de `observations` crece en 1 y `decisions` no cambia.
- AC-02: Con el mismo punto de partida, `note --decision "D" --by "Programador" --evidence "E"` devuelve 0 y `project.decisions[-1]` es `{"at": <ISO UTC>, "by": "Programador", "decision": "D", "evidence": "E"}` (solo esas cuatro claves); la longitud de `decisions` crece en 1 y `observations` no cambia.
- AC-03: `at` de la entrada nueva coincide con el valor devuelto por `now()` (controlado en la prueba) y tiene formato `AAAA-MM-DDTHH:MM:SS+00:00`.
- AC-04: Tras AC-01 y AC-02, `tasks`, `schema_version` y las entradas previas del proyecto son iguales (comparación de datos) a las del estado inicial.
- AC-05: `note` con `--fact` y `--decision` a la vez, y `note --evidence "E"` sin ninguno, devuelven 1, escriben `ERROR:` en stderr y `memory.json` queda byte a byte igual.
- AC-06: Cada uno de `--fact "  "`, `--decision ""`, `--by "  "` (con `--decision`) y `--evidence " "` devuelve 1, escribe `ERROR:` en stderr y `memory.json` queda byte a byte igual.
- AC-07: `note --decision "D" --evidence "E"` sin `--by` devuelve 1 y `memory.json` queda byte a byte igual; `note --fact "F" --by "X" --evidence "E"` devuelve 1 y `memory.json` queda byte a byte igual.
- AC-08: Sin `memory.json`, `note --fact "F" --evidence "E"` devuelve 0 y crea `memory.json` con `tasks == {}`, `decisions == []` y una única observación; con un `memory.json` cuyo `project` carece de `decisions` (o del objeto `project` completo), `note --decision ...` devuelve 0 y crea la lista con una entrada sin alterar `tasks`.
- AC-09: Con un `memory.json` inválido (texto no JSON), `note --fact "F" --evidence "E"` devuelve 1 con `ERROR:` y el archivo queda byte a byte igual.
- AC-10: `README.md` contiene, en la sección 5, un ejemplo de `sdd.py note --fact ... --evidence ...` y otro de `sdd.py note --decision ... --by ... --evidence ...`, y una frase que aclara que registrar una decisión es una declaración y no autentica a nadie.
- AC-11: La suite completa `python -m unittest discover -s tests -v` termina con código 0.

## Fuera de alcance
- Cambios en `.claude/hooks/pretool.py`, `.claude/agents/lider.md` u otros agentes, `.claude/settings.json` o `CLAUDE.md`.
- Prohibir a los agentes escribir en `.microharness/` o ejecutar `approve`/`seal` (tarea posterior).
- Escritura atómica, bloqueo de archivos o control de concurrencia de `memory.json`.
- Corregir las observaciones históricas con clave `observation`.
- Listar, editar o borrar notas; autenticar la identidad de `--by`.
- Cualquier otra mejora del parche de seguridad y refactors ajenos a `note`.
