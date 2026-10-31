# QUÉ: requisitos

## Objetivo
Que el resultado del bench signifique algo:

1. **Señal de éxito.** En las cinco tareas, un fixture sin corregir da FALLO y uno corregido da ÉXITO, de forma determinista y comprobada sin red. Cero pruebas ejecutadas nunca cuenta como éxito.
2. **Aviso de invalidez.** `bench/baseline/README.md` y `notes` de `bench/config.json` dicen que ese baseline no es evidencia sobre MicroSDD. Los datos históricos no se tocan.

## Precondiciones
- PRE-01: rama `fix/bench-senal-exito`, sobre `a6cc163`.
- PRE-02: suite en verde: 490 pruebas, 4 omitidas (`sh .microharness/python.sh -m unittest discover -s tests`, ejecutado con Python 3.14.7).
- PRE-03: DEC-01, DEC-02 y DEC-03 de `plan.md` resueltas por el humano al aprobar la spec. Los requisitos marcados con DEC están redactados con la opción recomendada; si el humano elige otra, el autor ajusta la spec antes de aprobarla.

## Requisitos EARS
- REQ-01: WHEN el bench evalúa una celda, THE bench SHALL marcarla como éxito solo si el comando de prueba termina con código 0 y el resumen de `unittest` indica al menos una prueba ejecutada y pasada.
- REQ-02: IF el resumen indica 0 pruebas, todas omitidas o solo fallos esperados, o no hay resumen, THEN el bench SHALL marcar la celda como no exitosa, con cualquier código de salida y cualquier versión de Python.
- REQ-03: WHEN el fixture de cualquiera de las cinco tareas está sin corregir, en cualquiera de los dos brazos, THE evaluación SHALL dar FALLO con al menos una prueba recogida.
- REQ-04: WHEN `fixture_mod.py` se sustituye por su versión corregida de `plan.md`, en cualquiera de los dos brazos, THE evaluación SHALL dar ÉXITO.
- REQ-05 (DEC-01): WHEN termina el agente de una celda, THE bench SHALL restaurar `test_fixture.py` desde la tarea antes de evaluar, de modo que editar la prueba no produzca éxito.
- REQ-06: WHEN el comando empieza por `python` o `python3`, THE bench SHALL ejecutarlo con el intérprete que corre el bench y sin escribir bytecode.
- REQ-07 (DEC-03): WHEN el bench ejecuta el comando de prueba, THE entorno del subproceso SHALL NOT contener las claves de `SECRET_ENV_KEYS`.
- REQ-08: THE celda SHALL registrar `testsRun`, también en el reporte sanitizado.
- REQ-09: THE `fixtureSha256` de cada `task.json` SHALL coincidir con los archivos de su fixture.
- REQ-10: THE `bench/baseline/README.md` y `notes` de `bench/config.json` SHALL avisar, con los textos de `plan.md`, que los brazos eran equivalentes y que el veredicto no es evidencia sobre MicroSDD.

## Criterios de aceptación
Salvo AC-08 a AC-10, se comprueban en `tests/test_bench_senal.py`, con `urllib.request.urlopen` parcheado para fallar si se invoca.

- AC-01 (REQ-01, REQ-02, REQ-06): `evaluate_fixture` con `subprocess.run` simulado devuelve:

  | Código | stderr | `ok` | `testsRun` |
  |---|---|---|---|
  | 0 | `Ran 0 tests in 0.000s`, `OK` (Python anterior a 3.12) | `False` | 0 |
  | 5 | `Ran 0 tests in 0.000s`, `NO TESTS RAN` | `False` | 0 |
  | 0 | `Ran 1 test in 0.000s`, `OK (skipped=1)` | `False` | 1 |
  | 0 | `Ran 1 test in 0.000s`, `OK (expected failures=1)` | `False` | 1 |
  | 0 | `Ran 2 tests in 0.000s`, `OK (skipped=1, expected failures=1)` | `False` | 2 |
  | 0 | `Ran 2 tests in 0.000s`, `OK (skipped=1)` | `True` | 2 |
  | 0 | `Ran 1 test in 0.000s`, `OK` | `True` | 1 |
  | 1 | `Ran 1 test in 0.000s`, `FAILED (failures=1)` | `False` | 1 |
  | 0 | vacío | `False` | 0 |

  `OSError` y `subprocess.TimeoutExpired` dan `ok=False`, `testsRun=0`. El primer elemento del comando recibido por `subprocess.run` es `sys.executable`.
- AC-02 (REQ-02): con un `test_fixture.py` real de funciones sueltas, sin `TestCase`, `evaluate_fixture` real da `ok=False`, `testsRun=0`.
- AC-03 (REQ-03): para las cinco tareas y los brazos `base` y `treatment`, tras `prepare_cell_workdir` sin editar nada, `evaluate_fixture` real da `ok=False` y `testsRun>=1`.
- AC-04 (REQ-04): sobre esos mismos directorios, tras escribir `CORREGIDO[task_id]` en `fixture_mod.py`, da `ok=True` y `testsRun>=1`.
- AC-05 (REQ-01, REQ-08): `ClaudeCodeProvider.run_cell`, con Claude simulado y el comando de prueba real, da `success=False`, `status='fail'` si el fixture no cambia, y `success=True`, `status='ok'` si el agente simulado escribe la versión corregida. `testsRun` aparece en la celda y sobrevive a `sanitize_report`.
- AC-06 (REQ-05, DEC-01): si el agente simulado sustituye `test_fixture.py` por una prueba trivial que pasa, `run_cell` da `success=False` y el archivo del directorio de trabajo vuelve a ser idéntico al de la tarea.
- AC-07 (REQ-06, REQ-07, DEC-03): el `env` recibido por `subprocess.run` en la evaluación no contiene ninguna clave de `SECRET_ENV_KEYS` definida en el entorno y tiene `PYTHONDONTWRITEBYTECODE=1`.
- AC-08 (REQ-09): una prueba recalcula `sha256` de `fixture_mod.py` seguido de `test_fixture.py` y coincide con `fixtureSha256` en las cinco tareas.
- AC-09 (REQ-10): una prueba comprueba que `bench/baseline/README.md` empieza su contenido, tras el título, con el aviso y que este y `notes` contienen `1f3a731`, `eb3d43e`, `ef3955f` y `no es evidencia sobre MicroSDD`.
- AC-10: `git diff --name-only a6cc163` no muestra, bajo `bench/baseline/`, nada salvo `README.md`. En `bench/config.json` solo cambia `notes`: `maxSpendUsd`, `maxRequestsPerRun`, `maxTurnsPerCell` y `baselineStatus` quedan iguales. Las rutas cambiadas están todas en `allowed_paths`.
- AC-11: `sh .microharness/python.sh .microharness/sdd.py check bench-senal-exito --run` termina en `OK`, con al menos 498 pruebas y sin ejecutar el bench con red.

## Fuera de alcance
- Correr el bench con red, incluida la comprobación de `treatment`.
- Subir `maxSpendUsd` u otros topes.
- Regenerar el baseline, o borrar o reescribir sus datos históricos.
- Cambiar cómo se instala el arnés en `treatment` (`install_harness`, `HARNESS_FILES`, `prepare_cell_workdir`).
- Fijar si `treatment` puede terminar una tarea. Queda descrito en `plan.md` como siguiente paso, y requiere autorización de gasto del humano.
- `symbols` o fixtures multimódulo. Medir duplicación. Estados, roles o motor nuevos.
- Cambiar `baselineStatus`, el cálculo del veredicto, `FakeProvider` o los workflows.
