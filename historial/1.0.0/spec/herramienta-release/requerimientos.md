# QUÉ: requisitos

## Objetivo
Primera de dos tareas de la herramienta de release (D-09). Añadir a `.microharness/sdd.py`, solo con la biblioteca estándar, la fuente única de versión decidida en H-04 (constante `__version__ = '0.1.0'` expuesta con `sdd.py --version`) y el subcomando de solo lectura `sdd.py release propose`, que propone la siguiente versión según «Reglas de incremento» y «Fase 0.y.z» (R-03) con las guardas de R-02 precisadas para su fase. Actualizar lo mínimo de `assets/proceso-versionado.md` para que no sea falso. `release prepare` y `release tag` quedan para una tarea posterior.

## Precondiciones
- Hechos comprobados en el repositorio (2026-10-12):
  - `git tag` no devuelve tags; no existen `CHANGELOG.md` ni `VERSION`; `.microharness/sdd.py` no define constante de versión.
  - `python -m unittest discover -s tests` pasa con 10 pruebas. En este entorno se usa `python`; `python3` no existe.
  - Las pruebas existentes aíslan el repositorio reasignando `sdd.ROOT` y `sdd.MEMORY` a un `tempfile.TemporaryDirectory`.
  - La configuración Git global tiene `commit.gpgsign=true`; las pruebas que hagan commits deben desactivarlo en la configuración local del repositorio temporal.
  - `diff_files()` llama a Git sin `core.quotePath=false`: las rutas con `ñ` (por ejemplo `diseño.md`) salen entre comillas y escapadas.
  - `.microharness/sdd.py` y `tests/test_sdd.py` tienen finales de línea CRLF en el árbol de trabajo.
- Decisiones del programador registradas en `.microharness/memory.json`: H-01, H-03, H-04, H-07 y H-08 de proceso-versionado; para esta tarea, D-01 (subcomando anidado `release propose`), D-02 (`__version__`), D-03 (`MicroSDD 0.1.0`), D-04 (sin incremento, código 1), D-06, D-08 (alcance documental mínimo), D-09 (división) y D-10 (sellado tras revisión humana del RED).
- B-01: el hook `.claude/hooks/pretool.py` niega al implementador Write/Edit sobre `.microharness/`. Autorización humana explícita y acotada: en esta tarea el implementador puede editar únicamente `.microharness/sdd.py`; nunca `.microharness/memory.json` ni `.claude/`. El hook no se modifica.
- Esta spec no está aprobada; la aprobación la registra el líder tras la respuesta expresa del humano.

## Requisitos EARS
- REQ-01: WHEN se ejecute `sdd.py --version`, THE herramienta SHALL imprimir `MicroSDD <__version__>` y terminar con código 0; `__version__` SHALL definirse una única vez en `.microharness/sdd.py` con valor `0.1.0`.
- REQ-02: WHEN se ejecute `sdd.py release propose` y se cumplan sus precondiciones, THE herramienta SHALL leer los asuntos de commit desde el mayor tag final `vX.Y.Z` alcanzable desde `HEAD` (o desde el inicio si no hay ninguno), imprimir `Último tag: <tag>` o `Último tag: (ninguno)`, una línea `<grupo>: <asunto>` por commit y `Versión propuesta: X.Y.Z`, y terminar con código 0.
- REQ-03: THE clasificación SHALL asignar: asunto con `!` → «Incompatible»; `feat` → «Añadido»; `fix` o `perf` → «Corregido»; cualquier otro tipo o asunto no convencional → «Otros» sin incremento. Los tags `vX.Y.Z-rc.N` SHALL NOT usarse como base.
- REQ-04: WHILE la versión base tenga mayor 0, THE propuesta SHALL aplicar `!` → MINOR y `feat`/`fix`/`perf` → PATCH. WHILE la versión base sea ≥ 1.0.0, THE propuesta SHALL aplicar `!` → MAJOR, `feat` → MINOR y `fix`/`perf` → PATCH. THE propuesta SHALL tomar el mayor incremento y poner a 0 los componentes inferiores.
- REQ-05: IF no existe ningún tag final, THEN THE propuesta SHALL ser el valor de `__version__` leído de `ROOT/.microharness/sdd.py` sin sufijo `-rc.N` (H-01).
- REQ-06: IF ningún commit del rango produce incremento, THEN `release propose` SHALL terminar con código 1 con un mensaje que contenga `sin incremento` y SHALL NOT imprimir `Versión propuesta`.
- REQ-07: IF la rama actual no es `main`, o hay alguna tarea en `proceso`, o el árbol tiene cambios rastreados o archivos no rastreados fuera de `spec/**` y `.microharness/memory.json` (en un renombrado o copia cuentan la ruta de origen y la de destino, y basta con que una quede fuera), THEN `release propose` SHALL terminar con código 1 con un mensaje que identifique la precondición.
- REQ-08: THE subcomando `release propose` SHALL NOT modificar archivos, tags, ramas ni memoria, ni ejecutar `push` (R-06).
- REQ-09: WHEN se complete la tarea, THE documento `assets/proceso-versionado.md` SHALL reflejar que `__version__`, `--version` y `release propose` existen, que `release prepare` y `release tag` siguen pendientes, y SHALL precisar R-02 por fase (incluida «ninguna otra tarea en `proceso`» para la preparación futura), conservando R-01 a R-07 y dejando intactas las demás secciones salvo una línea de «Estado actual».
- REQ-10: WHEN se ejecute la suite, THE pruebas nuevas SHALL operar solo sobre repositorios Git temporales con `sdd.ROOT` y `sdd.MEMORY` reasignados, y SHALL NOT crear tags, commits ni archivos en el repositorio real.
- REQ-11: IF el diff de la tarea modifica `.claude/`, `CLAUDE.md` o, en `.microharness/memory.json`, algo distinto de la entrada `tasks.herramienta-release` y de `project`, THEN THE revisión SHALL rechazarla.

## Criterios de aceptación
- AC-01: `python .microharness/sdd.py --version` imprime exactamente `MicroSDD 0.1.0` y sale con 0; `.microharness/sdd.py` contiene una sola línea `__version__ = '0.1.0'`. Verificación: prueba unitaria por subproceso y comandos segundo y tercero de `spec.json`.
- AC-02: En un repositorio temporal con tag `v0.1.0`, `release propose` imprime `Versión propuesta: 0.1.1` si tras el tag hay `fix:`, `feat:` o `perf:` (cada caso por separado), y `Versión propuesta: 0.2.0` si además hay un asunto con `!` (por ejemplo `docs!: x`); un tag posterior `v0.2.0-rc.1` no cambia la base; `docs:`, `test:`, `refactor:`, `chore:` y un asunto no convencional aparecen con el grupo `Otros`; un asunto con `ñ` se imprime sin alterar. Verificación: pruebas unitarias.
- AC-03: Con tag `v1.2.3`: `fix:` o `perf:` → `1.2.4`; `feat:` → `1.3.0`; `refactor!:` → `2.0.0`; con varios commits se toma el mayor incremento. Verificación: pruebas unitarias.
- AC-04: Sin tags y con `__version__ = '0.1.0'` en `ROOT/.microharness/sdd.py`, `release propose` con commits `feat:` desde el inicio imprime `Último tag: (ninguno)` y `Versión propuesta: 0.1.0`; con `__version__ = '0.1.0-rc.1'` también propone `0.1.0`. Verificación: pruebas unitarias.
- AC-05: Si todos los commits del rango son `docs:`, `test:`, `refactor:`, `chore:` o no convencionales, `release propose` sale con 1 vía `main()`, el error contiene `sin incremento` y la salida no contiene `Versión propuesta`. Verificación: prueba unitaria.
- AC-06: `release propose` sale con 1 vía `main()` en cada caso: rama `otra`; una tarea con estado `proceso`; un archivo rastreado modificado fuera de las rutas permitidas; un archivo no rastreado fuera de ellas; un renombrado preparado desde fuera hacia `spec/` (`git mv README.md spec/README.md`). Con cambios solo en `spec/<slug>/diseño.md` (ruta con `ñ`) y `.microharness/memory.json`, sale con 0; con un archivo nuevo en una ruta con espacios dentro de `spec/` (por ejemplo `spec/<slug>/nota con espacios.md`), también sale con 0. Verificación: pruebas unitarias.
- AC-07: Tras cada ejecución de `release propose` (con éxito o con error), `git status --porcelain`, `git tag` y `git rev-parse HEAD` del repositorio temporal son idénticos a los previos; `sdd.py release` sin acción sale con 2 (argparse). Verificación: pruebas unitarias.
- AC-08: El comando `python -c` de `spec.json` imprime `OK docs`: la última sección `##` de `assets/proceso-versionado.md` es «Herramienta de release», contiene `- **R-01**` a `- **R-07**`, `release propose`, `--version`, `__version__`, `pendiente` y `ninguna otra tarea`, y no contiene `Hoy no existe`; «Estado actual» contiene `__version__` y no `ninguna constante`, con como máximo una línea eliminada y una añadida respecto de `HEAD`; el preámbulo y las demás secciones son idénticos a `HEAD`. Verificación: comando `python -c`; el revisor confirma que el texto coincide con lo implementado y no presenta `prepare`/`tag` como existentes.
- AC-09: `python -m unittest discover -s tests` sale con 0 con las 10 pruebas previas sin modificar; `git tag` y `git status --porcelain` del repositorio real no cambian por ejecutar la suite. Verificación: `python .microharness/sdd.py check herramienta-release --run` y comparación de `git tag`/`git status --porcelain` antes y después.
- AC-10: `git status --porcelain` no muestra rutas bajo `.claude/` ni `CLAUDE.md`; en `.microharness/memory.json` solo difieren respecto de `HEAD` la entrada `tasks.herramienta-release` y `project`; fuera de `spec/herramienta-release/` y `.microharness/memory.json` solo cambian `.microharness/sdd.py`, `tests/test_sdd.py` y `assets/proceso-versionado.md`; en `sdd.py` las funciones existentes no cambian salvo `main()`. Verificación: comando `python -c` de `spec.json` y revisión del diff.

## Fuera de alcance
- `release prepare` y `release tag` (escritura de `CHANGELOG.md`, actualización de la constante, creación de tags): tarea posterior. Tampoco se añade código especulativo para ellas.
- Crear `CHANGELOG.md`, `VERSION` o tags reales; `push`; releases de GitHub.
- Modificar el hook, `.claude/`, `CLAUDE.md`, `README.md`, `docs/` o `assets/decisiones-diseno.md`.
- Modificar en `assets/proceso-versionado.md` secciones distintas de la última y de una línea de «Estado actual» (D-08: API-01 y el paso 9 del flujo quedan sin tocar).
- Corregir `core.quotePath` en `diff_files()` o refactorizar funciones existentes.
- Leer el pie `BREAKING CHANGE` del cuerpo (H-07: solo `!` en el asunto).
- Mutation testing con herramientas externas.
