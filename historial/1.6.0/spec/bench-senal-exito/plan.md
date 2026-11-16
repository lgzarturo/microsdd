# CÓMO: diseño mínimo

## Situación comprobada

### Cómo se calcula el éxito
`ClaudeCodeProvider.run_cell` ejecuta `testCommand` con el `python` del PATH y fija `test_ok = returncode == 0`; `success` y `status` salen de ahí. `aggregate_report` solo cuenta `success`. `FakeProvider` no ejecuta nada: `bench run --provider fake` no prueba esta señal.

### Las cinco tareas, sin editar nada (ejecutado)
Comando: `-m unittest test_fixture`. «Aserción» es el resultado de llamar directamente a la función de prueba.

| Tarea | 3.14.7, 3.13.15, 3.12.14 | PyPy 3.11.15 | Aserción |
|---|---|---|---|
| 01 | `Ran 0 tests`, código 5 | `Ran 0 tests`, `OK`, código 0 | falla |
| 02 | `Ran 0 tests`, código 5 | `Ran 0 tests`, `OK`, código 0 | falla (`NotImplementedError`) |
| 03 | `Ran 0 tests`, código 5 | `Ran 0 tests`, `OK`, código 0 | **ya pasa** |
| 04 | `Ran 0 tests`, código 5 | `Ran 0 tests`, `OK`, código 0 | **ya pasa** |
| 05 | `Ran 0 tests`, código 5 | `Ran 0 tests`, `OK`, código 0 | **ya pasa** |

- Las cinco pruebas son funciones sueltas sin `TestCase`. El código de salida no distingue un fixture corregido de uno sin corregir: desde 3.12 todo falla; antes, todo tendría éxito. No hay CPython anterior a 3.12 en esta máquina: el caso se observó con PyPy 3.11.
- Una suite solo con omisiones o fallos esperados sale con código 0 en las cuatro versiones (ejecutado): tampoco basta con exigir `Ran N>0`.
- Los fixtures no han cambiado desde `b752e73`.

### Baseline (comprobado)
| Hecho | Cómo se comprobó |
|---|---|
| Las 16 celdas previas corrieron en `eb3d43e`; el relleno de 14, en `ef3955f` | `gh run view` de 39802356050 y 39878723841 (`headSha`) |
| En esos commits, `run_bench` llama a `copy_fixture` para ambos brazos, y `_prompt` y `run_cell` no usan `variant` | lectura de `git show eb3d43e:.microharness/bench.py` |
| `bench.py` es idéntico en ambos commits | `git diff --stat eb3d43e ef3955f` no lo lista |
| Los dos workflows fijan Python 3.12 | lectura de ambas versiones de `bench-baseline.yml`; no se leyeron los registros de ejecución |
| Con 3.12.14, las cinco tareas sin editar dan código 5 | ejecutado |

**La equivalencia queda confirmada en las 30 celdas**, no solo en las 14 del relleno. La señal tampoco era fiable.

**Inferido, no observado:** con 3.12, las 19 celdas con éxito (11 + 8) exigen que el agente alterara algo para que `unittest` recogiera pruebas, probablemente `test_fixture.py`. Por eso un éxito tampoco indica que la lógica se corrigiera. Los diffs no se conservaron.

### Interacción de `treatment` con la señal
- **El comando no cambia de resultado por el arnés (por lectura).** `-m unittest test_fixture` carga un módulo por nombre, sin descubrimiento, y `HARNESS_FILES` no incluye `test_fixture.py`, `fixture_mod.py` ni `unittest.py`. AC-03 y AC-04 lo comprueban en los dos brazos. No se ejecutó con el arnés copiado: el hook lo impide al autor.
- **La evaluación corre fuera de Claude**, así que el hook no le afecta.
- **La señal corregida puede dejar a `treatment` sin éxitos (por lectura, no ejecutado).** En el directorio de `treatment` no hay `spec/` y la memoria está vacía. `pretool.py` deniega editar `fixture_mod.py` a `lider` («no modifica código»), a `implementador` (exige una spec en `proceso`) y a un agente sin rol. Si el hook se aplica con `--dangerously-skip-permissions`, un `RECHAZA` futuro podría medir ese bloqueo y no la calidad del arnés. Por eso la comprobación de abajo debe hacerse antes de cualquier corrida completa.

### Dependencias de los archivos que cambian
- **`notes`:** ni el código ni las pruebas lo leen (`load_config` lo copia y nadie lo usa). El `'notes'` de `aggregate_report` es otro campo, del reporte.
- **`bench/baseline/README.md`:** no lo lee ningún código. `assets/eval-esfuerzo.md:4` solo lo enlaza.
- **`baselineStatus`:** `test_bench_config_json_declares_budget` exige `complete`; no se toca. Los reportes futuros seguirán copiando ese valor: es un defecto menor que queda sin resolver.
- **`fixtureSha256`:** ningún código ni prueba lo lee. Es `sha256(fixture_mod.py + test_fixture.py)`, comprobado en las cinco tareas. Se actualiza para no dejarlo falso.
- **`tests/test_bench.py`:** ninguna prueba afirma `success=True` con el mock `_run_claude`; con la señal nueva ese mock, con stderr vacío, daría fallo aunque `test_ok=True`. Se ajusta esa línea para que no mienta.
- **Pruebas que no se ven afectadas:** ninguna depende del contenido de los fixtures. `test_list_tasks_five` y `dry_run_harness_check` no los leen más allá de copiarlos.

### Otros documentos que afirman el veredicto
`git grep` de `11/15`, `8/15` y similares, sin `historial/` ni archivos `archive-*`:
- **Se corrigen:** `bench/config.json` y `bench/baseline/README.md`.
- **Se conservan como datos históricos, cubiertos por el aviso:** `bench/baseline/bench-report.sanitized.*`, `fill-pending-2026-10-23/*`, `request-estimate.md:12`.
- **No lo presentan como evidencia:** `tests/test_bench.py:710` (dato de prueba de formato), `assets/eval-esfuerzo.md`, `README.md`, `docs/`, `CHANGELOG.md`.
- **Queda desfasado:** `spec/symbol-map/plan.md:113-115` dice que no se comprobaron las 16 celdas y que `bench/baseline/` no avisa. Es otra spec y no se toca aquí; lo decide el líder.

### Hook
- `.microharness/bench.py` está en `HARNESS_EDITABLE`: el implementador puede editarlo si está en `allowed_paths`. Solo por lectura: no hay prueba que lo cubra. `assets/arnes-completo.md:136` no lo menciona y está desfasado.
- `bench/`, `assets/` y `tests/` no tienen bloqueo propio. **No hay bloqueo.**
- Efecto práctico: `Write` sobre un archivo existente y `Edit` con `old_string` de 80 % o más del archivo se deniegan. Los fixtures son diminutos, así que `tareas.md` indica ediciones parciales. Solo `tests/test_bench_senal.py` se crea con `Write`.

## Decisión y justificación
Un helper en `bench.py`, las pruebas de los fixtures reescritas con `TestCase` y el aviso. Sin capas nuevas.

### Interfaz
```python
def evaluate_fixture(test_cmd: list[str], workdir: Path) -> dict:
    """{'ok': bool, 'testsRun': int}. Usa stderr de unittest; solo el último resumen cuenta."""

def restore_fixture_test(task: dict, workdir: Path) -> None:
    """Copia <task _dir>/fixture/test_fixture.py al workdir. No hace nada si la tarea no tiene _dir."""
```

Reglas de `evaluate_fixture`:
- Sustituye `python` o `python3` por `sys.executable`, como `check --run`.
- `env`: `os.environ` sin `SECRET_ENV_KEYS` (DEC-03), con `PYTHONDONTWRITEBYTECODE=1`. Mantiene `timeout=60`, `capture_output`, `text=True`, y añade `errors='replace'`.
- `testsRun` = N de la última línea `^Ran (\d+) tests? in`, o 0.
- Pasadas = `testsRun` menos `skipped=` y `expected failures=` de la última línea `^OK(?: \((.*)\))?$`; 0 si no hay línea `OK`.
- `ok` = código 0 y pasadas >= 1.

En `run_cell`: `restore_fixture_test` (DEC-01) y `evaluate_fixture` sustituyen al bloque `try/except` actual; `test_ok = result['ok']`; se añade `'testsRun'` al diccionario devuelto y a `cell_keep`. Con DEC-01, `_prompt` añade: `Do not edit test_fixture.py: it is restored before evaluation.`

### Cómo se fija el fixture «corregido»
Con una tabla `CORREGIDO`, id de tarea a contenido exacto de `fixture_mod.py`, dentro de `tests/test_bench_senal.py`. Queda sellada con la prueba. Un fixture corregido es la copia de `bench/tareas/<id>/fixture/` con `fixture_mod.py` sustituido por ese contenido y `test_fixture.py` intacto. El agente no la ve, porque `copy_fixture` solo copia `fixture/`.

### Contenido de las tareas
Prototipo ejecutado con 3.14.7, 3.13.15, 3.12.14 y PyPy 3.11.15: rojo con código 1 y verde con código 0 en las cinco, y las nueve filas de AC-01 dan lo esperado.

**`test_fixture.py`** (sin línea en blanco al final):

01:
```python
import unittest

from fixture_mod import add


class AddTests(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)
```
02:
```python
import unittest

from fixture_mod import eligible


class EligibleTests(unittest.TestCase):
    def test_eligible(self):
        self.assertIs(eligible(18), True)
        self.assertIs(eligible(17), False)
```
03:
```python
import ast
import unittest
from pathlib import Path

from fixture_mod import total


class TotalTests(unittest.TestCase):
    def test_total(self):
        self.assertEqual(total([1, 2, 3]), 6)

    def test_sin_bucle_manual(self):
        source = Path(__file__).with_name('fixture_mod.py').read_text(encoding='utf-8')
        loops = [n for n in ast.walk(ast.parse(source)) if isinstance(n, (ast.For, ast.While))]
        self.assertEqual(loops, [], 'refactoriza total sin bucle manual')
```
04:
```python
import unittest

from fixture_mod import VERSION


class VersionTests(unittest.TestCase):
    def test_version_semver(self):
        parts = VERSION.split('.')
        self.assertEqual(len(parts), 3)
        self.assertTrue(all(p.isdigit() for p in parts))
```
05:
```python
import unittest

from fixture_mod import clamp


class ClampTests(unittest.TestCase):
    def test_clamp_bounds(self):
        self.assertEqual(clamp(-1, 0, 10), 0)
        self.assertEqual(clamp(11, 0, 10), 10)
        self.assertEqual(clamp(5, 0, 10), 5)
```

**`fixture_mod.py` y `CORREGIDO`:**

| Tarea | Sin corregir | Cambia | `CORREGIDO` |
|---|---|---|---|
| 01 | `return a - b  # defecto: resta` | no | `def add(a, b):\n    return a + b\n` |
| 02 | `raise NotImplementedError` | no | `def eligible(age):\n    return age >= 18\n` |
| 03 | bucle `for` | no | `def total(xs):\n    return sum(xs)\n` |
| 04 | `VERSION = '0.1'` | **sí** | `VERSION = '0.1.0'\n` |
| 05 | `return min(hi, x)` (sin límite inferior) | **sí** (DEC-02) | `def clamp(x, lo, hi):\n    return max(lo, min(hi, x))\n` |

**Tarea 03.** Un refactor conserva la conducta, así que ninguna prueba de conducta puede partir en rojo: la única vía es una regla estructural, y eso añade `test_sin_bucle_manual`.

**`fixtureSha256`** (solo válidos con el contenido exacto de arriba, con `fixture_mod.py` terminado en salto de línea; los de 01, 02 y 03 mantienen su `fixture_mod.py` actual):

| Tarea | Valor esperado |
|---|---|
| 01 | `51190d30c9550f43aeb6164681c862da7031f03456ffed41f6c014f49976be93` |
| 02 | `635e6014f3ce8997c831d2ab9ca991dbe6e8eb5a74fdac117883ede07b50150f` |
| 03 | `1558cee8f6c79e04667f8314df15a2cfd99c2c96715454fb1d1ab9d3da8bc7d7` |
| 04 | `a14747efd847effbeab7000f054fb2e8d1aa55b4d3113f17c8f9fcd795fe897c` |
| 05 | `2e571438d8abf17694648103cddef33f5d7548c1a5dfcd4622bb763dc6160164` |

Si la prueba de AC-08 difiere, manda la prueba: el implementador pega el valor que calcule y lo reporta. Los valores no son el criterio.

### Textos del aviso
**`bench/baseline/README.md`**, justo tras el título `# Línea base`, sin tocar el resto:

```markdown
> **AVISO: este baseline no es evidencia sobre MicroSDD.** Su veredicto `RECHAZA` no compara con y sin arnés. Los datos se conservan solo como registro histórico.
>
> - **Brazos equivalentes (confirmado).** Según `1f3a731`, `treatment` solo copiaba el fixture. En `eb3d43e` (16 celdas, run 39802356050) y `ef3955f` (14 celdas, run 39878723841), `run_bench` llama a `copy_fixture` en ambos brazos y el prompt no depende del brazo.
> - **Señal de éxito no fiable (confirmado).** Las cinco pruebas eran funciones sueltas sin `TestCase`: sin editarlas, `python -m unittest test_fixture` da `Ran 0 tests` y código 5 con Python 3.12, la versión que fija el workflow. Además, las tareas 03, 04 y 05 ya cumplían sus aserciones.
> - **Inferido, no observado.** Las 19 celdas con éxito exigen que el agente alterara algo para que `unittest` recogiera pruebas; los diffs no se conservaron. Un éxito tampoco indica que la lógica se corrigiera.
>
> `complete` significa que terminaron las 30 celdas, no que el resultado sea válido. Solo el gasto sirve, como orden de magnitud.
```

**`notes` de `bench/config.json`** (sustituye a las cuatro actuales):

```json
"notes": [
  "AVISO: este baseline no es evidencia sobre MicroSDD; ver bench/baseline/README.md.",
  "Brazos equivalentes según 1f3a731 (treatment solo copiaba el fixture); confirmado en eb3d43e (16 celdas, run 39802356050) y ef3955f (14 celdas, run 39878723841). Su veredicto no compara con y sin arnés.",
  "Señal de éxito no fiable: 0 pruebas recogidas y código 5 con Python 3.12 sin editar; las tareas 03, 04 y 05 ya cumplían sus aserciones.",
  "Datos históricos, sin regenerar: cheap N=3, 30/30 celdas, reporte RECHAZA (base 11/15, treatment 8/15). Modelo deepseek/deepseek-v4-flash, maxTurns=6. Fill: 85/100 req, usage Δ ≈ $0.080. No mezclar archivos viejos."
]
```

**`bench/README.md`**, tras la línea de A/B:

```markdown
Una celda solo cuenta como éxito si `unittest` termina con código 0 y ejecuta al menos una prueba que pasa; `tests/test_bench_senal.py` lo comprueba en las cinco tareas, sin red.
```

**`assets/eval-esfuerzo.md:17`** (solo con DEC-02 A): `5. **Prueba de regresión:** un defecto reintroducido que la prueba de regresión existente detecta; se corrige el código sin tocar la prueba. → \`bench/tareas/05-prueba-regresion\``

## Decisiones para el humano
- **DEC-01: ¿restaurar `test_fixture.py` antes de evaluar?** Sin esto, un agente puede cambiar la prueba por `assertTrue(True)` y obtener ÉXITO, incumpliendo el objetivo. Es lo que el baseline sugiere que ya ocurría.
  - A (recomendada): restaurar y avisar en el prompt, en los dos brazos. Unas 8 líneas y AC-06.
  - B: no restaurar y aceptar el riesgo. Se quitan REQ-05, AC-06 y T08.
- **DEC-02: ¿cómo parte en rojo la tarea 05?** Hoy pide añadir una prueba para un defecto ya corregido, lo que choca con una evaluación que restaura la prueba.
  - A (recomendada): reintroducir el defecto en `clamp`. Es mínima, pero la tarea pasa a parecerse a la 01 y cambia su descripción en `assets/eval-esfuerzo.md`.
  - B: una prueba que exija un `test_regresion.py` escrito por el agente y compruebe que detecta un mutante. Conserva el tipo de tarea, pero añade unas 15 líneas al fixture, un archivo más y lógica frágil. Exige rehacer el presupuesto.
- **DEC-03: ¿quitar las claves del entorno de la prueba?** Hallazgo no solicitado: `run_cell` quita la clave del entorno de Claude, pero la prueba hereda `os.environ` y ejecuta código escrito por el modelo con `OPENROUTER_API_KEY` disponible. Ese riesgo aplica en cualquier corrida real.
  - A (recomendada): quitarlas, 2 líneas en el helper y AC-07.
  - B: dejarlo fuera y abrir otra tarea. Se quita REQ-07.

## Alternativas descartadas
- **Solo tratar el código 5 como 0 en anteriores a 3.12, o solo exigir `Ran N>0`:** dejan pasar omisiones y fallos esperados.
- **`--failfast`, `-v` o un `testCommand` propio:** no resuelven `Ran 0` y añaden divergencia.
- **Reporte JSON con un runner propio:** una capa más, sin necesidad.
- **Directorio `solucion/` por tarea:** cinco archivos más, sin sellar, y más riesgo de filtrarse al fixture.
- **Parchear `fixture_mod.py` en la prueba:** no ejercería el comando real.
- **Añadir las pruebas a `tests/test_bench.py`:** obligaría a sellar 1.083 líneas.
- **Mantener funciones sueltas y usar pytest:** añade una dependencia; el proyecto usa solo stdlib.
- **`testing.fitness` activo:** `bench.py` tiene más de 2.000 líneas y crece, así que `max_lines` daría violación y habría que subir el límite. No funciona sin complicaciones.
- **Mutación:** lógica pequeña, y la tabla de AC-01 y los rojos y verdes reales la fijan.

## Invariantes y riesgos
- **Invariantes:** cinco tareas; mismos `testCommand` y `title`; `install_harness` sin cambios; topes y `baselineStatus` sin cambios; prompt igual en los dos brazos; datos de `bench/baseline/` intactos.
- **R-01: formato del resumen.** Depende del texto de `unittest`; si cambia, la señal falla cerrada (`ok=False`), nunca abierta. La prueba de los rojos y verdes reales lo detectaría en la versión que corra la suite.
- **R-02: `testsRun` y resultados previos.** Los resultados anteriores no son comparables con los nuevos: cambió el contenido de las tareas.
- **R-03: bytecode del agente.** Un `.pyc` obsoleto solo sería válido con igual tamaño y mismo segundo de `mtime`, algo muy improbable tras un turno de agente; no se trata (YAGNI).
- **R-04: engaños del agente fuera de la prueba.** Un `unittest.py` propio o un `fixture_mod.py` que manipule `unittest` siguen siendo posibles. No se busca seguridad frente a un agente hostil.
- **R-05: comodines en la tarea 03.** Una recursión o `functools.reduce` también pasan: es válido, la regla solo prohíbe bucles manuales.
- **R-06: ruido.** Con brazos idénticos se observó 11/15 frente a 8/15. Un dato anecdótico, pero indica que N=3 distingue poco; no se usa como medida.
- **Hallazgo sin tratar:** `aggregate_report` usa `hash(tid)` en la semilla por tarea, que varía con `PYTHONHASHSEED`. Solo afecta al IC por tarea, no al veredicto global. Queda fuera de alcance.

## Estimación
| Bloque | Base | Factor | Tope |
|---|---|---|---|
| `.microharness/bench.py` | 45 | ×1,3 | 60 |
| Aviso, `notes`, `bench/README.md`, `eval-esfuerzo.md` | 23 | ×1,3 | 30 |
| `test_fixture.py` (5 archivos) | 52 | ×1,75 | 91 |
| `fixture_mod.py` y `task.json` | 7 | ×1,3 | 9 |
| `tests/test_bench_senal.py` | 85 | ×1,75 | 150 |
| `tests/test_bench.py` (mock) | 1 | ×1,75 | 2 |
| **Total** | | | **342** |

**Margen frente a `rdd_max_lines`: 500 − 342 = 158**, por encima de los 150 pedidos. El hook acumula también el retrabajo, así que una iteración del revisor consume ese margen. Si DEC-02 B se elige, el margen baja de 150 y hay que recortar antes de aprobar. Primer recorte: unir AC-05 y AC-06.

## Siguiente paso (fuera de esta spec)
**Comprobar si `treatment` puede terminar una tarea.** Requiere red y autorización de gasto del humano: no lo ejecuta ningún agente de esta tarea. Conviene hacerlo con esta tarea integrada y antes de cualquier corrida completa.

**Coste estimado.** Referencia: 14 celdas ≈ $0,080 y 85 solicitudes, unos $0,0057 y 6 solicitudes por celda. `treatment` añade contexto del arnés, sin medir: se toma como orden de magnitud **$0,005 a $0,02 por celda**, estimación sin confirmar. Una celda de `treatment` y otra de `base`, para comparar, quedan alrededor de **$0,04 como máximo**, por debajo del candado vigente de $0,10 (aborta en $0,08). `costUsdModelEstimate` no es el gasto facturado.

**Comando** (humano, en su terminal, con Claude Code 2.1.197). `bench run` no admite elegir celdas por CLI, así que se edita `bench/config.json` solo para la corrida y luego se revierte:

```sh
python3 -c "import json;p='bench/config.json';c=json.load(open(p,encoding='utf-8'));c['onlyCells']=[{'taskId':'01-correccion-localizada','variant':'treatment','repetition':0},{'taskId':'01-correccion-localizada','variant':'base','repetition':0}];json.dump(c,open(p,'w',encoding='utf-8'),indent=2)"
export OPENROUTER_API_KEY=...
export BENCH_PROXY_STATE="$HOME/.cache/microsdd-ab/celda-count.json"
mkdir -p "$HOME/.cache/microsdd-ab"
python3 .microharness/metrics.py bench run --cheap --provider openrouter --out "$HOME/.cache/microsdd-ab/celda"
git restore bench/config.json
```

**Lectura.** En `bench-report.json`, mirar en cada celda `success`, `testsRun`, `subtype`, `iterations` y `tokens`; el veredicto será `NO CONCLUYENTE`, como corresponde con dos celdas. Si `treatment` falla y `base` no, hay indicio de bloqueo del arnés, no prueba: el reporte no guarda la conversación. Para distinguirlo, habría que conservar la salida de Claude, y eso requiere otra spec. Si lo confirma, una corrida completa mediría ese bloqueo, y arreglarlo (`install_harness`, spec precargada) también es otra spec, que no se ha estimado aquí.
