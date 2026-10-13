# CÓMO: diseño mínimo

## Situación comprobada
- `.microharness/sdd.py`, `diff_files()` (líneas 130-140): ejecuta `git diff --name-only HEAD` y `git ls-files --others --exclude-standard` con `subprocess.run(..., capture_output=True, text=True, check=False)` y toma `r.stdout.splitlines()`.
- Consumidores: `validate()` (chequeo de alcance, línea ~232, usa `filename.startswith(('spec/', 'docs/', '.microharness/'))`) y `code_fingerprint()` (líneas 143-151, lee `ROOT / filename` o `<deleted>`).
- Fallo 1: git entrecomilla y escapa en octal las rutas no ASCII (`core.quotePath=true` por defecto). La ruta empieza por `"`, no por `spec/`.
- Fallo 2: `text=True` decodifica con la codificación del locale (cp1252 en Windows), lo que produce mojibake aunque se desactive el entrecomillado.
- Evidencia del líder: `git ls-files -z --others --exclude-standard` con `encoding='utf-8'` y separación por `'\0'` devuelve `'spec/instalador-uvx/dise\xf1o.md'`, y el archivo existe.
- `tests/test_sdd.py`: carga `sdd.py` con `importlib`, redirige `sdd.ROOT`/`sdd.MEMORY` a un `TemporaryDirectory` y crea la tarea `fix-sesiones` en `setUp`. El temporal no es repositorio Git, así que hoy `diff_files()` devuelve `[]` en esas pruebas.

## Excepción autorizada
Excepción autorizada por el programador 2026-10-12: solo para esta tarea el implementador puede editar `.microharness/sdd.py`, pese a la regla del hook que normalmente lo prohíbe. No modifica el hook ni amplía permisos.

## Decisión y justificación
Cambio único y local en `diff_files()`:
- Añadir `-z` a ambos comandos: `['git', 'diff', '--name-only', '-z', 'HEAD']` y `['git', 'ls-files', '-z', '--others', '--exclude-standard']`. Con `-z` git emite las rutas literales (sin comillas ni escapes) separadas por NUL, sin depender de `core.quotePath`.
- Sustituir `text=True` por `encoding='utf-8'` en esa llamada a `subprocess.run` (git emite los nombres como bytes UTF-8 en Windows y en los sistemas habituales).
- Separar con `r.stdout.split('\0')` y descartar vacíos (el último elemento tras el NUL final).
- Mantener intactos: la detección de repositorio (primer `subprocess.run` con `text=True`, que no procesa rutas), el manejo de `returncode`, el `set` y el `sorted`.

KISS/YAGNI: es la corrección mínima que resuelve ambos fallos en el único punto donde se obtienen rutas; no se añaden funciones auxiliares, parámetros ni configuración.

## Alternativas descartadas
- `git -c core.quotePath=false`: resuelve el entrecomillado pero no el mojibake del locale; además no protege rutas con saltos de línea o comillas.
- Decodificar a mano los escapes octales: frágil y duplica lógica de git.
- Cambiar `core.quotePath` en la configuración del repositorio: fuera de alcance, no portable y afecta al usuario.
- `errors='surrogateescape'` o leer bytes y decodificar después: complejidad sin necesidad comprobada.
- Ajustar `validate()` o `code_fingerprint()`: el defecto está en la fuente de rutas; tocar consumidores sería un parche sintomático.

## Pruebas (TDD)
Nuevas pruebas en `tests/test_sdd.py`, en la clase existente o en una nueva que reutilice el mismo patrón de `sdd.ROOT` temporal:
- Inicializar Git en `sdd.ROOT` (`git init`), configurar `user.email` y `user.name` locales (`git config` sin `--global`) y crear un commit inicial (necesario para `git diff ... HEAD`). Para aislarse de configuración global del desarrollador, puede pasarse `-c core.quotePath=true` solo en las llamadas de la prueba si se desea asegurar el caso por defecto; no es obligatorio.
- AC-01: archivo rastreado no ASCII (por ejemplo `src/módulo.py`) incluido en el commit inicial y luego modificado; `spec/x/diseño.md` sin seguimiento; comparar el resultado exacto de `diff_files()` y comprobar `is_file()`.
- AC-02: commit inicial que no incluya `spec/fix-sesiones/`; `validate('fix-sesiones')` no debe reportar `spec/fix-sesiones/diseño.md` fuera de scope.
- AC-03: archivo permitido no ASCII (por ejemplo `src/módulo.py`); calcular `code_fingerprint(['src/**'])`, cambiar contenido, recalcular y comprobar que difiere. Con el código actual el sello no cambia porque se lee `<deleted>` o la ruta entrecomillada no coincide con el patrón.
- AC-04: archivo sin seguimiento `src/con espacio.py`; aparece con ruta exacta.
- AC-05: suite completa en verde.

## Invariantes y riesgos
- Invariante: `diff_files()` sigue devolviendo `list[str]` ordenada, sin duplicados, con rutas relativas en formato POSIX; devuelve `[]` fuera de un repositorio Git.
- Invariante: un comando git fallido (código distinto de cero) se sigue ignorando.
- Efecto secundario esperado: rutas no ASCII que antes aparecían entrecomilladas ahora se evalúan con `path_allowed`; un archivo no ASCII fuera de `spec/`, `docs/` o `.microharness/` y no permitido se reportará correctamente como fuera de scope (antes también se reportaba, pero con nombre ilegible).
- Efecto secundario esperado: `code_fingerprint()` cambia para tareas con archivos permitidos no ASCII; un `review_fingerprint` registrado antes de la corrección podría no coincidir y exigir nueva revisión. Riesgo bajo; no hay tareas en proceso conocidas que dependan de ello.
- Riesgo: un `.git` con nombres no UTF-8 (repositorios heredados con codificación legacy) lanzaría `UnicodeDecodeError`. Se acepta: fuera de alcance y no observado.
- Riesgo de pruebas: en Windows los objetos de `.git` son de solo lectura; `TemporaryDirectory.cleanup()` en Python >= 3.8 reintenta con cambio de permisos, pero si falla deberá documentarse en lugar de deshabilitar la limpieza a ciegas.
- Riesgo de pruebas: `git commit` puede verse afectado por hooks o firma global (`commit.gpgsign`); mitigación: en la prueba usar `git -c commit.gpgsign=false commit` o `--no-verify` si fuese necesario.
- `.microharness/` está excluido del chequeo de alcance de `validate()` por diseño; se incluye en `allowed_paths` solo por trazabilidad.
