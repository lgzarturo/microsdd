# QUÉ: requisitos

## Objetivo

Cerrar el riesgo R8: hoy `check --run` (y por tanto `approve close`, que llama a `validate(run=True)`) solo mira el código de salida de cada comando de `testing.commands`. Un comando que sale con 0 sin ejecutar ninguna prueba pasa la puerta. Ejemplos: `python -m unittest --help`, un `discover` sobre un directorio vacío en Python 3.10 y 3.11, o `python -c 'print("tests ok")'`.

Se quiere:

1. Que `check --run` capture la salida de cada comando de `testing.commands`, la siga mostrando y cuente cuántas pruebas ejecutó según el resumen del runner.
2. Que la puerta falle si un comando no muestra un recuento reconocible o si el recuento es menor que `testing.min_tests`. `min_tests` es opcional, vale 1 por defecto y debe ser un entero mayor o igual a 1.
3. Que `mutation.command` se siga ejecutando sin contarse.
4. Que las tareas `terminado` no queden invalidadas en retrospectiva. `fundamentos-diseno`, `herramienta-release` y `proceso-versionado` tienen comandos `python -c ...` sin recuento.

## Precondiciones

- Python 3.10 o superior, solo biblioteca estándar. Sin dependencias nuevas.
- Decisión humana previa, comunicada por el líder: el implementador modifica `.microharness/sdd.py` por Bash, porque el hook le niega Write/Edit en `.microharness/`.
- Decisión humana registrada en `memory.json` (2026-10-13): las validaciones nuevas sobre comandos de prueba solo se aplican mientras la tarea no esté `terminado`. Esta spec aplica el mismo criterio al recuento.
- Las pruebas de `tests/test_sdd.py` redirigen `sdd.ROOT` y `sdd.MEMORY` a un directorio temporal. El fixture `MicroSDDTests.setUp` usa hoy `[sys.executable, '-c', 'print("tests ok")']` como suite. Con este cambio esa suite deja de pasar la puerta y hay que ajustar el fixture.
- Prueba de la suite del repositorio: `python -m unittest discover -s tests -v`.

## Requisitos EARS

- REQ-01: WHEN `check --run` (o `validate(slug, run=True)`) ejecuta un comando de `testing.commands` o `mutation.command`, THE sistema SHALL capturar su stdout y su stderr. Al terminar el comando, SHALL reproducir cada flujo en el suyo (stdout del proceso hijo en `sys.stdout`, stderr en `sys.stderr`). La línea `EJECUTANDO: ...`, el timeout de 300 s, `cwd=ROOT`, `shell=False` y la sustitución de `python`/`python3` por `sys.executable` no cambian.
- REQ-02: THE sistema SHALL ofrecer una función de módulo `tests_ran(output: str) -> int | None` que devuelva el número de pruebas ejecutadas según el resumen del runner, o `None` si no reconoce ninguno:
  - unittest: `Ran N test(s) in` al inicio de línea.
  - pytest: `N passed`.
  - bun: `N pass` al inicio de línea, con espacios iniciales opcionales.
  - Maven: `Tests run: N`.
  - Go: cada línea que empieza con `ok` seguido de espacio y un paquete cuenta como 1.
- REQ-03: WHEN una salida contiene varias coincidencias del mismo resumen numérico (unittest, pytest, bun, Maven), THE sistema SHALL usar la última. WHEN coinciden varios formatos distintos, THE sistema SHALL devolver el mayor valor entre ellos.
- REQ-04: WHILE la tarea no esté `terminado`, WHEN un comando de `testing.commands` termina con código 0, THE sistema SHALL calcular `tests_ran` sobre su stdout y stderr. IF el resultado es `None` o menor que `min_tests`, THEN SHALL añadir un error con este texto: `Se requieren al menos {min_tests} pruebas ejecutadas; detectadas: {N|ninguna} en {comando}`.
- REQ-05: THE sistema SHALL aplicar REQ-04 a cada comando de `testing.commands` por separado. Un comando con recuento suficiente no compensa a otro sin recuento ni con recuento menor (ver D-01 en `plan.md`).
- REQ-06: IF un comando termina con código distinto de 0, THEN THE sistema SHALL mantener solo el error actual `Comando falló (...)` para ese comando, sin añadir el error de recuento.
- REQ-07: WHEN se ejecuta `mutation.command` (si `mutation.enabled`), THE sistema SHALL no contar sus pruebas ni exigir `min_tests`.
- REQ-08: WHILE la tarea esté `terminado`, THE sistema SHALL ejecutar y mostrar los comandos igual que antes, sin aplicar REQ-04.
- REQ-09: WHEN se ejecuta `validate` (con o sin `--run`) y `testing.min_tests` existe, IF no es un `int` (se excluye `bool`) mayor o igual a 1, THEN THE sistema SHALL añadir el error `testing.min_tests debe ser un entero mayor o igual a 1`. Si la clave no existe, el valor es 1 (ver D-02 en `plan.md`).
- REQ-10: WHEN el flujo de destino tiene `buffer` (consola o pipe real), THE sistema SHALL reproducir los bytes del proceso hijo sin recodificarlos. Si no lo tiene (por ejemplo, `io.StringIO` en pruebas), SHALL escribir el texto decodificado como UTF-8 con `errors='replace'`. Para contar, la salida se decodifica como UTF-8 con `errors='replace'`.
- REQ-11: `README.md` SHALL documentar `testing.min_tests`: es opcional, vale 1 por defecto y debe ser un entero mayor o igual a 1. También SHALL indicar qué runners se reconocen, que el mínimo se exige por comando, que el comando de mutación no se cuenta y que las tareas `terminado` no se cuentan.

## Criterios de aceptación

- AC-01: `tests_ran` devuelve estos valores:
  - `'Ran 12 tests in 0.1s\nOK\n'` → 12.
  - `'Ran 1 test in 0.0s\n'` → 1.
  - `'Ran 0 tests in 0.000s\n'` → 0.
  - `'==== 5 passed, 1 skipped in 0.2s ===='` → 5.
  - `' 7 pass\n 0 fail\n'` → 7.
  - `'Tests run: 3, Failures: 0\n...\nResults:\nTests run: 9, Failures: 0'` → 9.
  - `'ok  \tej/a\t0.01s\nok  \tej/b\t(cached)\n?   \tej/c\t[no test files]\n'` → 2.
  - `'Ran 1 test in 0.0s\n...\nRan 40 tests in 3.0s\n'` → 40 (salida anidada: vale la última).
  - `'tests ok'` → `None`.
  - `''` → `None`.
- AC-02: con la tarea en `pendiente` y `testing.commands = [[sys.executable, '-m', 'unittest', 'discover', '-s', 'pruebas']]`, donde `pruebas/` del `ROOT` temporal contiene una prueba que pasa, `validate(..., run=True)` devuelve `[]`. Con `sys.stdout` y `sys.stderr` sustituidos por `io.StringIO`, el texto de stderr contiene `Ran 1 test` y el de stdout contiene `EJECUTANDO:`.
- AC-03: con `testing.commands = [[sys.executable, '-m', 'unittest', '--help']]` (sale con 0 y no ejecuta pruebas), `validate(..., run=True)` contiene un error con `al menos 1` y `ninguna`.
- AC-04: con la suite de AC-02 (1 prueba) y `testing.min_tests = 2`, `validate(..., run=True)` contiene un error con `al menos 2` y `detectadas: 1`. Con `min_tests = 1` devuelve `[]`.
- AC-05: con `testing.min_tests` igual a `0`, `-1`, `'2'`, `1.5`, `True` o `None`, `validate(...)` sin `run` contiene `testing.min_tests debe ser un entero mayor o igual a 1`. Con la clave ausente, `1` o `5` no aparece ese error.
- AC-06: con `testing.commands = [<suite de AC-02>, [sys.executable, '-m', 'unittest', '--help']]`, `validate(..., run=True)` contiene exactamente un error de recuento, y ese error nombra el segundo comando (contiene `--help`).
- AC-07: con la suite de AC-02, `mutation.enabled = true` y `mutation.command = [sys.executable, '-m', 'unittest', '--help']`, `validate(..., run=True)` devuelve `[]`.
- AC-08: con `testing.commands = [[sys.executable, '-c', 'raise SystemExit(1)']]` (prueba existente `test_testing_failure_is_reported`), los errores contienen `Comando falló` y ninguno contiene `al menos`.
- AC-09: si una tarea llega a `terminado` por el ciclo normal (`approve spec`, `review APROBADO`, `approve close`) y después `validate(..., run=True)` se ejecuta con `sdd.tests_ran` parcheado para devolver `None`, el resultado es `[]`. Si la tarea está en `proceso` (antes del cierre), el mismo parche produce el error de recuento.
- AC-10: `python -m unittest discover -s tests -v` pasa completa. En `git diff tests/test_sdd.py` ninguna línea eliminada contiene `assert` ni `def test_`: los nombres y las aserciones existentes no cambian. Solo cambian el fixture de `MicroSDDTests.setUp` y la preparación de `test_run_replaces_python_alias_with_current_interpreter`, y se añaden pruebas nuevas.
- AC-11: `README.md` menciona `min_tests` con su valor por defecto 1, que es por comando, que el comando de mutación no se cuenta, que las tareas `terminado` no se cuentan y los cinco runners de REQ-02. La fila «Tests y mutación» de la tabla de garantías refleja el recuento mínimo.
- AC-12: `sh .microharness/python.sh .microharness/sdd.py check check-min-pruebas --run --no-scope`, con la tarea en `proceso`, imprime la salida de la suite y termina con `OK: ... ejecución de pruebas.`. `check fundamentos-diseno`, `check herramienta-release` y `check proceso-versionado` sin `--run` no muestran errores nuevos atribuibles a `min_tests`.

## Fuera de alcance

- La lista blanca de runners de prueba (R6). Es otra tarea de la serie. Esta tarea no rechaza `python -c` ni otros ejecutables al validar.
- Que un comando imprima un resumen falso (por ejemplo, `print("Ran 5 tests in 0s")`). Lo mitiga R6, no esta tarea.
- Reconocer otros runners (Gradle, Jest, `cargo test`, Vitest, etc.) o contar pruebas individuales de Go sin `-v`. En Go se cuentan paquetes `ok`.
- Mostrar la salida en tiempo real (streaming). Ahora se muestra al terminar cada comando.
- Recuperar la salida parcial de un comando que agota el timeout.
- Cambiar `spec.json` de tareas existentes, `.claude/**`, `CLAUDE.md`, `memory.json`, el instalador o `scripts/**`.
- Contar las pruebas de `mutation.command`.
