# QUÉ: requisitos

## Objetivo
Añadir `sdd.py symbols [ruta ...]`: un comando de solo lectura y bajo demanda que imprime por stdout, en JSON, un mapa compacto de la superficie pública de un repositorio Python, sin cuerpos de función.

La hipótesis es que este mapa evita que un agente duplique abstracciones. **Esa hipótesis no está medida.** El comando queda marcado como experimental en la documentación, y usarlo como parte del flujo es una decisión posterior sobre datos. Esta tarea no afirma ningún beneficio.

## Precondiciones
- Rama `feat/symbol-map` en `23cec87`, con `.microharness/sdd.py` en versión 1.5.3.
- Suite en verde: 490 pruebas, 4 omitidas, con `sh .microharness/python.sh -m unittest discover -s tests` (ejecutada al especificar).
- **DEC-01 y DEC-02 confirmadas por el humano al aprobar la spec.**

## Decisiones pendientes del humano

**DEC-01: si los agentes pueden ejecutar el comando.** El hook solo admite a `lider`, `autor` e `implementador` los subcomandos de `SDD_ALLOWED`, así que `symbols` quedaría denegado. Además, ningún agente puede cambiarlo: `implementador` tiene prohibido `.claude/` aunque esté en `allowed_paths`, y `lider` y `autor` no editan código.

- **A (recomendada y redactada en esta spec).** El humano aplica en su editor, fuera de Claude Code, el parche de dos líneas de `plan.md`. Justificación: sin él, ningún agente puede usar el comando, que es su razón de ser; el comando no escribe nada y el hook sigue rechazando metacaracteres de shell. El permiso no obliga a usarlo: nada lo inyecta ni lo exige.
- **B.** No tocar el hook: solo el humano ejecuta `symbols` en su terminal y pega la salida si quiere. Evita ampliar API-05, pero un agente no puede consultarlo por sí mismo.

Si elige B, salen REQ-13, AC-12, `.claude/hooks/pretool.py` de `allowed_paths` y la mención a API-05; hay que volver a especificar antes de aprobar.

**DEC-02: compromiso de estabilidad de la salida.** Un subcomando nuevo tiene que constar en API-01, porque `tests/test_api_publica.py` lo exige.

- **A (recomendada y redactada en esta spec).** API-01 fija el nombre, los argumentos y los códigos de salida. El formato JSON se declara experimental y fuera de la API pública, en el párrafo «No forman parte de la API pública», de modo que puede cambiar sin versión mayor.
- **B.** El formato JSON también es API pública desde ahora. Cambiarlo de forma incompatible exigiría `!`, antes de saber si el comando se conserva.

Si elige B, cambian REQ-14 y AC-14.

## Requisitos EARS

### Contenido
- REQ-01: WHEN se ejecuta `symbols`, THE sistema SHALL imprimir por stdout una sola línea JSON ASCII con separadores compactos y las claves `source`, `files` y `errors`, en ese orden, y terminar con código 0, también si hay errores de análisis por archivo.
- REQ-02: THE sistema SHALL incluir, por archivo, solo clases y funciones públicas que sean hijas directas del módulo. Es pública la que no empieza por `_`.
- REQ-03: THE sistema SHALL describir cada clase con `name`, `bases`, `doc`, `fields` y `methods`. `bases` son las bases posicionales; `fields` son sus anotaciones directas públicas, como `"nombre: tipo"`, sin valor; `methods` son sus métodos directos públicos más `__init__`.
- REQ-04: THE sistema SHALL describir cada función y método con `name`, `signature` y `doc`, además de `async: true` solo si es asíncrono.
- REQ-05: THE sistema SHALL generar `signature` con los parámetros tal como están declarados, incluidos *positional-only*, *keyword-only*, `*args`, `**kwargs`, anotaciones, valores por defecto y retorno. IF falta una anotación o un retorno, THEN THE sistema SHALL omitirlos, sin inventar `Any` ni `None`.
- REQ-06: THE sistema SHALL tomar como `doc` la primera línea del docstring normalizado con `ast.get_docstring`.
- REQ-07: IF un valor es una lista o docstring vacíos, o un archivo no tiene símbolos públicos, THEN THE sistema SHALL omitir la clave o el archivo. `files` y `errors` siempre están presentes.

### Selección de archivos
- REQ-08: WHEN `git ls-files` funciona en la raíz, THE sistema SHALL considerar solo archivos rastreados, leer su contenido actual en disco e informar `"source": "git"`. WHEN no hay repositorio o Git no está disponible, THE sistema SHALL recorrer el disco e informar `"source": "filesystem"`, sin entrar en directorios ocultos ni en `__pycache__`, `node_modules`, `venv`, `env`, `site-packages`, `build` o `dist`.
- REQ-09: THE sistema SHALL procesar únicamente archivos terminados en `.py`, sin distinguir mayúsculas, que no sean enlaces simbólicos.
- REQ-10: THE sistema SHALL excluir, en ambos modos, los archivos con algún directorio oculto, `tests` o `test`, o con nombre `test_*.py`, `*_test.py` o `conftest.py`, evaluando solo los componentes por debajo de la ruta pedida. Los componentes por encima de la raíz nunca cuentan, y un archivo pedido de forma explícita nunca se excluye.
- REQ-11: WHEN se indican rutas, THE sistema SHALL interpretarlas relativas a la raíz del arnés, normalizarlas con `normalized_rel` y procesar su unión; sin rutas, procesa la raíz. IF una ruta es absoluta, contiene `..` o no existe, THEN THE sistema SHALL escribir `ERROR:` en stderr, no imprimir nada en stdout y terminar con código 1.

### Robustez y solo lectura
- REQ-12: IF un archivo seleccionado no se puede leer o analizar, THEN THE sistema SHALL añadir `{"path", "error"}` a `errors` y continuar con el resto. WHILE el árbol y el intérprete no cambien, THE sistema SHALL producir una salida idéntica, con `files` y `errors` ordenados por ruta y los símbolos en orden de aparición.
- REQ-13: WHEN `lider`, `autor` o `implementador` ejecutan `symbols` con un lanzador admitido y sin metacaracteres de shell, THE hook SHALL permitirlo. THE hook SHALL seguir denegándolo a `revisor`.
- REQ-14: THE documentación SHALL marcar el comando como experimental, declarar que no hay medición de beneficio y dejar su integración en el flujo como decisión posterior sobre datos.

Restricciones técnicas:
- Sin escribir archivos, sin caché, sin leer ni tocar `memory.json`, sin lock ni telemetría.
- Solo biblioteca estándar (D-05), sin imports nuevos en `sdd.py`. `ast.parse` no ejecuta el código analizado.

## Criterios de aceptación

**AC-01 (REQ-05), firmas.** `signature` exacta para cada fuente:

| Fuente | `signature` |
|---|---|
| `def f(a, b=1, /, c: int = 2, *args: str, d, e=3, **kw) -> int: pass` | `(a, b=1, /, c: int=2, *args: str, d, e=3, **kw) -> int` |
| `def f(*, k): pass` | `(*, k)` |
| `def f(): pass` | `()` |
| `def f(x, y): pass` | `(x, y)` |
| `def f(*a, **b) -> None: pass` | `(*a, **b) -> None` |
| `def f(x: 'Foo' = None) -> 'Bar': pass` | `(x: 'Foo'=None) -> 'Bar'` |

**AC-02 (REQ-01 a REQ-04, REQ-07), contenido exacto.** Dado `src/m.py`:
```python
class A(B, m.C, metaclass=M):
    """Clase A.

    Más."""
    x: int = 1
    _y: str
    z = 2
    def __init__(self, a): self.a = a
    def _p(self): pass
    def __repr__(self): return ''
    async def m(self, *, k=1) -> None: pass
    class Interna: pass
class _P: pass
def g(): pass
def _h(): pass
if True:
    def cond(): pass
```
la entrada de `files` es exactamente:
```json
{"path":"src/m.py","classes":[{"name":"A","bases":["B","m.C"],"doc":"Clase A.","fields":["x: int"],"methods":[{"name":"__init__","signature":"(self, a)"},{"name":"m","signature":"(self, *, k=1) -> None","async":true}]}],"functions":[{"name":"g","signature":"()"}]}
```

**AC-03 (REQ-06, REQ-07), docstrings y omisiones.**

| Fuente | Resultado |
|---|---|
| `def f():\n    """\n    Hola.\n\n    Más.\n    """` | `doc` = `Hola.` |
| `def f():\n    """   """` | sin clave `doc` |
| `def f(): pass` | sin clave `doc` |
| `class C: pass` | `{"name":"C"}` |
| solo `def _p(): pass` | el archivo no aparece en `files` ni en `errors` |

**AC-04 (REQ-08, REQ-09), con Git.** En un repositorio con `a.py` y `B.PY` en el índice, `n.py` sin rastrear y `x.txt` rastreado: `source` es `git` y `files` contiene `B.PY` y `a.py`, en ese orden. Si un archivo rastreado se modifica sin confirmar, el mapa refleja el disco. Si `borrado.py` está rastreado y no existe en disco, aparece en `errors` y el código es 0. Un `.py` rastreado que sea enlace simbólico no aparece (se omite donde no se puedan crear enlaces).

**AC-05 (REQ-08), sin Git.** Sin repositorio, y también con `git` inaccesible (`subprocess.run` lanzando `FileNotFoundError`): `source` es `filesystem`, y `a.py` y `pkg/b.py` aparecen. No aparecen `.oculto/o.py`, `__pycache__/c.py`, `venv/v.py`, `build/b.py` ni `node_modules/n.py`.

**AC-06 (REQ-10), exclusiones relativas.** En ambos modos, con la raíz en `<tmp>/tests/repo`:

| Archivo | `symbols` | Pedido explícito |
|---|---|---|
| `src/a.py` | aparece, aunque un directorio superior se llame `tests` | sí |
| `tests/t.py` | no aparece | `symbols tests` sí |
| `pkg/tests/t.py` | no aparece | `symbols pkg/tests` sí |
| `src/test_x.py`, `src/x_test.py`, `src/conftest.py` | no aparecen | `symbols src/test_x.py` sí |
| `.interno/i.py` | no aparece | `symbols .interno` sí |

**AC-07 (REQ-11), rutas.**

| Argumentos | Resultado |
|---|---|
| `symbols src` | solo archivos bajo `src/`; no `srcx/a.py` |
| `symbols src src/a.py` | cada archivo una sola vez |
| `symbols x.txt` (existe) | código 0, `files` vacío |
| `symbols no-existe`, `symbols ../x`, `symbols /abs/x` | código 1, `ERROR:` en stderr, stdout vacío |

En modo Git, `symbols n.py` con `n.py` sin rastrear da código 0 y `files` vacío.

**AC-08 (REQ-12), archivos no analizables.** Con `bad.py` (`def (:`), `nul.py` (contiene `\0`), `lat.py` (bytes `\xff\xfe`) y `ok.py` válido: código 0, `errors` lista las tres rutas por orden, cada una con `error` no vacío, y `files` contiene `ok.py`. El error de un archivo borrado no incluye su ruta absoluta.

**AC-09 (REQ-12), determinismo.** Dos ejecuciones seguidas sobre el mismo árbol dan stdout idéntico byte a byte, con archivos creados en orden no alfabético. `def z` antes de `def a` en un mismo archivo conserva ese orden.

**AC-10 (restricciones), solo lectura.** Tras `symbols`, en un árbol temporal sin `.microharness/memory.json`, la lista de rutas y el contenido de todos los archivos, incluido `.git/index`, no cambian, y `memory.json` y `SYMBOL_MAP.json` siguen sin existir.

**AC-11 (REQ-01), proceso real.** `sdd.py symbols src`, lanzado como subproceso sobre este repositorio, termina con código 0, y su stdout es una sola línea ASCII que `json.loads` acepta. `source` es `git` e incluye `src/microsdd/installer.py` con la función `main`.

**AC-12 (REQ-13), hook.** `hook.run` con `Bash`:

| Agente | Comando | Resultado |
|---|---|---|
| `lider`, `autor`, `implementador` | `sh .microharness/python.sh .microharness/sdd.py symbols` | permitido |
| `lider`, `autor`, `implementador` | `python .microharness/sdd.py symbols src tests` | permitido |
| `implementador` | `python .microharness/sdd.py symbols src; rm -rf src` | denegado |
| `implementador` | `python .microharness/sdd.py symbols src > x` | denegado |
| `revisor` | `python .microharness/sdd.py symbols` | denegado |

**AC-13 (restricciones), sin efectos laterales en el contrato.** Por `git diff`: `sdd.py` no añade imports ni cambia `__version__`; `src/microsdd/`, `pyproject.toml` y `.claude/agents/` no cambian. `sdd.py` no menciona `SYMBOL_MAP`, `.base_head_sha` ni `WorktreeCollisionGuard`.

**AC-14 (REQ-14), documentación.** Por lectura de `git diff`:
- `assets/proceso-versionado.md` incluye `symbols` en API-01 y API-05, y su formato JSON en «No forman parte de la API pública».
- `assets/arnes-completo.md` tiene una subsección que dice «experimental» y que no hay medición, indica la decisión posterior sobre datos y enumera los límites conocidos de `plan.md`. También añade `symbols` a la lista de formas permitidas del hook.
- Ninguno afirma beneficios ni contiene cifras de ahorro o latencia.
- `tests/test_api_publica.py` pasa sin cambios.

**AC-15, verificación.** `sh .microharness/python.sh .microharness/sdd.py check symbol-map --run` termina en `OK`, con al menos 502 pruebas (490 actuales más los 12 métodos de `tests/test_symbols.py`).

## Fuera de alcance
- Hooks de git, propagación a worktrees, detector de colisiones (`WorktreeCollisionGuard`) y `.base_head_sha`.
- Caché incremental y cualquier `SYMBOL_MAP.json` en disco.
- Inyectar el mapa en prompts o exigirlo en `.claude/agents/`.
- Estados, roles o motor nuevos; stubs; `chmod`; árbitro.
- Otros lenguajes y dependencias externas.
- Correr el bench o modificarlo.
- Decoradores, `metaclass`, parámetros de tipo (PEP 695), variables de módulo, `__all__`, clases anidadas y símbolos bajo `if`/`try`: límites documentados.
- `README.md`, `CHANGELOG.md`, `docs/`, `assets/decisiones-diseno.md` y `__version__`.
