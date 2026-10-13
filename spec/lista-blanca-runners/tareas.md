# PASOS: trabajo verificable

Cada prueba nueva se observa en RED antes de implementar. Archivos: `tests/test_sdd.py`, `.microharness/sdd.py` (por Bash), `README.md`.

- [ ] T01 (AC-09): en `tests/test_sdd.py`, cambiar solo la preparación de `test_testing_failure_is_reported` y `test_failed_command_has_no_count_error`: crear `pruebas_fallo/test_falla.py` con una prueba que falla y usar `[sys.executable, '-m', 'unittest', 'discover', '-s', 'pruebas_fallo']`. Mismos nombres y aserciones. Ejecutar la suite: debe seguir en verde antes de tocar `sdd.py`.
- [ ] T02 (AC-01, AC-02, AC-03): añadir en `MicroSDDTests` pruebas de aceptación de los 16 prefijos (con y sin argumentos extra, `subTest`), de `sys.executable` como `python` y de rechazo de la lista de AC-03 (incluido el caso de varios comandos con uno solo inválido). Observar RED.
- [ ] T03 (AC-04): pruebas de `mutation.command` permitido/no permitido con `enabled` verdadero y falso. Observar RED.
- [ ] T04 (AC-05, AC-06): pruebas de ampliación válida, prefijo con argumentos extra, prefijo no ampliado, ausencia de clave, valor no lista y entradas inválidas mezcladas con una válida (escribiendo `project.allowed_test_commands` en `sdd.MEMORY`). Observar RED.
- [ ] T05 (AC-07): prueba con `state = "terminado"` en `spec.json`, comando `python -c` y ampliación `"x"`: ningún error con `lista blanca` ni `allowed_test_commands`.
- [ ] T06 (AC-08): prueba con comando no permitido que crearía `marca.txt`: `validate(run=True)` reporta lista blanca, sin `EJECUTANDO:` en stdout y sin `marca.txt`. Observar RED.
- [ ] T07 (AC-01..AC-08): en `.microharness/sdd.py` añadir `TEST_COMMANDS`, `allowed_test_commands(memory)` y `command_allowed(command, allowed)`, y las comprobaciones en `validate()` dentro de `if s.get('state') != 'terminado'`, con los mensajes exactos de requerimientos. Sin tocar el bloque de ejecución. Suite en verde.
- [ ] T08 (AC-10): ejecutar `sh .microharness/python.sh .microharness/sdd.py check <slug> --no-scope` para `fundamentos-diseno`, `proceso-versionado`, `herramienta-release`, `check-min-pruebas` y `lista-blanca-runners`: todos `OK`.
- [ ] T09 (AC-11): en `README.md`, junto a la explicación de `check --run` (sección 1, «Lanzador») y en la tabla de la sección 7, documentar prefijos, `sys.executable`, rechazo de rutas, ampliación y su reporte de errores, exención de `terminado`, por qué no se incluyen `py -3` ni `uv run`, y el límite de que los runners ejecutan scripts del proyecto.
- [ ] T10 (AC-09, AC-11): ejecutar `sh .microharness/python.sh -m unittest discover -s tests -v` y `sh .microharness/python.sh .microharness/sdd.py check lista-blanca-runners --run` (lo valida el revisor). El líder actualiza `docs/arquitectura.md` (no lo edita el implementador).
