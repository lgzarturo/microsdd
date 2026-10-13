# CÓMO: diseño mínimo

## Situación comprobada
- `.microharness/sdd.py`, `diff_files()` (líneas 130-140): la tupla `commands` contiene `['git', 'diff', '--name-only', 'HEAD']` y `['git', 'ls-files', '--others', '--exclude-standard']`; cada uno se ejecuta con `subprocess.run(..., capture_output=True, text=True, check=False)` y se aceptan sus líneas solo si `returncode == 0`.
- Consumidores: `code_fingerprint()` (línea 146, une `ROOT / filename` y codifica con UTF-8) y `validate()` (línea 231, exime prefijos `spec/`, `docs/`, `.microharness/` y aplica `path_allowed`). Ambos esperan rutas literales.
- `tests/test_sdd.py`, `MicroSDDTests.setUp`: redirige `sdd.ROOT` a un `TemporaryDirectory`, crea `spec/fix-sesiones/` (con `diseño.md`) y fija `allowed_paths = ['src/**', 'tests/**']`. Hoy el tmp no es repositorio git, por lo que `diff_files()` devuelve `[]` en las pruebas existentes.

## Decisión y justificación
Cambio en una sola línea lógica de `diff_files()`:
1. Anteponer `-c core.quotePath=false` a ambos comandos de la tupla: `['git', '-c', 'core.quotePath=false', 'diff', ...]` y `['git', '-c', 'core.quotePath=false', 'ls-files', ...]`. Anula cualquier configuración local o global y hace que git emita bytes UTF-8 crudos.
2. En el `subprocess.run` del bucle, sustituir `text=True` por `encoding='utf-8'` (que también activa modo texto). Así la decodificación no depende de la codificación local (cp1252 en Windows).

Sobre `errors`: no se añade (queda el `strict` por defecto). Justificación: con `quotePath=false` git emite los bytes del nombre tal cual; en Windows y en repos normales son UTF-8 válido. Un nombre con bytes no UTF-8 (solo posible en POSIX) es fuera de alcance; con `strict` produce un `UnicodeDecodeError` visible en lugar de una ruta alterada en silencio. `errors='replace'` daría una ruta inexistente que `code_fingerprint` sellaría como `<deleted>`; `errors='surrogateescape'` haría fallar `filename.encode('utf-8')` en `code_fingerprint`. Ninguna mejora el resultado y ambas añaden casos sin necesidad actual (YAGNI). Si el líder prefiere fallo cerrado sin excepción, la alternativa sería `errors='replace'` (el archivo seguiría reportándose fuera de alcance).

Prueba (TDD): un método nuevo en `MicroSDDTests`, decorado con `@unittest.skipUnless(shutil.which('git'), ...)`, que ejecuta `git init` en `sdd.ROOT` y `git config core.quotePath true` (para que el resultado no dependa de la configuración global del desarrollador), sin commits; crea `fuera/configuración.txt`; y comprueba AC-01..AC-03. Sin commits `git diff HEAD` devuelve código distinto de 0 y el código ya lo ignora; `ls-files --others` cubre los archivos no rastreados. `git init` sin commit no requiere `user.name`/`user.email`. Se usa `subprocess.run([...], cwd=sdd.ROOT, check=True, capture_output=True)`; `shutil`/`subprocess` se importan si no lo están ya.

## Alternativas descartadas
- Usar `-z` y separar por `\0`: también evita el entrecomillado, pero cambia el parseo y añade más diff que `core.quotePath=false`; innecesario.
- Desentrecomillar en Python la salida escapada de git: más código y frágil.
- Leer bytes (`text=False`) y decodificar a mano: equivalente a `encoding='utf-8'` con más líneas.
- Cambiar la llamada `git rev-parse`: su salida no se usa; fuera de alcance.

## Invariantes y riesgos
- Invariante: `diff_files()` mantiene firma, orden (`sorted`) y tolerancia a `returncode != 0`.
- Invariante: rutas ASCII se devuelven igual que antes.
- Riesgo: git anterior a 1.7 sin soporte de `-c`; despreciable. Mitigación: ninguna.
- Riesgo: la prueba nueva convierte el tmp en repo git; si el tmp estuviera dentro de otro repo, `git init` crea uno anidado propio y `ROOT/.git` existe, así que el resultado es determinista.
- Riesgo: nombres no UTF-8 lanzan `UnicodeDecodeError` (ver decisión sobre `errors`).
- Efecto secundario esperado: `python .microharness/sdd.py check <slug>` sin `--no-scope` deja de fallar por `diseño.md` en specs nuevas.
