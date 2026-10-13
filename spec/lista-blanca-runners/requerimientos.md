# QUÉ: requisitos

## Objetivo
Riesgo R6 del análisis de seguridad: hoy `check --run` ejecuta cualquier argv declarado en `testing.commands` o `mutation.command` (p. ej. `python -c ...`, `sh -c ...`, `/ruta/python3 ...`). Esta tarea restringe esos comandos a prefijos de argv de runners de pruebas conocidos, ampliables por el proyecto en `project.allowed_test_commands` de `.microharness/memory.json`. Solo se aplica a tareas que no estén `terminado`.

## Hechos comprobados
- `validate()` en `.microharness/sdd.py` solo exige que cada comando sea una lista no vacía de strings no vacíos; `mutation.command` solo se exige no vacío si `enabled`.
- En `check --run`, si `command[0]` es exactamente `python` o `python3` se sustituye por `sys.executable`; la ejecución solo ocurre si `validate` no acumuló errores (`run and not errors`).
- `approve spec` llama a `validate(scope=False)`: un error estructural nuevo impide aprobar la spec.
- `tests/test_sdd.py` (`MicroSDDTests.setUp`) usa `[sys.executable, '-m', 'unittest', 'discover', '-s', 'pruebas']`. Usan `-c`: `test_testing_failure_is_reported` y `test_failed_command_has_no_count_error` (ambos `[sys.executable, '-c', 'raise SystemExit(1)']`). `NO_TESTS = [sys.executable, '-m', 'unittest', '--help']` ya cumple el prefijo `python -m unittest`.
- Specs del repositorio: todas declaran `python -m unittest ...`, salvo `fundamentos-diseno`, `proceso-versionado` (`python -c ...`) y `herramienta-release` (`python -c ...`, `python .microharness/sdd.py --version`), las tres en `terminado`. Ninguna activa mutación. Las no terminadas (`bloquear-autoaprobacion`, esta) usan `python -m unittest`.
- `.microharness/python.sh` elige el intérprete (`MICROSDD_PYTHON` → `uv run ... python` → `python3` → `python` → `py -3`); el checker se ejecuta con ese intérprete y `python`/`python3` de los comandos se resuelven a él (`sys.executable`).

## Precondiciones
- Python >= 3.10, solo biblioteca estándar.
- `check-min-pruebas` terminado (recuento y exención de `terminado` ya existen).
- Decisión humana registrada: la validación de lista blanca solo se aplica mientras la tarea no esté `terminado`.
- El implementador modifica `.microharness/sdd.py` por Bash (decisión de proceso previa). `docs/arquitectura.md` lo actualiza el líder.

## Definiciones
- **Prefijos predeterminados** (tokens exactos, sensibles a mayúsculas): `python -m unittest`, `python3 -m unittest`, `python -m pytest`, `python3 -m pytest`, `pytest`, `npm test`, `pnpm test`, `yarn test`, `bun test`, `go test`, `cargo test`, `mvn test`, `./mvnw test`, `gradle test`, `./gradlew test`, `mutmut run`.
- **Comando permitido:** tras normalizar `command[0] == sys.executable` a `python`, sus primeros `len(p)` elementos son iguales a algún prefijo `p` (predeterminado o de la ampliación). El resto de argumentos es libre.
- **Ampliación:** `project.allowed_test_commands` en `memory.json`, lista de prefijos; cada prefijo es una lista no vacía de strings no vacíos.

## Requisitos EARS
- REQ-01: WHILE la tarea no esté `terminado`, WHEN `check` valida un elemento de `testing.commands` que no es un comando permitido, THE sistema SHALL reportar `Comando de pruebas fuera de la lista blanca: <comando>`.
- REQ-02: WHILE la tarea no esté `terminado`, IF `mutation.enabled` es verdadero y `mutation.command` no vacío no es un comando permitido, THEN THE sistema SHALL reportar `Comando de mutación fuera de la lista blanca: <comando>`.
- REQ-03: WHEN el primer elemento de un comando es exactamente `sys.executable`, THE sistema SHALL tratarlo como `python`; cualquier otro primer elemento con ruta SHALL compararse literalmente y, salvo que figure en la ampliación, quedar fuera de la lista.
- REQ-04: WHEN `project.allowed_test_commands` contiene prefijos válidos, THE sistema SHALL aceptarlos además de los predeterminados.
- REQ-05: WHILE la tarea no esté `terminado`, IF `project.allowed_test_commands` existe y no es una lista, o alguno de sus elementos no es una lista no vacía de strings no vacíos, THEN THE sistema SHALL reportar `project.allowed_test_commands inválido: <entrada>` por cada entrada inválida y seguir usando las entradas válidas.
- REQ-06: WHILE la tarea esté `terminado`, THE sistema SHALL omitir la validación de lista blanca y de la ampliación.
- REQ-07: IF hay un comando fuera de la lista blanca, THEN `check --run` SHALL no ejecutar ningún comando (comportamiento existente de `run and not errors`).

## Criterios de aceptación
- AC-01: Con la tarea en `pendiente`, cada uno de los 16 prefijos predeterminados, con y sin argumentos extra (p. ej. `["pytest", "-q"]`, `["go", "test", "./..."]`), no produce ningún error que contenga `lista blanca` en `validate` sin `run`.
- AC-02: `[sys.executable, "-m", "unittest", ...]` y `[sys.executable, "-m", "pytest"]` se aceptan; `[sys.executable, "-c", "..."]` se rechaza.
- AC-03: Se rechazan con `Comando de pruebas fuera de la lista blanca: ` al menos: `["python", "-c", "print(1)"]`, `["python3", ".microharness/sdd.py", "--version"]`, `["sh", "-c", "echo x"]`, `["bash", "-c", "x"]`, `["/tmp/evil/python3", "-m", "unittest"]`, `["curl", "https://example.com"]`, `["py", "-3", "-m", "unittest"]`, `["uv", "run", "pytest"]`, `["npm", "run", "test"]`, `["Python", "-m", "unittest"]`, `["python", "-m"]` (más corto que el prefijo) y `["python", "-m", "unittestx"]`. Con varios comandos, solo el no permitido genera error.
- AC-04: Con `mutation.enabled = true`: `["sh", "-c", "echo"]` produce `Comando de mutación fuera de la lista blanca: `; `["mutmut", "run"]` no produce error de lista blanca. Con `enabled = false`, un `mutation.command` no permitido no produce error.
- AC-05: Con `project.allowed_test_commands = [["make", "test"]]`, `["make", "test"]` y `["make", "test", "-j2"]` se aceptan; `["make", "install"]` se rechaza. Sin la clave, `["make", "test"]` se rechaza.
- AC-06: Con `project.allowed_test_commands` igual a `"make test"`, o conteniendo `"make test"`, `[]`, `[""]` o `[1]`, `validate` reporta `project.allowed_test_commands inválido: ` por cada entrada inválida; una entrada válida en la misma lista (`["make", "test"]`) sigue permitiendo `["make", "test"]`.
- AC-07: Con `state = "terminado"` y comandos o ampliación fuera de la lista (p. ej. `["python", "-c", "print(1)"]` y ampliación `"x"`), `validate` no reporta ningún error que contenga `lista blanca` ni `allowed_test_commands`.
- AC-08: Con un comando no permitido que crearía un archivo marcador (`[sys.executable, "-c", "open('marca.txt','w')"]`), `validate(run=True)` reporta el error de lista blanca, no imprime `EJECUTANDO:` y el marcador no existe.
- AC-09: `test_testing_failure_is_reported` y `test_failed_command_has_no_count_error` usan un runner permitido (`[sys.executable, "-m", "unittest", "discover", "-s", <carpeta con una prueba que falla>]`) sin cambiar su nombre ni sus aserciones; la suite completa `python -m unittest discover -s tests -v` pasa.
- AC-10: En el repositorio real, `sdd.py check <slug> --no-scope` sigue respondiendo `OK` para `fundamentos-diseno`, `proceso-versionado`, `herramienta-release` y `check-min-pruebas`, y para `lista-blanca-runners`.
- AC-11: `README.md` documenta: prefijos predeterminados, equivalencia de `sys.executable`, rechazo de otras rutas, ampliación en `memory.json` (formato y reporte de entradas inválidas), exención de `terminado`, que `py -3` y `uv run` no están incluidos (y por qué), y el límite de que `npm|pnpm|yarn|bun test`, `./mvnw`, `./gradlew` y cualquier runner ejecutan código o scripts del propio proyecto: la lista acota el ejecutable, no lo que ejecuta.

## Fuera de alcance
- Impedir que un agente edite `memory.json` para ampliar la lista (tarea `bloquear-autoaprobacion`).
- Validar el contenido de scripts de proyecto (`package.json`, `mvnw`, `gradlew`, `conftest.py`) o de las pruebas.
- Variantes Windows (`mvnw.cmd`, `gradlew.bat`, `.\gradlew`), `py -3`, `uv run`, `make test`, `npx`, `tox`, `nox`: se habilitan por ampliación.
- Cambiar la sustitución de `python`/`python3` por `sys.executable`, el recuento de pruebas o la exención de `terminado` existente.
- Modificar specs cerradas, `.claude/**`, `.microharness/python.sh`, el instalador o `docs/` distintos de `docs/arquitectura.md` (este último lo edita el líder).
