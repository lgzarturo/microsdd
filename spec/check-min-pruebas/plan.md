# CÓMO: diseño mínimo

## Situación comprobada

Hechos verificados en el repositorio (HEAD `ffe55d6`):

- `validate()` en `.microharness/sdd.py` ejecuta, con `run=True` y sin errores previos, `testing['commands']` y `mutation['command']` (si `enabled`). Usa `subprocess.run(command, cwd=ROOT, check=False, timeout=300)` sin capturar la salida y solo añade un error si `returncode != 0`. Antes sustituye `python`/`python3` en la primera posición por `sys.executable`.
- `approve(..., 'close')` llama a `validate(slug, run=True)` con la tarea en `proceso`, así que la puerta de cierre hereda el cambio.
- `testing.min_tests` no existe en ninguna `spec/*/spec.json` ni en `new()`.
- `testing.commands` de las specs existentes:
  - Todas, salvo tres, usan solo `["python","-m","unittest","discover","-s","tests"(,"-v")]`.
  - `fundamentos-diseno` y `proceso-versionado` (`terminado`) añaden un `["python","-c", ...]` que imprime `OK estructura`.
  - `herramienta-release` (`terminado`) añade `["python",".microharness/sdd.py","--version"]` y un `python -c` que imprime `OK docs`.
  - Ninguno de esos comandos muestra un recuento reconocible.
- `tests/test_sdd.py`:
  - `MicroSDDTests.setUp` usa `[sys.executable, '-c', 'print("tests ok")']` como suite.
  - Las pruebas que llegan a `approve close` dependen de ese fixture: `test_lifecycle_review_close` y `test_sealed_tests_ignored_after_close`.
  - `test_run_replaces_python_alias_with_current_interpreter` usa `[alias, '-c', code]` y comprueba `validate(..., run=True) == []`. Con el recuento fallaría.
  - `test_testing_failure_is_reported` usa `-c 'raise SystemExit(1)'`. Seguiría pasando, porque el código de salida distinto de 0 ya produce `Comando falló`.
  - Varias pruebas crean `ROOT/tests/` con `mkdir(parents=True)` sin `exist_ok`. Por eso el nuevo fixture no puede vivir en `tests/` y se pone en `pruebas/`.
- Con Python 3.14 local, `python -m unittest --help` sale con 0 sin la línea `Ran`. `discover` sobre un directorio vacío imprime `Ran 0 tests` y sale con 5 («NO TESTS RAN», desde 3.12). En 3.10 y 3.11 sale con 0.
- La salida de la propia suite (`-v`) incluye en stderr el resumen final `Ran N tests in`. Las pruebas internas que ejecutan `validate(run=True)` pueden volcar líneas `Ran 1 test` anidadas antes del resumen.
- Decisión humana registrada: «La lista blanca de comandos de prueba se valida solo mientras la tarea no esté `terminado`».
- Referencia no confiable: el parche externo (base `b19fe30`) propone `tests_ran` con suma por patrón, exigencia por comando, captura con `encoding='utf-8'` y reescritura con `sys.stdout.write`. Se adapta según se indica abajo.

## Decisión y justificación

Cambio mínimo en `.microharness/sdd.py`, sin capas nuevas:

1. **Constante y función de recuento.** Añadir `TEST_COUNT_RES`, una tupla de regex compiladas para unittest, pytest, bun y Maven, y una regex de líneas Go (`^ok\s+\S+`, multilínea). Añadir `tests_ran(output) -> int | None`:
   - Para los resúmenes numéricos, toma la **última** coincidencia de cada patrón.
   - Para Go, cuenta las líneas.
   - Devuelve el máximo entre los patrones que coincidan, o `None` si no coincide ninguno.
   - Se elige la última coincidencia y no la suma del parche externo por dos motivos. Las salidas anidadas, como la de esta suite, inflarían la suma. En Maven, la línea `Results: Tests run: N` repite el total por clase.
2. **Validación de `min_tests`.** En el bloque `testing` de `validate`: `min_tests = testing.get('min_tests', 1)`. Si `type(min_tests) is not int or min_tests < 1`, se añade el error de REQ-09. Usar `type(...) is int` excluye `bool`, igual que ya hace `max_iterations`.
3. **Ejecución.** En el bucle de `run`:
   - Marcar qué comandos se cuentan: los de `testing.commands` sí, el de mutación no.
   - Ejecutar con `capture_output=True` en bytes y reproducir stdout y stderr con un helper pequeño (`echo(data, stream)`). Si `stream` tiene `buffer`, hace `flush()` y escribe los bytes; si no, escribe `data.decode('utf-8', 'replace')`.
   - Si `returncode == 0`, el comando se cuenta y `s.get('state') != 'terminado'`: calcular `tests_ran` sobre stdout y stderr decodificados (`'utf-8', 'replace'`) y comparar con `min_tests`.
   - Reproducir bytes evita el `UnicodeEncodeError` que provocaría `sys.stdout.write` de texto con `U+FFFD` en consolas o pipes cp1252 de Windows, donde está comprobado el flujo del repositorio. También conserva la salida que el usuario veía antes.
4. **Fixtures de pruebas** (sin tocar aserciones):
   - `MicroSDDTests.setUp` crea `ROOT/pruebas/test_ok.py`, un `unittest.TestCase` con una prueba que pasa, y usa `[sys.executable, '-m', 'unittest', 'discover', '-s', 'pruebas']`.
   - `test_run_replaces_python_alias_with_current_interpreter` escribe `pruebas/test_alias.py`, cuya prueba guarda `sys.executable` en el archivo esperado, y usa `[alias, '-m', 'unittest', 'discover', '-s', 'pruebas']`. La aserción `== []` y la del contenido del archivo no cambian.
   - `test_testing_failure_is_reported` se deja igual (ver D-03).
5. **README.** Ampliar el párrafo de la línea 41 (o uno contiguo) con `min_tests` y los runners reconocidos, y actualizar la fila «Tests y mutación» de la tabla de garantías. Opcionalmente, mostrar `"min_tests": 1` en el ejemplo de `spec.json`.
6. **`docs/arquitectura.md`.** Lo actualiza el líder al cierre, no el implementador.

### Decisiones abiertas (con recomendación)

- **D-01. Agregación con varios comandos.** Recomendación: **por comando**. Cada comando de `testing.commands` debe mostrar un recuento de al menos `min_tests`.
  - Es fail-closed y simple: no hay estado agregado, y un comando sin pruebas no se esconde detrás de otro.
  - Coincide con el parche de referencia.
  - Los únicos comandos actuales sin recuento están en tareas `terminado`, que quedan exentas (REQ-08).
  - La tarea siguiente (R6, lista blanca) rechazará de todos modos `python -c` y scripts sueltos en tareas activas, así que la alternativa permisiva no aportaría nada duradero.
  - Coste: las verificaciones estructurales de documentos, que hoy se escriben como `python -c`, deberán ir como pruebas unittest dentro de `tests/`. Con varios runners heterogéneos (por ejemplo, Go cuenta paquetes), `min_tests` alto puede ser difícil de cumplir. Se documenta que el mínimo es por comando.
  - Alternativa descartada: «al menos un comando cumple el mínimo y los demás pueden no tener recuento». Es más permisiva y requiere estado agregado, y deja pasar comandos no-op.
- **D-02. Validar el tipo de `min_tests` también en `terminado`.** Recomendación: **sí, siempre**. Es una validación de esquema del propio campo, no de los comandos. Ninguna spec existente tiene la clave, así que no rompe nada. Una spec cerrada con `min_tests` inválido sería un JSON corrupto. Si el líder prefiere aplicar la decisión humana al pie de la letra, basta con condicionarla también a `state != 'terminado'`.
- **D-03. `test_testing_failure_is_reported`.** Recomendación: **no tocarlo** en esta tarea. Sigue pasando (AC-08) y R6 lo adaptará cuando rechace `-c`. Cambiarlo ahora sería trabajo no requerido.
- **D-04. Cobertura de formatos.** Recomendación: aceptar las limitaciones y documentarlas:
  - Go cuenta paquetes `ok`, no pruebas.
  - En Maven multimódulo, la última línea `Tests run:` solo refleja el último módulo, lo que subcuenta (es conservador).
  - pytest usa la última línea `N passed`.

### Alternativas descartadas

- `sys.stdout.write(outcome.stdout)` con `encoding='utf-8'`, como el parche: falla en Windows con salida no representable en la página de códigos.
- `text=True` con la codificación local: decodifica mal la salida UTF-8 de bun y Go.
- `tee` en tiempo real con hilos: más complejo. Mostrar la salida al terminar cada comando basta para el objetivo.
- Sumar coincidencias: infla el recuento con salidas anidadas y con Maven.
- Configurar los patrones por proyecto en `spec.json`: no se ha pedido (YAGNI).

## Invariantes y riesgos

Invariantes:

- Sin cambios en la interfaz CLI: los mismos argumentos y el mismo mensaje `OK:`. Códigos de salida: 1 si hay errores.
- `validate` sigue ejecutando comandos solo si no hay errores previos.
- `shell=False`, timeout de 300 s, `cwd=ROOT` y sustitución `python`/`python3` → `sys.executable` intactos.
- El recuento nunca convierte en éxito un comando que falló.
- Las tareas `terminado` no cambian de resultado en `check --run`.
- Solo biblioteca estándar.

Riesgos y efectos secundarios:

- La salida ya no se ve en tiempo real: con suites largas no se ve nada hasta que terminan. Si un comando agota el timeout, su salida no se muestra. Se acepta.
- Un runner con resumen no reconocido (Gradle, Jest, `cargo test`, etc.) hace fallar la puerta en tareas activas. Es intencional: fail-closed y documentado.
- Un comando puede imprimir un resumen falso. Lo mitiga parcialmente R6; aquí queda fuera de alcance.
- Las specs futuras que quieran comprobaciones `python -c` deberán expresarlas como pruebas. Afecta al proceso de tareas de documentación.
- Si se llama a `validate(run=True)` dentro de las pruebas, los procesos hijo escriben `Ran 1 test` en el stderr de la suite externa. No altera el recuento de la suite externa, porque se toma la última coincidencia, que es el resumen final.
- Hay más memoria por la captura (salida completa en RAM). Es aceptable para suites de pruebas.
