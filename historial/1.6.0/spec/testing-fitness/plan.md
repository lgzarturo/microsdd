# CÓMO: diseño mínimo

## Situación comprobada
Leído y ejecutado en el árbol actual (versión 1.5.3, `4f4ac1a`):
- `validate(slug, run, scope)` trata `testing.mutation` con `.get`, sin validar tipos salvo el comando, y `min_tests` con `type(x) is not int or x < 1`. La lista blanca solo se aplica `if s.get('state') != 'terminado'`.
- `approve spec` llama a `validate(slug, scope=False)`; `approve close` llama a `validate(slug, run=True)`, con alcance. `check --no-scope` pasa `scope=False`. Los comandos solo corren `if run and not errors`.
- `diff_files()` da `git diff --name-only -z HEAD` más no rastreados, ordenados, e incluye borrados. Sin repositorio devuelve `[]`; sin commits, solo los no rastreados.
- `path_allowed(rel, patterns)` usa `PurePosixPath.match`, que compara por sufijo si el patrón es relativo (`x.py` coincide con `src/x.py`), más el prefijo de `/**`. Por eso `protected_tests` no debe pasar por ella.
- `git()` decodifica UTF-8, inadecuado para fuentes con otra codificación; `count_assertions` hace `ast.parse(target.read_bytes(), filename=relative)` y convierte `SyntaxError`, `ValueError`, `RecursionError` y `MemoryError` en `ValueError`. `ast` ya está importado.
- `spec_fingerprint` cubre todo `spec.json` salvo `state`: subir un límite tras aprobar ya exige reaprobar, sin código nuevo.
- `.microharness/config.json` no existe, así que rigen los valores por defecto (`claude-opus-5-5`, `medium`, `rdd_max_lines` 500).
- `estimate_edit_lines` en `.claude/hooks/pretool.py` suma por cada `Edit` el máximo de líneas nuevas y antiguas, y por cada `Write` todo el contenido. Las reediciones acumulan.
- Por lectura, sin ejecutar la medida: `sdd.py` tiene 1437 líneas, `validate` queda muy por encima de complejidad 10 y `note` tiene 8 parámetros.
- Ninguna prueba fija la plantilla completa de `testing` (búsqueda de `mutation` en `tests/`).
- Supuesto no releído en esta tarea: `src/microsdd/` no requiere cambios porque el instalador copia `sdd.py`, según el plan de `seal-monotonico`.

## Decisión y justificación

**Campo opcional en `spec.json`, comprobado en `validate`.** En `.microharness/sdd.py`:

1. **Constantes:**
   ```python
   FITNESS_DEFAULTS = {'max_params': 4, 'max_complexity': 10, 'max_lines': 250}
   FITNESS_TEST_PATTERNS = ('test_*.py', '*_test.py', 'conftest.py', 'tests/**')
   ```
2. **Plantilla de `new`:** `'fitness': {'enabled': False, **FITNESS_DEFAULTS}`.
3. **`fitness_config_errors(fitness: object) -> list[str]`:** los mensajes de AC-03. Claves admitidas: `enabled`, los tres límites y `test_patterns`.
4. **`measure_python(data: bytes) -> tuple[int, list[tuple[int, str, int, int]]]`:** devuelve `(líneas, [(línea, nombre, parámetros, complejidad), …])` en orden de línea, aplicando REQ-05 y REQ-06. Es la interfaz que usan las pruebas de AC-05, AC-06 y AC-07; deja propagar las excepciones de análisis, que convierte quien la llama. Un recorrido recursivo con pila de nombres; `_complexity` desciende con `ast.iter_child_nodes` y no entra en `FunctionDef`/`AsyncFunctionDef`.
5. **`fitness_errors(spec: dict) -> list[str]`:** filtra `diff_files()` según REQ-07, lee el archivo y la versión de `HEAD`, y aplica la regla de `HEAD`. La versión de `HEAD` se pide con `subprocess.run(['git', 'show', f'HEAD:{rel}'], capture_output=True)` para tener bytes; un código distinto de 0 significa sin base. `protected_tests` se compara con `normalized_rel`, de forma literal; una ruta insegura propaga el `ValueError` que `main` y `approve` ya informan.
6. **En `validate`:** dentro del bloque `!= 'terminado'`, si `'fitness' in testing`, añadir `fitness_config_errors`. Después del bucle de alcance y antes de `if run and not errors`: `if scope and patterns and state != 'terminado'` y configuración válida, añadir `fitness_errors(s)`.

**Valores por defecto (4, 10, 250).** La propuesta de la idea original. Un `enabled: true` sin límites queda útil y la plantilla los muestra para que se editen.

**Compatibilidad.** Sin campo equivale a desactivado: las specs antiguas no cambian de huella ni de resultado. Las tareas `terminado` no se validan, igual que la lista blanca.

**`enabled` obligatorio y claves desconocidas como error.** Un `{"max_param": 3}` no debe dejar la puerta apagada, o con el valor por defecto, en silencio: una errata debilitaría el control sin que nadie lo vea.

**Identificación de pruebas.** `protected_tests` literal más patrones. Solo `protected_tests` trataría como código un auxiliar de pruebas no sellado. `test_patterns` es el mínimo configurable y vive en la spec aprobada, de modo que ampliarlo pasa por la huella.

**Medir con `HEAD` como base (DEC-01, opción A).** La comparación por nombre cualificado es lo más simple que permite tocar `sdd.py` sin subir el límite a 1437 para todos. Crecer exige subir el límite en la spec, lo que el humano ve al reaprobar.

**`--no-scope` y `approve spec` no evalúan.** La puerta depende del diff, igual que el alcance. El cierre sí pasa por ella: `approve close` usa `validate(run=True)`. Así una reaprobación a mitad de tarea no queda bloqueada por una violación aún sin corregir.

## Estimación de líneas (kill switch de 500)

| Archivo | Líneas | Detalle |
|---|---|---|
| `.microharness/sdd.py` | ~105 | constantes 3, plantilla 1, config 18, medidas 40, `fitness_errors` 35, `validate` 8 |
| `tests/test_sdd.py` | ~185 | `setUp` y auxiliares 30; tablas de AC-05 y AC-06, 45; el resto, 110 |
| `assets/arnes-completo.md` | ~25 | ejemplo 6, subsección 18, fila 1 |
| `assets/proceso-versionado.md` | ~2 | API-02 |
| **Total** | **~317** | **margen ~180 para correcciones** |

Cabe sin recortar alcance, a condición de:
- Añadir las pruebas en una sola edición de `tests/test_sdd.py`, con tablas y `subTest`, y fuentes de una línea; generar complejidad y líneas con un auxiliar (`'    if a: pass\n' * n`), no con literales.
- Como referencia, la tarea anterior usó 416 líneas de pruebas para 19 AC, porque cada caso era un método; aquí son unos 15 métodos.
- Si `tests/test_sdd.py` superara 240 líneas, hay que parar y reportarlo. El recorte previsto es retirar `test_patterns` (unas 12 líneas entre código y pruebas), lo que requiere reaprobar.

## Alternativas descartadas
- **Comando o configuración de proyecto en `memory.json`:** la puerta es por tarea, como `mutation`.
- **Depender de `radon`, `mccabe` o similares:** contra D-05. Además, sus conteos cambian entre versiones; aquí el conteo lo fija la spec.
- **Ejecutar como comando en `testing.commands`:** obligaría a añadir un runner a la lista blanca y dejaría la puerta fuera de `check` sin `--run`.
- **Línea de archivo como `:<límite + 1>`:** no aporta frente a `:1`.
- **Base en el recibo RDD:** guarda hashes, no contenidos, así que no permite medir.
- **Excepciones por función en la spec:** más superficie que subir un límite; se añadiría si aparece la necesidad.
- **Nueva capa o módulo `fitness.py`:** una ruta instalada más tocaría API-08 sin ganancia; `sdd.py` ya es el contrato ejecutable.

## Invariantes
- Sin `testing.fitness` o con `enabled: false`, `validate` da el mismo resultado que antes y no invoca a Git para esta puerta.
- `ast.parse` no ejecuta el código evaluado.
- Tres estados, roles, hook, huellas, sello y formato de memoria no cambian. `memory.json` no se escribe.
- `fitness_errors` no modifica el árbol ni el índice.

## Riesgos y efectos secundarios
- **La base es `HEAD`:** un commit intermedio de la tarea mueve la base, y a partir de él la violación ya confirmada no se detecta. Es el mismo límite del control de alcance («empieza con working tree limpio») y el líder confirma tras el cierre. Se documenta.
- **Renombrar o mover cuenta como nuevo:** una función de complejidad 12 renombrada, o un archivo movido, falla. Salida: subir el límite. Se documenta.
- **Nombres repetidos:** la base es el máximo, así que una redefinición nueva puede pasar por debajo de él (fila de AC-10). Se documenta.
- **Patrón `tests/**` por sufijo:** `path_allowed` también hace coincidir `pkg/tests/a.py`, pero no `pkg/tests/x/a.py`. Y `test_*.py` excluye un archivo de producción con ese nombre. Se documenta; se corrige con `test_patterns`.
- **`SyntaxWarning`:** `ast.parse` puede imprimir avisos de escapes inválidos en stderr; no se silencian, igual que en `seal`.
- **Sello y resellado:** el líder sella `tests/test_sdd.py` tras RED. Corregirlo requiere resellar, y bajar aserciones exige la nota `seal-reduce`. El sello cuenta aserciones, y las tablas con `subTest` tienen pocas por caso; no es un problema, pero reducirlas sí lo es.
- **Kill switch:** si el hook rechaza por `rdd_max_lines`, el implementador se detiene y reporta. No fragmenta ediciones para seguir, tal como consta en `project.discoveries` de la tarea anterior.
- **Verificación del revisor:** el hook niega `grep` sobre rutas que contengan `sdd.py` a los agentes; las pruebas y `check --run` cubren los AC, salvo AC-17 y AC-18, que se revisan por lectura o con `git diff`.
- **Compatibilidad API:** `testing.fitness` es un campo aditivo en API-02. No se cambia `__version__`: lo decide el proceso de versión.
- **`assets/decisiones-diseno.md`:** D-05, D-09 y D-10 siguen siendo ciertas. No se añade decisión nueva; es opcional para el humano.
