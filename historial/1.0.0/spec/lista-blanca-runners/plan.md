# CÓMO: diseño mínimo

## Situación comprobada
- `.microharness/sdd.py`, `validate()`: el bucle de `testing.commands` solo valida forma (`Comando de pruebas inválido; ...`); `mutation` solo exige comando si `enabled`. `min_tests` y la exención `s.get('state') != 'terminado'` (sellos, recuento) ya existen. `memory` está cargada en `validate` vía `task_files`.
- La ejecución (`run and not errors`) sustituye `python`/`python3` por `sys.executable` y no se ejecuta si hubo errores estructurales.
- Fixtures afectados en `tests/test_sdd.py`: solo los dos `-c 'raise SystemExit(1)'` (`test_testing_failure_is_reported`, `test_failed_command_has_no_count_error`). El resto (`SUITE`, `NO_TESTS`, alias `python`/`python3`) ya usa `-m unittest`.
- Specs cerradas con `python -c`/`python .microharness/sdd.py --version` están en `terminado` y quedan exentas por decisión humana.
- Referencia externa (no confiable, base antigua): `TEST_COMMANDS`, `allowed_test_commands()` y `command_allowed()` en el parche; ignoraba en silencio entradas inválidas y no tenía exención de `terminado`. Se adapta, no se copia.

## Decisión y justificación
1. Constante de módulo `TEST_COMMANDS`: tupla de tuplas con los 16 prefijos de la definición. Comparación exacta de tokens por prefijo: simple, sin regex ni normalización de rutas, y cualquier ejecutable con ruta queda fuera porque no es igual a ningún token.
2. Función `allowed_test_commands(memory) -> tuple[list[tuple[str, ...]], list[str]]` (o equivalente mínimo) que devuelve prefijos válidos (predeterminados + ampliación) y mensajes `project.allowed_test_commands inválido: <entrada>` para las entradas inválidas. Si la clave no existe: sin ampliación ni errores. Si no es lista: un error para el valor completo.
3. Función `command_allowed(command, allowed) -> bool`: si `command` no es lista no vacía devuelve `False`; si `command[0] == sys.executable` se compara como `['python', *command[1:]]`; aceptado si `tuple(argv[:len(p)]) == p` para algún `p`.
4. En `validate()`, solo `if s.get('state') != 'terminado'`: añadir errores de ampliación; para cada comando de forma válida no permitido, `Comando de pruebas fuera de la lista blanca: {cmd}`; si `mutation.enabled` y hay comando, `Comando de mutación fuera de la lista blanca: {cmd}`. No se toca el bloque de ejecución: REQ-07 sale de `run and not errors`.
5. Pruebas: los dos fixtures `-c` pasan a crear una carpeta propia (p. ej. `pruebas_fallo/test_falla.py` con una prueba que falla) y ejecutar `[sys.executable, '-m', 'unittest', 'discover', '-s', 'pruebas_fallo']`. No se usa `pruebas/` porque `SUITE` y otras pruebas esperan exactamente 1 prueba allí. La salida de un unittest fallido sale con código 1, así que `Comando falló` se mantiene y no aparece error de recuento (aserciones intactas).

### Entradas inválidas de la ampliación: reportar (recomendado) frente a ignorar
- Se reportan como error de `check`: una ampliación mal escrita (p. ej. `"make test"` como string) produciría si se ignorara un `fuera de la lista blanca` confuso sin pista de la causa. Reportar es fail-closed y diagnosticable; el coste es un bucle.
- Efecto: una entrada inválida bloquea `check` de todas las tareas no terminadas del proyecto hasta corregirla. Se considera aceptable porque la memoria es configuración del proyecto y el error indica la entrada exacta.

### `py -3` y `uv run`: no se incluyen (recomendado)
- `check --run` ya ejecuta `python`/`python3` con `sys.executable`, el intérprete elegido por `.microharness/python.sh` (que contempla `py -3` y `uv`). Declarar `python -m unittest` es portable; `py -3` sería redundante y solo Windows.
- `uv run` es un ejecutor genérico: permitir el prefijo `uv run` admitiría `uv run sh -c ...` y anularía la lista. Restringirlo a `uv run ... python -m unittest` exige parsear opciones de `uv` (YAGNI). Quien lo necesite lo amplía con un prefijo exacto en `memory.json`.

## Alternativas descartadas
- Regex o globs por prefijo: más superficie y ambigüedad que la igualdad de tokens.
- Resolver rutas (`shutil.which`, `Path.resolve`) para admitir `/usr/bin/python3`: depende del entorno y reabre el vector de ejecutables con ruta.
- Validar solo en `--run`: dejaría aprobar (`approve spec`) specs con comandos arbitrarios.
- Ignorar en silencio entradas inválidas (parche externo): ver arriba.
- Aplicar a tareas `terminado`: rompería tres specs cerradas, contra la decisión humana.

## Invariantes y riesgos
- Invariante: con la lista predeterminada, todo comando que hoy usan las specs no terminadas sigue pasando; las terminadas no cambian.
- Invariante: no cambia la sustitución por `sys.executable` ni el recuento ni el texto de errores existentes.
- Riesgo (límite R6, documentar): `npm|pnpm|yarn|bun test`, `./mvnw`, `./gradlew`, `pytest` (plugins, `conftest.py`) y `python -m unittest` ejecutan código del propio proyecto. Si el implementador tiene esos archivos en su alcance puede cambiar lo que se ejecuta. La lista acota el ejecutable, no su comportamiento.
- Riesgo: `./mvnw` y `./gradlew` son rutas relativas permitidas explícitamente; en Windows (`mvnw.cmd`, `gradlew.bat`) no están y requieren ampliación.
- Riesgo: la ampliación vive en `memory.json`, que hoy un agente puede editar; lo cierra `bloquear-autoaprobacion`, fuera de esta tarea.
- Riesgo: comparación sensible a mayúsculas; en Windows `Python` o `PYTHON.EXE` se rechazan (aceptable: el contrato documentado usa minúsculas).
- Efecto secundario: specs nuevas de documentación que usaban `python -c` como verificación deben convertir la verificación en una prueba `unittest` o ampliar la lista.
- Mutación: desactivada (no hay herramienta instalada; lógica de igualdad de prefijos cubierta por casos límite AC-03/AC-05/AC-06). Mutaciones manuales sugeridas al revisor en `spec.json`.
