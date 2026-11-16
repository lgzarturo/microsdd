# PASOS: trabajo verificable

Estrategia `tdd`. Pruebas en una clase nueva `FitnessTests` de `tests/test_sdd.py`, añadida en una sola edición, con raíz temporal, `GIT_CEILING_DIRECTORIES` como en `SealMonotonicoTests`, tablas y `subTest`. Presupuesto: 240 líneas de pruebas como máximo; si se supera, o si el hook rechaza por `rdd_max_lines`, detente y reporta.

Requisito previo: DEC-01 confirmada. Interfaz para las pruebas: `sdd.measure_python(data: bytes)` y `sdd.fitness_errors(spec)`, definidas en `plan.md`.

## RED: pruebas en `tests/test_sdd.py`
- [ ] T01 (AC-05, AC-06, AC-07): `test_parametros`, `test_complejidad` y `test_lineas`, por tabla sobre `measure_python`, con todas las filas de los AC.
- [ ] T02 (AC-01, AC-02): `test_plantilla_new` y `test_activacion_y_valores_por_defecto`.
- [ ] T03 (AC-03, AC-04): `test_tipos_invalidos`, por tabla, incluido `approve spec`, y `test_terminado_se_ignora`.
- [ ] T04 (AC-08, AC-09): `test_archivos_evaluados` y `test_pruebas_excluidas`, por tabla, más el caso sin repositorio.
- [ ] T05 (AC-10, AC-11, AC-12): `test_funciones_frente_a_head` y `test_lineas_frente_a_head`, por tabla, con commit y modificación por fila; incluyen las filas de límite subido.
- [ ] T06 (AC-13): `test_subir_limite_invalida_huella`.
- [ ] T07 (AC-14, AC-15): `test_formato_y_orden` y `test_archivo_no_analizable`, este último también vía `main()`.
- [ ] T08 (AC-16): `test_integracion_check_y_approve`, con `check`, `--run`, `--no-scope`, `approve spec` y `approve close`.
- [ ] T09 (AC-01..AC-16): ejecutar `sh .microharness/python.sh -m unittest tests.test_sdd`; comprobar que solo fallan las pruebas nuevas y por falta de comportamiento. El líder sella `tests/test_sdd.py` antes de continuar.

## GREEN: implementación en `.microharness/sdd.py`
- [ ] T10 (AC-01): añadir `FITNESS_DEFAULTS`, `FITNESS_TEST_PATTERNS` y el campo en la plantilla de `new`; `test_plantilla_new` en verde.
- [ ] T11 (AC-03, AC-04): añadir `fitness_config_errors` y llamarla desde `validate` en el bloque de tareas no `terminado`.
- [ ] T12 (AC-05, AC-06, AC-07): añadir `measure_python`, sin dependencias nuevas; las tres pruebas de tabla en verde.
- [ ] T13 (AC-02, AC-08, AC-09): añadir `fitness_errors` con el filtrado de archivos y la comparación con los límites, sin base de `HEAD` todavía; llamarla desde `validate` antes de `if run and not errors`, solo con alcance.
- [ ] T14 (AC-10, AC-11, AC-12): añadir la lectura de `HEAD` en bytes y la regla frente a la base.
- [ ] T15 (AC-14, AC-15): fijar el orden de errores y convertir errores de lectura y análisis en `Fitness: <ruta>: no se pudo analizar: <detalle>`.
- [ ] T16 (AC-13, AC-16): sin código nuevo previsto; comprobar que `test_subir_limite_invalida_huella` y `test_integracion_check_y_approve` pasan.
- [ ] T17 (AC-01..AC-16): ejecutar `sh .microharness/python.sh -m unittest tests.test_sdd`; todo en verde.

## Documentación
- [ ] T18 (AC-18): en `assets/arnes-completo.md`, añadir `fitness` al ejemplo de `spec.json` y una subsección junto a «Mutation testing y hashing de pruebas» con medidas, archivos evaluados, regla frente a `HEAD`, subir un límite y límites conocidos (`plan.md`, Riesgos).
- [ ] T19 (AC-18): en `assets/arnes-completo.md`, añadir la fila «Fitness estructural» a «Qué se obliga y qué NO»: solo Python, estructura y no calidad semántica, no es control de seguridad.
- [ ] T20 (AC-18): en `assets/proceso-versionado.md`, añadir `testing.fitness` a API-02.

## Verificación
- [ ] T21 (AC-17): comprobar con `git diff` que `.microharness/sdd.py` no añade imports ni cambia `__version__`.
- [ ] T22 (AC-19): ejecutar `sh .microharness/python.sh .microharness/sdd.py check testing-fitness --run`; salida `OK` con al menos 470 pruebas y sin campo `fitness` activo en la spec de esta tarea.
