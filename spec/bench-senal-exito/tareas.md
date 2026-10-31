# PASOS: trabajo verificable

Estrategia `tdd`. Contenidos exactos, interfaz y textos en `plan.md`. Requisito previo: DEC-01, DEC-02 y DEC-03 resueltas. Las tareas marcadas con DEC se omiten o ajustan según lo decidido.

**Presupuesto (líneas contadas por el hook):**

| Bloque | Tope |
|---|---|
| `tests/test_bench_senal.py` | 150 |
| `test_fixture.py` (cinco archivos) | 91 |
| `.microharness/bench.py` | 60 |
| Aviso, `notes`, `bench/README.md`, `eval-esfuerzo.md` | 30 |
| `fixture_mod.py` y `task.json` | 9 |
| `tests/test_bench.py` | 2 |
| **Total** | **342** |

**Regla de parada.** Detente y reporta al líder, sin fragmentar ediciones ni recortar pruebas por tu cuenta, si superas un tope, si el total se acerca a 500 o si el hook rechaza por `rdd_max_lines`, por el alcance o por cualquier otra causa.

**Ediciones.** `Write` solo para `tests/test_bench_senal.py`. En archivos existentes, `Edit` con `old_string` por debajo del 80 % del archivo: en los fixtures, una edición para la cabecera y otra para el cuerpo; en `fixture_mod.py`, solo el fragmento que cambia.

**Sin red.** No ejecutes el bench con red, `bench ab` ni `bench run --provider openrouter`.

## RED: pruebas en `tests/test_bench_senal.py`
- [ ] T01 (AC-01 a AC-09): crear el archivo con la carga de `bench` como en `tests/test_ab_harness.py`, `urlopen` parcheado para fallar en `setUp`, la tabla `CORREGIDO` y estos 8 métodos, por tabla y con `subTest`:
  - `test_resumen_unittest` (AC-01)
  - `test_cero_pruebas_real` (AC-02)
  - `test_rojo_y_verde` (AC-03, AC-04), brazos `base` y `treatment`
  - `test_run_cell_usa_senal` (AC-05)
  - `test_prueba_manipulada_se_restaura` (AC-06, DEC-01)
  - `test_entorno_de_evaluacion` (AC-07, DEC-03)
  - `test_huella_fixture` (AC-08)
  - `test_aviso_baseline` (AC-09)
- [ ] T02 (AC-01 a AC-09): ejecutar `sh .microharness/python.sh -m unittest tests.test_bench_senal`. Fallan todos por falta de comportamiento, salvo `test_huella_fixture`, que pasa hoy y es una guarda. Comprobar que el archivo no pasa de 150 líneas. El líder sella `tests/test_bench_senal.py` antes de continuar.

## GREEN: señal de éxito en `.microharness/bench.py`
- [ ] T03 (AC-01, AC-02, AC-07): añadir `import re`, las expresiones y `evaluate_fixture`; `test_resumen_unittest`, `test_cero_pruebas_real` y `test_entorno_de_evaluacion` en verde.
- [ ] T04 (AC-05): en `run_cell`, usar `evaluate_fixture` en lugar del bloque actual; añadir `testsRun` a la celda y a `cell_keep`. `test_run_cell_usa_senal` puede seguir en rojo hasta T06, porque requiere los fixtures nuevos.
- [ ] T05 (AC-05): en `tests/test_bench.py:869`, hacer que el mock con `test_ok=True` devuelva `stderr='Ran 1 test in 0.001s\n\nOK\n'`; `sh .microharness/python.sh -m unittest tests.test_bench` en verde.

## GREEN: fixtures
- [ ] T06 (AC-03, AC-04, AC-05): reescribir con `TestCase` los cinco `test_fixture.py`, con el contenido exacto de `plan.md`, tarea por tarea; ajustar `fixture_mod.py` de 04 y de 05 (DEC-02); `test_rojo_y_verde` y `test_run_cell_usa_senal` en verde.
- [ ] T07 (AC-08): actualizar `fixtureSha256` en los cinco `task.json`; `test_huella_fixture` en verde. Si un valor difiere del de `plan.md`, usa el que calcule la prueba y repórtalo.
- [ ] T08 (AC-06, DEC-01): añadir `restore_fixture_test`, llamarla en `run_cell` antes de evaluar y añadir la frase al prompt; `test_prueba_manipulada_se_restaura` en verde.

## Aviso de invalidez
- [ ] T09 (AC-09, AC-10): insertar el aviso de `plan.md` en `bench/baseline/README.md`, tras el título, sin cambiar lo demás.
- [ ] T10 (AC-09, AC-10): sustituir `notes` en `bench/config.json` por el texto de `plan.md`, sin tocar otras claves; `test_aviso_baseline` en verde.
- [ ] T11 (AC-11): añadir la línea de `plan.md` a `bench/README.md` y, con DEC-02 A, cambiar `assets/eval-esfuerzo.md:17`.

## Verificación
- [ ] T12 (AC-10): `git diff --name-only a6cc163` lista solo rutas de `allowed_paths`, y bajo `bench/baseline/` solo `README.md`. `git diff a6cc163 -- bench/config.json` solo cambia `notes`. Comparar los topes con `git diff --stat`.
- [ ] T13 (AC-11): `sh .microharness/python.sh .microharness/sdd.py check bench-senal-exito --run`: `OK` con al menos 498 pruebas. Reportar cuántas líneas contó el hook, según `.microharness/rdd_runtime.json`, leído con `Read`.

## Fuera de esta tarea
La comprobación de `treatment` con una celda real (`plan.md`, «Siguiente paso») la autoriza y ejecuta el humano.
