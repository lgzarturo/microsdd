# CÓMO: diseño mínimo

## Situación comprobada
Leído y ejecutado en `0638cb7` (versión 1.5.3) y revalidado en `23cec87`, que sigue en 1.5.3. `git diff 0638cb7 23cec87` no toca `.microharness/sdd.py`, `.claude/`, `tests/test_api_publica.py`, `tests/test_sdd.py`, `assets/`, `src/` ni `pyproject.toml`, así que lo siguiente no cambia, y el prototipo no se repitió. El PR #18 toca `bench.py`, `or_proxy.py`, `bench/`, `historial/`, `tests/test_or_proxy.py` y `tests/test_ab_harness.py` (nuevo); en `metrics.py` solo cambia una línea de ayuda:
- `main()` despacha subcomandos argparse sin cargar memoria, salvo en cada función. `ValueError` y `OSError` ya terminan en `ERROR:` y código 1.
- `SDD_ALLOWED` (`.claude/hooks/pretool.py:16`) no admite subcomandos nuevos: `sdd.py symbols` se deniega a `lider`, `autor` e `implementador`. `REVIEWER_SDD_CHECK_RE` solo admite `check … --run` a `revisor`.
- Una ruta aparte, como `.microharness/symbols.py`, también se deniega: `PROTECTED_RE` coincide con `microharness`.
- `run()` niega al implementador toda ruta bajo `.claude/`, sin mirar `allowed_paths`. `lider` solo edita `docs/` y `spec/`, y `autor` solo los cuatro archivos. **Ningún agente puede aplicar el cambio del hook.**
- `tracked_files()` devuelve `[]` tanto sin repositorio como con repositorio vacío, decodifica UTF-8 estricto y lanza `FileNotFoundError` si no hay binario `git`. No sirve para distinguir los modos.
- Sin repositorio, `git ls-files -z` termina con código 128; en un repositorio recién creado, con 0 y salida vacía (ejecutado).
- `normalized_rel` rechaza rutas absolutas, `..`, espacios en los extremos y la cadena vacía, y convierte `\` en `/`.
- `FITNESS_ANALYSIS_ERRORS` ya agrupa `OSError`, `SyntaxError`, `ValueError`, `RecursionError` y `MemoryError`. `ast`, `os`, `contextlib`, `subprocess`, `json`, `Path` y `PurePosixPath` ya están importados.
- `tests/test_api_publica.py` obliga a documentar cada subcomando en la sección «API pública», en cualquier punto de ella.
- El instalador copia `sdd.py` y el hook desde `MANIFEST`: sin archivos nuevos, API-08, `installer.py` y `pyproject.toml` no cambian.
- `.microharness/config.json` no existe: `claude-opus-5-5`, `medium`, `rdd_max_lines` 500.
- Prototipo en memoria, sin escribir en el repositorio, con Python 3.14.7: 80 líneas, y salidas coherentes con AC-01, AC-02 y AC-08 sobre fuentes equivalentes, no idénticas. **Supuesto:** los formatos de `ast.unparse` de AC-01 son iguales desde 3.10; solo se ejecutó con 3.14.7.

## Decisión y justificación

**Subcomando de `sdd.py`.** Es el contrato ejecutable que ya se instala, sin ruta nueva ni cambios de manifiesto. Un script aparte tocaría API-08, `pyproject.toml` y `HARNESS_EDITABLE`, y el hook lo denegaría igual.

**En `.microharness/sdd.py`:**
1. **Constantes:** `SYMBOL_TEST_FILES`, `SYMBOL_TEST_DIRS` y `SYMBOL_NOISE_DIRS` (REQ-08, REQ-10).
2. **`_symbol_doc(node) -> dict`**, **`_symbol_callable(node) -> dict`** y **`_symbol_class(node) -> dict`**: REQ-03 a REQ-07. La firma es `f'({ast.unparse(node.args)})'` más el retorno si existe, de modo que nada se inventa.
3. **`symbols_of(data: bytes, relative: str) -> dict`:** analiza con `ast.parse` y recorre solo `body`. Deja propagar las excepciones. Es la interfaz de AC-01 a AC-03.
4. **`_symbol_excluded(relative, base) -> bool`:** aplica REQ-10 sobre `PurePosixPath(relative).relative_to(base)`, de modo que nunca ve componentes de la ruta por encima de la raíz.
5. **`_symbol_listing(base, tracked) -> list[str]`:** con `tracked`, filtra por igualdad o prefijo `base + '/'`; si es `None`, usa `os.walk`, con poda de ruido y de directorios ocultos.
6. **`symbols(paths: list[str]) -> dict`:** valida rutas, ejecuta `git ls-files -z` en bytes con `os.fsdecode`, trata `OSError` y código distinto de 0 como sin Git, y procesa la unión ordenada. El error es `getattr(e, 'strerror', None) or str(e)`, para no incluir la ruta absoluta.
7. **`main`:** `sub.add_parser('symbols').add_argument('paths', nargs='*', metavar='ruta')`, y `print(json.dumps(symbols(args.paths), separators=(',', ':')))`. El `ensure_ascii` por defecto evita fallos de codificación en la consola de Windows.

**Filtrar en Python, no con pathspec.** Una sola llamada a `git`, sin magia de pathspec como `:!x` o `*.py` en los argumentos.

**Excluir pruebas, salvo si se piden.** Los auxiliares de prueba no son superficie pública y agrandan el mapa. Se evalúa por debajo de la ruta pedida, de modo que `symbols tests` funciona en vez de dar un vacío sorprendente, y que un repositorio bajo `/x/tests/` no pierda nada.

**El ruido solo se poda sin Git.** Con Git, lo rastreado ya lo decidió el proyecto: un `src/build/x.py` rastreado se conserva.

**`source` en la salida.** El modo cambia qué archivos entran, así que debe verse. Git roto, o una raíz sin rastrear dentro de otro repositorio, no se confunde con un repositorio sin Python.

### Parche del hook (DEC-01 A; lo aplica el humano)
```diff
-SDD_ALLOWED = ('init', 'new', 'check', 'review', 'commit-check', 'note', 'release', '--version', '--help')
+SDD_ALLOWED = ('init', 'new', 'check', 'review', 'commit-check', 'note', 'release', 'symbols', '--version', '--help')
```
```diff
-            f'commit-check, note, release, --version o --help; {version_hint}; '
+            f'commit-check, note, release, symbols, --version o --help; {version_hint}; '
```
Dos líneas, fuera del contador de líneas del implementador. `check` lo acepta porque la ruta está en `allowed_paths`. `revisor` no cambia.

### `testing.fitness`: apagado
`sdd.py` tiene 1570 líneas, y una rama más en `main` empeora un valor ya fuera de límite. Activarlo exigiría subir `max_lines` por encima de 1690 y `max_complexity` por encima de la de `main`, y esos límites se aplicarían también a las funciones nuevas. La puerta pasaría casi sin comprobar nada. No funciona sin complicaciones, así que queda en `enabled: false`.

## Estimación de líneas (kill switch de 500)
Corrección por las tareas anteriores: código ×1,3 (+134 frente a ~105) y pruebas ×1,75 (322 frente a ~185).

| Archivo | Base | Con factor | Tope duro |
|---|---|---|---|
| `.microharness/sdd.py` | 83 (prototipo 80 + `main` 3) | ~108 | 120 |
| `tests/test_symbols.py` | ~115 | ~200 | 200 |
| `assets/arnes-completo.md` | ~16 | ~20 | 25 |
| `assets/proceso-versionado.md` | 3 | ~4 | 5 |
| **Total** | **~217** | **~332** | **350** |

Con el tope, quedan **150 líneas libres**, y ~168 con la estimación.

**Archivo de pruebas nuevo: `tests/test_symbols.py`.** Se crea con un único `Write`, se sella solo él (no las 2327 líneas de `tests/test_sdd.py`) y `discover` lo encuentra. Reparto de las 200 líneas: carga y `setUp` 35, doce métodos con tablas 165.

Recorte si se llega a un tope: retirar enlaces simbólicos (~6 líneas) y `async` (~5). Requiere reaprobar.

## Medición: el A/B actual compara con y sin arnés, no `symbols`
Esta tarea no corre el bench con red ni lo modifica. **Conclusión: hoy no se puede evaluar `symbols`.** Es una medición posterior, que requiere cambiar el bench y una decisión humana sobre el gasto.

### Comprobado
Por lectura de `.microharness/bench.py`, `bench/AB.md`, `bench/README.md`, `bench/config.json`, `bench/tareas/` y `tests/test_ab_harness.py` en `23cec87`, salvo lo que se indica como ejecutado:
- **Qué compara.** `bench ab` lanza `base` (solo fixture) frente a `treatment` (fixture más arnés), con el mismo `--model`. `prepare_cell_workdir` llama a `install_harness` solo en `treatment`.
- **El arnés sí se instala.** `HARNESS_FILES` incluye `CLAUDE.md`, `.claude/settings.json`, los agentes, `.claude/hooks/pretool.py`, `.microharness/sdd.py` y los lanzadores; además se crea una memoria vacía. La copia sale de la raíz del repositorio (`harness_root=ROOT`, fijo en `run_bench`).
- **Qué se verifica sin red.** `dry_run_harness_check` y `tests/test_ab_harness.py` solo comprueban archivos presentes, huellas distintas, `settings.model`, topes y contador. No lanzan ningún agente, así que no demuestran que el hook actúe en una celda real.
- **`dry-run`.** El hook denegó `metrics.py bench dry-run` al autor. Su salida se observó porque la suite, ejecutada como se pidió, incluye `test_cmd_bench_dry_run_exit_0`: `treatment preset=microsdd`, 17 archivos, `base loaded=false`, `50×5=250 < 300 (margen 50)`.
- **Qué registra.** Por celda: éxito (código de salida de `testCommand`), tokens, turnos, coste y duración. El veredicto usa éxito y eficiencia en tokens o iteraciones.
- **Sin medida de duplicación.** `dupRatio` existe, pero mide líneas repetidas en los archivos de prompt (`_file_metrics`), no código. El temporal de cada corrida se borra al terminar y `sanitize_report` no conserva diffs.
- **Fixtures sin nada que duplicar.** Las cinco tareas tienen un `fixture_mod.py` de 1 a 5 líneas y un `test_fixture.py` de 3 o 4. `list_tasks` exige exactamente 5 tareas.
- **`symbols` sin contraste propio.** Tras esta tarea, `treatment` copiaría el comando dentro de `sdd.py`, pero `base` no tiene arnés, y el prompt no depende del brazo ni lo menciona. La huella tampoco lo detecta: `PROMPT_PATHS` no incluye `sdd.py` ni el hook.
- **Éxito no fiable (ejecutado con Python 3.14.7, tareas 01 y 03, sin editar nada).** `python -B -m unittest test_fixture` da `Ran 0 tests`, `NO TESTS RAN` y código 5, también en 03, cuya aserción cumple el código. Por lectura, las cinco pruebas son funciones sueltas, sin `TestCase`, y las cinco tareas usan ese mismo comando. Con este intérprete, el código de salida no distingue un fixture corregido de uno sin corregir.
- **Tope de gasto vigente.** `bench ab` sustituye `maxRequestsPerRun` y `maxTurnsPerCell`, pero conserva `maxSpendUsd` de `bench/config.json` ($0,10), con `spendApproachRatio` 0,8: aborta cuando el gasto llega a $0,08.

### Inferido, sin ejecutar
- **Un brazo `treatment` podría no poder corregir el fixture.** La regla de `pretool.py` es clara: `lider` no edita fuera de `docs/` y `spec/`, y `implementador` necesita una spec en `proceso` con aprobación. La memoria está vacía, `copy_fixture` no copia `spec/` y hay 5 o 6 turnos por celda. Si `--dangerously-skip-permissions` respeta el hook y `settings.agent` se aplica, el brazo mediría sobre todo ese bloqueo. Ninguna de las dos condiciones está comprobada, y una sola celda real lo aclararía.
- **El éxito depende de la versión.** Las celdas con éxito de la línea base sugieren que el agente reescribió la prueba o que el intérprete era anterior a 3.12, versiones en las que `Ran 0 tests` terminaría con 0 (supuesto, no ejecutado). No se comprobó cuál fue el caso.

### Qué faltaría para evaluar `symbols`
1. Corregir antes la señal de éxito (pruebas que `unittest` recoja, con la huella `fixtureSha256` al día) y confirmar con una celda que `treatment` puede terminar la tarea.
2. Comparar `arnés` frente a `arnés + symbols`. Hoy `variant` solo admite `base` y `treatment`, y `harness_root` es fijo.
3. Dar a conocer el comando en el brazo con `symbols`. Inyectarlo en prompts queda fuera de esta spec.
4. Crear fixtures de varios módulos con un auxiliar reutilizable. Hoy hay 5 tareas fijas, también en `ab_run_dims` y en la estimación de celdas.
5. Definir una medida objetiva de duplicación, calcularla antes de borrar el temporal y añadirla a `cell_keep`.

### Coste con los topes actuales
| Concepto | Valor | Tipo |
|---|---|---|
| Celdas (N=5 × 5 tareas × 2 brazos) | 50 | leído |
| Solicitudes `deepseek` | 50×5 = 250, tope 300 | leído |
| Solicitudes `free` | 50×6 = 300, tope 500; cuota diaria ≥ 300 exigida | leído |
| Gasto de referencia | 16 celdas ≈ $0,078 y 14 celdas ≈ $0,080 (85 solicitudes), ≈ $0,0053 por celda | leído en `bench/baseline/` |
| Gasto de 50 celdas `deepseek` | ≈ $0,24 a $0,28, sin el contexto del arnés | inferido |
| Corte con `maxSpendUsd` $0,10 | hacia la celda 15 de 50, con veredicto `NO CONCLUYENTE` | inferido |
| `maxSpendUsd` para 50 celdas | más de $0,35 según esta estimación; lo decide el humano | inferido |

Los topes de solicitudes alcanzan; **el de gasto no**. Las cifras son un suelo orientativo: las celdas de referencia usaban fixtures mínimos, sin arnés y con 6 turnos. El coste adicional de `treatment` no está medido, aunque `CLAUDE.md` y `lider.md` suman unos 5,8 KB. Tampoco se cuenta el trabajo de modificar el bench, y `costUsdModelEstimate` (≈ $7,97) no es gasto facturado.

`check --run` ejecuta `tests/test_ab_harness.py`: incluye el `dry-run` sin red y copia `sdd.py` a temporales. No gasta solicitudes y no cuenta como correr el bench (T16). `.microharness/bench.py` no está en `allowed_paths` y no se modifica.

### Advertencia sobre N=3: la línea base no es evidencia
**La línea base 11/15 frente a 8/15 no compara con y sin arnés, y no se usa como evidencia de nada sobre el arnés ni sobre `symbols`.** Tampoco permite concluir si N=3 o N=5 bastan. El commit `1f3a731` dice: «Causa de baselines inválidas: treatment solo copiaba el fixture (≡ base)». `git diff ef3955f 1f3a731` lo confirma para el relleno de 14 celdas: en `ef3955f`, `run_bench` llamaba a `copy_fixture` en ambos brazos. No se comprobó el commit de las 16 celdas previas. De esa línea base solo se toma el gasto, como orden de magnitud.

**`bench/baseline/` no lo advierte.** `bench/baseline/README.md` sigue con `Estado: complete` y `Veredicto: RECHAZA`, sin aviso de invalidez; `bench/config.json` repite ese veredicto en `notes`. Una búsqueda en `bench/baseline/` de `inválid`, `equivalent`, `sin arnés`, `T-034` y `1f3a731` no encontró nada, y su último commit (`920d99d`) es anterior a `1f3a731`. Esta spec no lo edita.

## Alternativas descartadas
- **Generar `SYMBOL_MAP.json` y caché:** estado que se desfasa y más superficie, sin datos que lo justifiquen.
- **Evaluar `inspect.signature` importando módulos:** ejecuta código del proyecto.
- **Formatear la firma a mano:** repite `ast.unparse` y es otra fuente de errores.
- **Salida en texto o con sangría:** más difícil de procesar, o más grande.
- **Abortar con el primer archivo roto, o devolver código 1:** un archivo roto no debe esconder el resto del mapa.
- **`__all__` como definición de público:** requiere evaluar expresiones y más casos, sin necesidad demostrada.
- **Añadir `symbols` al revisor:** su contrato es dictaminar, y no hay necesidad observada.
- **Añadir la prueba a `tests/test_bloquear_autoaprobacion.py`:** obligaría a sellar otro archivo.

## Invariantes
- `symbols` no escribe archivos, no toma lock, no emite telemetría y no lee `memory.json`.
- `ast.parse` no ejecuta el código analizado.
- Sin invocar `symbols`, el comportamiento del resto de subcomandos es el mismo.
- Estados, roles, huellas, sellos, formato de memoria y manifiesto no cambian.

## Riesgos y efectos secundarios
- **Parche manual del hook:** `tests/test_symbols.py::test_hook` falla hasta que el humano lo aplique, y `check --run` no pasa. El implementador se detiene en T11 y lo pide por el líder.
- **Ampliación de API-05:** cambio aditivo. Los agentes pueden leer los mismos archivos con `Read`, así que no se abre acceso a datos nuevos.
- **Instalaciones:** un `sdd.py` y un hook de distinta versión darían una denegación clara, no una escalada.
- **Símbolos que el mapa no ve:** decoradores (una `@property` parece un método), `metaclass`, parámetros de tipo (PEP 695), variables de módulo, `__all__`, clases anidadas y definiciones bajo `if`/`try`. Un mapa sin un símbolo puede llevar a duplicarlo. Se documenta.
- **Exclusión por nombre:** un archivo de producción `test_utils.py` no aparece sin pedirlo de forma explícita. Se documenta.
- **Dependencia del intérprete:** la sintaxis nueva da una entrada en `errors` con un Python antiguo, y el formato de `ast.unparse` puede variar entre versiones. El determinismo se promete para el mismo árbol y el mismo intérprete.
- **Repositorio padre:** una raíz sin rastrear dentro de otro repositorio da `source: git` y `files` vacío. Es visible y se documenta.
- **Argumento que es un enlace simbólico a un directorio:** sin Git, `os.walk` lo sigue en el nivel superior, porque el humano o el agente lo pidieron por su nombre.
- **`SyntaxWarning` y `__pycache__`:** `ast.parse` puede avisar por stderr, sin afectar a stdout. Python puede crear `.microharness/__pycache__` al importar `metrics` opcionalmente; es del intérprete, no del comando.
- **Tamaño de salida:** no hay límite; no se afirma ninguna cifra de ahorro.
- **Sello:** el líder sella `tests/test_symbols.py` tras RED. Corregirlo después exige resellar, y reducir aserciones, la nota `seal-reduce`.
- **Kill switch:** cada reedición suma al contador. Si el hook rechaza, se detiene y reporta, sin fragmentar.
- **Revisión:** el hook niega `grep` sobre rutas con `sdd.py`. AC-13 y AC-14 se revisan por `git diff` o `Read`.
- **`assets/decisiones-diseno.md`:** D-05 y D-14 siguen vigentes; `D-14` no se ve afectada porque no se añade comparador de benchmarks.
