# QUÉ: requisitos

## Objetivo
Añadir una puerta opcional por tarea, `testing.fitness`, apagada por defecto. Cuando está activa, `check` rechaza archivos Python cambiados dentro del alcance que violan límites estructurales medidos con `ast`: parámetros, complejidad ciclomática y líneas físicas. Mismo espíritu que `testing.mutation` (D-10): proporcional, no obligatoria.

Límites del control, que deben quedar documentados: solo Python; mide estructura y no calidad semántica; no es un control de seguridad; compara contra `HEAD`.

## Precondiciones
- Rama `feat/seal-monotonico` en `4f4ac1a`, con `.microharness/sdd.py` en versión 1.5.3.
- Suite en verde: 461 pruebas, 4 omitidas, con `python -m unittest discover -s tests` (ejecutada al especificar).
- **DEC-01 confirmada por el humano al aprobar la spec.**

## Decisión pendiente del humano

**DEC-01: qué pasa con un archivo preexistente que ya está fuera de límite.** `.microharness/sdd.py` tiene 1437 líneas y funciones como `validate` superan con creces la complejidad 10, así que la regla determina si la puerta se puede usar en código real.

- **A (recomendada y redactada en esta spec).** Trinquete frente a `HEAD` más límite explícito: un valor falla solo si supera el límite **y** además es nuevo o peor que en `HEAD`. Para hacer crecer algo ya fuera de límite, la spec sube el límite, cambio que invalida la huella y exige reaprobación (D-09).
- **B.** Sin comparación con `HEAD`: todo valor sobre el límite falla y la única salida es subir el límite. Más simple (unas 25 líneas menos), pero tocar una función de complejidad 40 obliga a admitir 40 en todas las funciones nuevas de la tarea.
- **C.** Como A para funciones, pero `max_lines` solo se aplica a archivos nuevos. Evita subir el límite para crecer un archivo grande, pero no frena su crecimiento, que es justo el caso de `sdd.py`.

Si el humano elige B o C, cambian REQ-08, REQ-09, AC-10, AC-11, AC-12 y el plan; hay que volver a especificar antes de aprobar.

## Requisitos EARS

### Configuración
- REQ-01: WHEN se crea una tarea con `new`, THE sistema SHALL escribir en `testing.fitness` el objeto `{"enabled": false, "max_params": 4, "max_complexity": 10, "max_lines": 250}`.
- REQ-02: IF `testing.fitness` no existe o `enabled` es `false`, THEN THE sistema SHALL no evaluar ningún archivo, de modo que las specs existentes sin el campo sigan funcionando igual.
- REQ-03: IF `enabled` es `true` y falta un límite, THEN THE sistema SHALL usar su valor por defecto: `max_params` 4, `max_complexity` 10, `max_lines` 250.
- REQ-04: WHILE la tarea no esté `terminado`, WHEN `check` o `approve spec` validen la spec, THE sistema SHALL rechazar con error claro un `testing.fitness` de tipo inválido, también con `enabled` en `false`. IF la tarea está `terminado`, THEN THE sistema SHALL ignorar el campo por completo.

### Medidas
- REQ-05: THE sistema SHALL medir cada `def` y `async def` del archivo, incluidos métodos y funciones anidadas, identificados por nombre cualificado con puntos (`C.m`, `f.g`, `f.C.m`), según estas definiciones:
  - **Parámetros:** posicionales (incluidos los *positional-only*), keyword-only, `*args` y `**kwargs`. Se descuenta 1 solo si el primer posicional o *positional-only* se llama exactamente `self` o `cls`, sea cual sea el contexto. No se descuenta en `*self`, `**cls`, en un keyword-only ni en otra posición.
  - **Complejidad ciclomática:** 1 más la suma, en el cuerpo de la función, de:

    | Nodo `ast` | Suma |
    |---|---|
    | `If`, `IfExp` | 1 cada uno (cada `elif` es un `If`) |
    | `For`, `AsyncFor`, `While` | 1 cada uno (su `else` no suma) |
    | `ExceptHandler` | 1 cada uno |
    | `BoolOp` | número de operandos menos 1 |
    | `comprehension` | 1 por cada `for` más 1 por cada `if` de la comprensión, en lista, conjunto, diccionario o generador |
    | `match_case` | 1 cada uno, incluido `case _` (su guarda no suma por sí misma) |

    No suman: `try`, `else`, `finally`, `with`, `assert`, `return`, `raise`, `lambda`. El cuerpo de una `lambda` pertenece a la función que la contiene. No se entra en un `def` anidado, que se mide aparte. El cuerpo de una clase anidada sí suma a la función que la contiene, salvo sus métodos. Decoradores, anotaciones y valores por defecto del propio `def` no suman.
- REQ-06: THE sistema SHALL medir las líneas físicas del archivo como las que resultan de partir sus bytes por `\n`, `\r\n` o `\r`, incluidas líneas en blanco y comentarios. Código a nivel de módulo o de clase solo se mide mediante este total.

### Archivos evaluados
- REQ-07: WHEN se valide con alcance una tarea no `terminado` con la puerta activa, THE sistema SHALL evaluar solo los archivos del diff frente a `HEAD` más los no rastreados (`diff_files`) que cumplan todo lo siguiente: terminan en `.py` (sin distinguir mayúsculas), coinciden con `scope.allowed_paths`, existen en disco (los borrados no se evalúan) y no son pruebas. Es prueba un archivo cuya ruta esté literalmente en `testing.protected_tests` o coincida con `testing.fitness.test_patterns`. Si `test_patterns` falta, se usan `test_*.py`, `*_test.py`, `conftest.py` y `tests/**`; si existe, sustituye a esos valores, y `[]` deja solo `protected_tests`.

### Archivos preexistentes (según DEC-01, opción A)
- REQ-08: IF un valor supera su límite, THEN THE sistema SHALL informar violación solo si la función o el archivo no existe en `HEAD`, o si el valor es mayor que en `HEAD`. Una función se identifica por nombre cualificado; si el nombre se repite en `HEAD`, la base es el mayor valor de los repetidos. Si la versión de `HEAD` no se puede analizar, la base se considera vacía.
- REQ-09: WHEN una spec sube un límite, THE sistema SHALL aplicar el nuevo límite a todos los archivos evaluados de la tarea, y el cambio tras la aprobación SHALL invalidar la huella de la spec como cualquier otro cambio de `spec.json`.

### Errores e integración
- REQ-10: WHEN haya violaciones, THE sistema SHALL añadir un error por violación con el formato `Fitness: <ruta>:<línea> <función> <medida> N > límite M`, donde `<medida>` es `parámetros`, `complejidad` o `líneas`, `<línea>` es la del `def`, y la violación de líneas usa `:1` y `<archivo>` como función. El orden es por ruta; dentro de cada archivo, primero `líneas` y después las funciones por línea, con `parámetros` antes que `complejidad`.
- REQ-11: IF un archivo evaluado no se puede leer o analizar, THEN THE sistema SHALL añadir un único error `Fitness: <ruta>: no se pudo analizar: <detalle>`, sin traza de Python, y SHALL seguir evaluando los demás archivos.
- REQ-12: WHEN `check` tenga errores de fitness, THE sistema SHALL devolver código 1 sin ejecutar comandos de pruebas con `--run`, y `approve close` SHALL rechazar el cierre. WHEN se use `check --no-scope` o `approve spec`, THE sistema SHALL no evaluar archivos, porque esas vías no miran el diff.
- REQ-13: THE sistema SHALL usar solo la biblioteca estándar (D-05) y documentar la puerta y sus límites en `assets/arnes-completo.md` y el esquema en API-02 de `assets/proceso-versionado.md`.

## Criterios de aceptación

Salvo que se indique otra cosa, los casos usan un repositorio Git temporal con commit inicial, `scope.allowed_paths: ["src/**", "tests/**"]`, tarea no `terminado` y `sdd.validate(slug)`. «Sin error» significa ningún error que empiece por `Fitness:` o `testing.fitness`.

### Configuración
- AC-01: `new` genera `testing.fitness == {"enabled": false, "max_params": 4, "max_complexity": 10, "max_lines": 250}`; `check` no da errores de fitness con esa plantilla.
- AC-02: con `src/a.py` en el diff y una función de 5 parámetros: sin el campo → sin error; con `{"enabled": false}` → sin error; con `{"enabled": true}` → `Fitness: src/a.py:1 f parámetros 5 > límite 4`; con `{"enabled": true, "max_params": 5}` → sin error. Un archivo nuevo de 251 líneas con `{"enabled": true}` → error de `líneas`, y una función de complejidad 11 → error de `complejidad`.
- AC-03: tipos inválidos, cada uno con `enabled` en `false` cuando aplique, producen exactamente este error y `check` devuelve 1:

  | Entrada | Error |
  |---|---|
  | `testing.fitness`: `[]`, `true`, `"x"`, `null` | `testing.fitness debe ser un objeto` |
  | `{}`, `{"enabled": 1}`, `{"enabled": "true"}` | `testing.fitness.enabled debe ser booleano` |
  | cada límite: `0`, `-1`, `true`, `"4"`, `1.5`, `null` | `testing.fitness.<límite> debe ser un entero mayor o igual a 1` |
  | `{"enabled": false, "max_param": 4}` | `testing.fitness: claves no admitidas: max_param` |
  | `test_patterns`: `"tests/**"`, `[1]`, `[""]`, `["../x"]` | `testing.fitness.test_patterns debe ser una lista de rutas relativas` |

  `approve spec` rechaza `{"enabled": 1}` con `La spec no es válida:` y ese texto.
- AC-04: con `state: terminado` y `testing.fitness: "x"`, o activa con un archivo en violación en el diff, `validate` no devuelve errores de fitness.

### Medidas
- AC-05: parámetros de la función `f` (o del método indicado):

  | Fuente | Parámetros |
  |---|---|
  | `def f(): pass` | 0 |
  | `def f(a, b, /, c, *d, e, **g): pass` | 6 |
  | `def f(self, a): pass` | 1 |
  | `def f(cls, a): pass` | 1 |
  | `def f(self, /, a): pass` | 1 |
  | `def f(a, self): pass` | 2 |
  | `def f(*self): pass` | 1 |
  | `def f(**cls): pass` | 1 |
  | `def f(*, self): pass` | 1 |
  | `def f(this, a): pass` | 2 |
  | `async def f(a, b): pass` | 2 |
  | `class C:` con `def m(self, a): pass` (nombre `C.m`) | 1 |

- AC-06: complejidad, con cada fuente como cuerpo de `def f(a, b, c, y, v):` salvo donde se indica:

  | Cuerpo | Complejidad |
  |---|---|
  | `pass` | 1 |
  | `if a: pass` / `elif b: pass` / `else: pass` | 3 |
  | `z = 1 if a else 2` | 2 |
  | `for x in y: pass` / `else: pass` | 2 |
  | `while a: pass` | 2 |
  | `try: pass` / `except A: pass` / `except B: pass` / `else: pass` / `finally: pass` | 3 |
  | `z = a and b` | 2 |
  | `z = a and b and c` | 3 |
  | `z = a and b or c` | 3 |
  | `z = [x for x in y]` | 2 |
  | `z = {x for x in y}` | 2 |
  | `z = (x for x in y)` | 2 |
  | `z = {k: 1 for a in b for k in a}` | 3 |
  | `z = [x for x in y if x if a]` | 4 |
  | `match v:` con `case 1`, `case 2 if a`, `case _` | 4 |
  | `with a: pass` | 1 |
  | `assert a` | 1 |
  | `z = lambda: a and b` | 2 |

  Además: `async def f(y):` con `async for x in y: pass` → 2. `def f(a):` con `def g(): if a: pass` anidada → `f` 1 y `f.g` 2. `def f(a=b and c): pass` → 1. `def f(a):` con clase anidada `C` cuyo cuerpo tiene `if a: pass` y método `m` con `if a: pass` → `f` 2 y `f.C.m` 2.
- AC-07: líneas físicas: `b''` → 0; `b'a\n'` → 1; `b'a\nb'` → 2; `b'a\r\nb\r\n'` → 2; `b'\n\n'` → 2; `b'# c\n\nx = 1\n'` → 3; `b'x = 1\x0c\n'` → 1. Un archivo con `# -*- coding: latin-1 -*-` y bytes no UTF-8 se analiza sin error.

### Archivos evaluados
- AC-08: con la puerta activa y contenido que violaría `max_lines` (251 líneas):

  | Archivo | Resultado |
  |---|---|
  | `src/a.py` modificado | error `Fitness` |
  | `src/n.py` no rastreado | error `Fitness` |
  | `src/A.PY` no rastreado | error `Fitness` |
  | `src/a.txt`, `src/a.pyi` no rastreados | sin error |
  | `otro/b.py` fuera del alcance | sin error `Fitness`; sí el de `fuera de scope` existente |
  | `src/old.py` rastreado y sin cambios | sin error |
  | `src/del.py` rastreado y borrado | sin error |

  Sin repositorio Git (`diff_files` vacío) → sin error.
- AC-09: pruebas excluidas, con archivos de 251 líneas:

  | Configuración | Archivo | Resultado |
  |---|---|---|
  | por defecto | `src/test_a.py`, `src/a_test.py`, `src/conftest.py`, `tests/helper.py` | sin error |
  | `protected_tests: ["src/checks.py"]` | `src/checks.py` | sin error |
  | `protected_tests: ["src/checks.py"]` | `src/lib/src/checks.py` | error (la comparación es literal) |
  | `test_patterns: ["src/qa/**"]` | `src/qa/x.py` | sin error |
  | `test_patterns: ["src/qa/**"]` | `tests/helper.py` | error |
  | `test_patterns: []`, `protected_tests: ["tests/helper.py"]` | `tests/helper.py` | sin error |
  | `test_patterns: []` | `src/test_a.py` | error |

### Archivos preexistentes
- AC-10: funciones frente a `HEAD`, con `max_complexity` 10 y `max_params` 4:

  | `HEAD` | Árbol de trabajo | Resultado |
  |---|---|---|
  | sin `f` | `f` complejidad 11 | `complejidad 11 > límite 10` |
  | sin `f` | `f` complejidad 10 | sin error |
  | `f` 12 | `f` 12, otro cambio en el archivo | sin error |
  | `f` 12 | `f` 11 | sin error |
  | `f` 12 | `f` 13 | `complejidad 13 > límite 10` |
  | `f` 9 | `f` 11 | `complejidad 11 > límite 10` |
  | `f` 12 | renombrada `g` 12 | error en `g` |
  | `C.m` 12 | `C.m` 12 y `D.m` 12 | error solo en `D.m` |
  | `f` con 6 parámetros | `f` con 6 | sin error |
  | `f` con 6 parámetros | `f` con 7 | `parámetros 7 > límite 4` |
  | dos `f`: 12 y 3 | dos `f`: 12 y 12 | sin error (límite conocido) |
  | archivo que no parsea | `f` complejidad 11 | `complejidad 11 > límite 10` |

- AC-11: archivo frente a `HEAD`, con `max_lines` 250:

  | `HEAD` | Árbol de trabajo | Resultado |
  |---|---|---|
  | no existe | 251 líneas | `Fitness: src/a.py:1 <archivo> líneas 251 > límite 250` |
  | no existe | 250 líneas | sin error |
  | 300 | 300, con contenido distinto | sin error |
  | 300 | 299 | sin error |
  | 300 | 301 | `líneas 301 > límite 250` |
  | 200 | 251 | `líneas 251 > límite 250` |
  | 200 | 250 | sin error |

- AC-12: subir el límite en la spec permite crecer: `HEAD` 300 líneas, árbol 301, `max_lines` 301 → sin error; `f` 12 → 13 con `max_complexity` 13 → sin error.
- AC-13: tras `approve spec`, cambiar `max_lines` en `spec.json` hace que `validate` devuelva `Especificación alterada después de aprobación; se requiere reaprobación`.

### Errores e integración
- AC-14: `src/a.py` nuevo con 251 líneas, una función `f` en la línea 3 con 5 parámetros y complejidad 11, y `g` en una línea posterior con 5 parámetros producen exactamente, en este orden: `Fitness: src/a.py:1 <archivo> líneas 251 > límite 250`, `Fitness: src/a.py:3 f parámetros 5 > límite 4`, `Fitness: src/a.py:3 f complejidad 11 > límite 10`, `Fitness: src/a.py:<línea de g> g parámetros 5 > límite 4`.
- AC-15: `src/a.py` con `def (:` y `src/b.py` con `b'\xff\xfe\n'` producen cada uno un único error que empieza por `Fitness: <ruta>: no se pudo analizar:`; un tercer archivo con violación también se informa. Vía `main()`: `check` devuelve 1, escribe `ERROR: Fitness:` en stderr y sin `Traceback`.
- AC-16: con una violación en el diff: `check <slug>` devuelve 1; `check <slug> --run` devuelve 1 sin imprimir `EJECUTANDO:`; `check <slug> --no-scope` no informa `Fitness:`; `approve spec` tiene éxito; `approve close`, con revisión `APROBADO`, falla con `Puerta de calidad fallida: Fitness:`.
- AC-17: `.microharness/sdd.py` no añade imports fuera de la biblioteca estándar. `__version__` no cambia.
- AC-18: `assets/arnes-completo.md` documenta el campo en el ejemplo de `spec.json`, las definiciones de medida, la regla frente a `HEAD`, los límites conocidos y una fila en «Qué se obliga y qué NO» que diga que solo cubre Python, mide estructura y no calidad semántica, y no es control de seguridad. API-02 de `assets/proceso-versionado.md` incluye `testing.fitness`.
- AC-19: `sh .microharness/python.sh .microharness/sdd.py check testing-fitness --run` devuelve `OK` con al menos 470 pruebas. `spec/testing-fitness/spec.json` no activa la puerta.

## Fuera de alcance
Estados, roles o motor nuevos; stubs obligatorios; `chmod`; árbitro; hooks de git; SYMBOL_MAP; prohibición de mocks; regla de capas o imports de dominio; activar la puerta por defecto; aplicarla al propio repositorio en esta tarea; dependencias externas; otros lenguajes; medir complejidad de código a nivel de módulo o clase; opciones nuevas de la CLI; ampliar `count_assertions` o `seal`.
