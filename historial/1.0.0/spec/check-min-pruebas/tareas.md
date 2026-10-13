# PASOS: trabajo verificable

Estrategia TDD. El implementador modifica `.microharness/sdd.py` por Bash (decisión humana previa). Comando de pruebas: `python -m unittest discover -s tests -v`.

- [ ] T01 (AC-10): en `tests/test_sdd.py`, cambiar el fixture de `MicroSDDTests.setUp` para que cree `ROOT/pruebas/test_ok.py` (un `unittest.TestCase` con una prueba que pasa) y use `[sys.executable, '-m', 'unittest', 'discover', '-s', 'pruebas']`. Adaptar la preparación de `test_run_replaces_python_alias_with_current_interpreter`: escribe `pruebas/test_alias.py`, que guarda `sys.executable` en el archivo esperado, y usa `[alias, '-m', 'unittest', 'discover', '-s', 'pruebas']`. No tocar aserciones ni nombres. Verificar que la suite sigue en verde con el `sdd.py` actual.
- [ ] T02 (AC-01): añadir pruebas de `sdd.tests_ran` con los casos literales de AC-01. Confirmar RED (`AttributeError` o fallo).
- [ ] T03 (AC-02, AC-03, AC-04, AC-06, AC-07, AC-08): añadir pruebas de `validate(..., run=True)`, con `sys.stdout` y `sys.stderr` sustituidos por `io.StringIO`, para estos casos:
  - Suite real que pasa y cuya salida se reproduce (AC-02).
  - `unittest --help` sin recuento (AC-03).
  - Umbral `min_tests = 2` (AC-04).
  - Dos comandos, uno sin recuento (AC-06).
  - Mutación no contada (AC-07).
  - Comando que falla sin error de recuento (AC-08).

  Confirmar RED en AC-02 (captura), AC-03, AC-04 y AC-06.
- [ ] T04 (AC-05): añadir una prueba de `validate(...)` sin `run` con los valores inválidos y válidos de `min_tests`. Confirmar RED.
- [ ] T05 (AC-09): añadir una prueba con el ciclo `approve spec` → `review APROBADO` → `approve close` y, después, `validate(run=True)` con `mock.patch.object(sdd, 'tests_ran', return_value=None)` que devuelve `[]`. Antes del cierre, en `proceso`, con el mismo parche, aparece el error de recuento. Confirmar RED en la parte de `proceso`.
- [ ] T06 (AC-01): en `.microharness/sdd.py`, añadir `TEST_COUNT_RES` y `tests_ran()` (última coincidencia por patrón numérico, conteo de líneas `ok` de Go, máximo entre patrones, `None` si no hay ninguno). T02 en verde.
- [ ] T07 (AC-05): en `validate`, leer `min_tests = testing.get('min_tests', 1)` y añadir el error de REQ-09 si no es `int` (sin `bool`) ≥1. T04 en verde.
- [ ] T08 (AC-02, AC-03, AC-04, AC-06, AC-07, AC-08, AC-09): en el bucle de `run`:
  - Distinguir los comandos que se cuentan de la mutación.
  - Ejecutar con `capture_output=True` (bytes) y reproducir stdout y stderr con el helper `echo` (bytes a `buffer` si existe; si no, texto UTF-8 con `replace`).
  - Si el código es 0, el comando se cuenta y el estado no es `terminado`, aplicar `tests_ran` y `min_tests` con el mensaje de REQ-04.

  T03 y T05 en verde.
- [ ] T09 (AC-11): en `README.md`, documentar `testing.min_tests` (opcional, por defecto 1, entero ≥1, por comando), los runners reconocidos (unittest, pytest, bun, Maven, Go), que la mutación no se cuenta y que las tareas `terminado` no se cuentan. Actualizar la fila «Tests y mutación» de la tabla de garantías. Verificar con `grep -n min_tests README.md`.
- [ ] T10 (AC-10): ejecutar `sh .microharness/python.sh -m unittest discover -s tests -v`: todo en verde. Revisar `git diff tests/test_sdd.py` y confirmar que ninguna línea eliminada contiene `assert` ni `def test_`.
- [ ] T11 (AC-12): ejecutar `sh .microharness/python.sh .microharness/sdd.py check check-min-pruebas --run --no-scope` con la tarea en `proceso`: muestra la salida de la suite y termina con `OK`. Ejecutar `check` sin `--run` sobre `fundamentos-diseno`, `herramienta-release` y `proceso-versionado` y confirmar que no aparece ningún error con `min_tests`.
