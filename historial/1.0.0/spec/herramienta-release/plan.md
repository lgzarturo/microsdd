# CÓMO: diseño mínimo

## Situación comprobada
- `.microharness/sdd.py` (366 líneas, CRLF) define `ROOT`, `MEMORY`, `SLUG_RE`, `COMMIT_RE`, `load`, `diff_files` y `main()` con `argparse`; `main()` convierte `OSError`, `ValueError`, `KeyError`, `TypeError` y `JSONDecodeError` en código 1; los errores de uso de argparse salen con 2. No hay constante de versión.
- `COMMIT_RE` exige `fullmatch` de 1 a 72 caracteres; no sirve para clasificar asuntos históricos más largos.
- `diff_files()` no usa `core.quotePath=false`: con `diseño.md` devuelve `"spec/.../dise\303\261o.md"`, que no empieza por `spec/` (defecto de C-05; no se toca).
- `tests/test_sdd.py` carga `sdd.py` con `importlib`, reasigna `sdd.ROOT`/`sdd.MEMORY` a un directorio temporal y los restaura con `addCleanup`. No hay pruebas con Git real.
- Git global: `commit.gpgsign=true`. Git 2.55 y Python 3.12.3 disponibles.
- `.claude/hooks/pretool.py` niega Write/Edit del implementador sobre `.microharness/` antes de mirar `allowed_paths` (B-01, resuelto por autorización humana acotada a `.microharness/sdd.py`).
- `validate()` excluye `.microharness/` de la comprobación de alcance; `code_fingerprint()` solo incluye archivos que casan con `allowed_paths`, por eso `.microharness/sdd.py` figura en ellos.

## R-02 precisado por fase
R-02 exige árbol limpio, rama `main`, ninguna tarea en `proceso` y tag inexistente, pero proponer ocurre mientras el autor especifica la tarea `release-vX-Y-Z` (en `pendiente`, con `spec/` y `memory.json` sin commit) y preparar ocurre con esa tarea en `proceso`. Se precisa así:

| Fase | Sintaxis | Estado | Rama | Árbol | Tareas | Tag |
|---|---|---|---|---|---|---|
| Proponer | `sdd.py release propose` | esta tarea | `main` | limpio salvo `spec/**` y `.microharness/memory.json` | ninguna en `proceso` | no aplica |
| Preparar | `sdd.py release prepare X.Y.Z[-rc.N]` | pendiente | `main` | limpio salvo `spec/<slug>/**` y `memory.json` | `<slug>` en `proceso`; ninguna otra tarea en `proceso` | inexistente |
| Etiquetar | `sdd.py release tag X.Y.Z[-rc.N]` | pendiente | `main` | totalmente limpio | `<slug>` en `terminado` con `close`; ninguna en `proceso` | inexistente |

Las filas pendientes solo se documentan como contrato para la tarea posterior (D-05: versión sin `v`, slug `release-v` + versión con `.` → `-`, p. ej. `release-v0-2-0-rc-1`); aquí no se escribe código para ellas.

## Decisión y justificación
Cambios en `.microharness/sdd.py`, todos nuevos salvo `main()`:

1. Constantes: `__version__ = '0.1.0'` (D-02); `SUBJECT_RE = re.compile(r'^([a-z]+)(\([^)]*\))?(!)?: ')` para clasificar sin límite de longitud; `FINAL_TAG_RE = re.compile(r'^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$')`.
2. `git(*args) -> str`: `subprocess.run(['git', '-c', 'core.quotePath=false', *args], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', check=False)`; código distinto de 0 → `ValueError`. Evita el defecto de `diff_files()` sin modificarlo y decodifica asuntos con acentos en Windows.
3. `release_propose() -> None`:
   - Guardas (REQ-07): `git branch --show-current` == `main`; ningún `ROOT/spec/*/spec.json` con `state == 'proceso'`; rutas de `git status --porcelain -z --untracked-files=all` (registros separados por NUL y sin comillas, así que los espacios y la `ñ` llegan literales): cada registro es `XY ruta`; si X o Y es `R` o `C`, el registro NUL siguiente es la ruta de origen y se comprueban AMBAS rutas, origen y destino. Cada ruta debe empezar por `spec/` o ser `.microharness/memory.json`; así `git mv README.md spec/README.md` se rechaza por el origen. Fallo → `ValueError` con la precondición.
   - Base: máximo por tupla numérica entre `git tag --merged HEAD --list v*` que casan con `FINAL_TAG_RE`. Asuntos: `git log --reverse --format=%s <tag>..HEAD` o `git log --reverse --format=%s HEAD` sin tag.
   - Clasificación e incremento según REQ-03/REQ-04. Sin tag: la propuesta es `__version__` leída con `re.search(r"^__version__ = '([^']*)'", texto, re.M)` sobre `ROOT/.microharness/sdd.py`, quitando `-rc.N` (H-01); así las pruebas usan el archivo del temporal y no la constante del módulo.
   - Sin ningún incremento → `ValueError('... sin incremento; no se publica versión')` (D-04).
   - Impresión: `Último tag: <tag|(ninguno)>`, `<grupo>: <asunto>` por commit, `Versión propuesta: X.Y.Z`.
4. `main()`: `p.add_argument('--version', action='version', version=f'MicroSDD {__version__}')` (D-03); `rel = sub.add_parser('release')` con `rel.add_subparsers(dest='action', required=True)` y solo `propose` (D-01). La tarea posterior añade `prepare`/`tag` en ese mismo subparser.

En `assets/proceso-versionado.md`:
- «Estado actual»: solo la línea «No existen `CHANGELOG.md` ni `VERSION`, y `.microharness/sdd.py` no define ninguna constante de versión» pasa a decir que no existen `CHANGELOG.md` ni `VERSION` y que `sdd.py` define `__version__` (`0.1.0`), expuesta con `--version`.
- Última sección: título «Herramienta de release»; párrafo inicial que diga que existen `--version` y `release propose` y que `release prepare` y `release tag` están pendientes de su propia tarea; conservar R-01 a R-07, precisando R-02 por fase según la tabla anterior (con «ninguna otra tarea en `proceso`» para la preparación); la frase de la fuente única pasa de propuesta a hecho.

## Alternativas descartadas
- Hacer las tres fases en una tarea: el programador eligió dividir (D-09).
- Leer la versión solo de la constante del módulo: impediría probar el caso sin tags con otros valores sin parchear el módulo; se lee el archivo de `ROOT`.
- Omitir la comprobación de árbol en `propose`: permitiría proponer con código sin commit fuera de specs.
- Corregir `diff_files()` y reutilizarlo: es el defecto de C-05 y amplía el alcance.
- `git describe`: elige el tag más cercano topológicamente, no el mayor, y necesita excluir `-rc`.
- Crear ya `release_plan()` separado para reutilizar en `prepare`: especulativo; se extraerá en la tarea posterior si hace falta.

## Invariantes y riesgos
- Invariante: `release propose` no escribe archivos, tags, ramas ni memoria ni ejecuta `push`; solo ejecuta comandos Git de lectura.
- Invariante: toda guarda fallida sale con 1; argparse sigue saliendo con 2.
- Invariante: todas las llamadas Git usan `cwd=ROOT`; las pruebas reasignan `ROOT`.
- Riesgo: `commit.gpgsign=true` global hace fallar los commits de prueba → configurar en cada repo temporal `user.name`, `user.email`, `commit.gpgsign=false` y `tag.gpgsign=false`.
- Riesgo: `text=True` sin `encoding` decodifica con cp1252 en Windows → `encoding='utf-8'` en el helper y una prueba con asunto con `ñ`.
- Riesgo: CRLF en `sdd.py` → la regex de lectura de `__version__` no ancla `$`; el implementador edita sin convertir finales de línea.
- Riesgo: el hook sigue negando `.microharness/`; la edición se apoya en la autorización humana acotada de B-01 y el revisor comprueba que solo cambió `.microharness/sdd.py` (AC-10).
- Efecto secundario: el comando de verificación de la tarea terminada `proceso-versionado` (exige el título «Herramienta de release (futura)» y «no existe») dejará de pasar sobre el árbol nuevo; es histórico y no se reejecuta en ningún flujo.
- Efecto secundario: API-01 y el paso 9 del flujo no mencionan `release` ni `--version` (D-08); el commit de esta tarea es `feat`.

## Decisiones
Registradas por el programador: D-01, D-02, D-03, D-04, D-05 (solo contrato futuro), D-06, D-08, D-09 y D-10; B-01 resuelto con autorización acotada. D-07 no aplica a esta tarea. No quedan decisiones bloqueantes.
