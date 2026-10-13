# CÓMO: diseño mínimo

## Situación comprobada
- `src/microsdd/installer.py`:
  - `remediation(problem, location)` (68-85): mensaje centrado en `python3` (alias de Store en `WindowsApps`, `python3.exe`, `uv python install … --default`).
  - `check_python(python)` (88-106): si `python is None`, busca `python3.exe`/`python3` con `shutil.which` sobre `filter_path(PATH, sys.prefix, sys.base_prefix)`; ejecuta `VERSION_CODE` y exige ≥3.10. Es el único uso de `re` y de `VERSION_CODE`.
  - `install(source, target, *, python, home, force, dry_run)` (171-232): llama a `check_python` tras `check_target`; línea 214 `[*python, '.microharness/sdd.py', 'init']`; línea 216 mensaje `python3 .microharness/sdd.py init falló`; línea 218 smoke `[*python, '.claude/hooks/pretool.py']`.
  - `main()` (243) pasa `python=None`.
- `.claude/settings.json`: hook exec `uv run --no-project --quiet --python ">=3.10" ${CLAUDE_PROJECT_DIR}/.claude/hooks/pretool.py`, `onFailure: block`. En Windows la forma exec requiere un `.exe` real.
- `pyproject.toml`: `requires-python = ">=3.10"`; por tanto `sys.executable` del instalador es ≥3.10.
- `.microharness/sdd.py init` y `pretool.py` solo usan biblioteca estándar; `init` solo invoca `git` si no existe `.git`.
- `tests/test_installer.py`: `run_install(…, python=…)` inyecta `[sys.executable]`; `test_broken_or_old_python3_fails_without_writing` (AC-08 de `instalador-uvx`) y `test_windows_ignores_python3_cmd_shim` prueban el requisito que se elimina; `test_smoke_requires_reviewer_read_only_reason` pasa `python=[sys.executable]`. No figura en `protected_tests` de ninguna tarea. `tests/test_sdd.py` sí figura como protegido en `deteccion-python-multiplataforma` y `herramienta-release` (ambas terminadas): queda excluido.
- `README.md` líneas 74 y 84 describen el requisito de `python3`.
- Local: `uv 0.12.21`; `uvx --help` lista `-n, --no-cache`.

## Decisión y justificación
1. **Precondición `uv`**: sustituir `check_python` por `check_uv(uv: list[str] | None) -> str | None`.
   - Si `uv is None`: `shutil.which('uv.exe' if sys.platform == 'win32' else 'uv', path=filter_path(...))`. Igual que antes con `python3.exe`: en Windows solo cuenta el `.exe`, porque la forma exec de Claude Code no resuelve `.cmd`/`.bat`. Se conserva `filter_path` (ya probado) para no detectar binarios del entorno aislado de `uvx`.
   - Ejecutar `[*uv, '--version']` (timeout 60, `capture_output`); éxito si `returncode == 0`. No se analiza la versión (YAGNI: el hook no exige una mínima).
   - Errores (no encontrado, `OSError`/`SubprocessError`, código ≠ 0) → `remediation(problem)`, que nombra `uv`, explica que el hook se ejecuta con `uv run` en forma exec y lista la instalación por SO (Windows: instalador PowerShell oficial o `winget install astral-sh.uv`, «se exige `uv.exe`; los shims `.cmd`/`.bat` no sirven»; macOS: `brew install uv` o `curl -LsSf https://astral.sh/uv/install.sh | sh`; Linux: el `curl`).
   - Se eliminan la rama del alias de Microsoft Store (no aplica a `uv`), el parámetro `location`, `VERSION_CODE`, `check_python` y el `import re` que queda sin uso.
2. **`init` y smoke con `sys.executable`**: las líneas 214 y 218 pasan a `[sys.executable, …]`. Es lo más simple y verificable: el instalador ya corre en un Python ≥3.10 garantizado por `requires-python`, ambos scripts son solo stdlib y la prueba puede comprobar el argv exacto. Mensaje de error: `ERROR: .microharness/sdd.py init falló (código N).`
3. **Interfaz**: `install(source, target, *, uv, home, force=False, dry_run=False)`. El parámetro `python` se renombra a `uv` (misma semántica de inyección para pruebas; `None` = buscar en PATH). `main()` pasa `uv=None`. No se añaden más parámetros.
4. **Pruebas** (`tests/test_installer.py`):
   - `run_install` inyecta por defecto `uv=[sys.executable, '-c', 'print("uv 0.0.0")']` (el `--version` añadido llega como argumento ignorado).
   - Reemplazar `test_broken_or_old_python3_fails_without_writing` por la prueba de `uv` roto (AC-02) y `test_windows_ignores_python3_cmd_shim` por la de `uv.cmd` (AC-04); añadir AC-03 (sin `uv`), AC-05 (sin `python3`) y AC-06 (argv de init/smoke mediante `mock.patch.object(installer.subprocess, 'run', side_effect=<run original>)`, registrando las llamadas).
   - Adaptar `test_smoke_requires_reviewer_read_only_reason` al parámetro `uv`.
5. **README**: reescribir la frase de precondiciones (línea 74) y la de `init` (línea 84); añadir, tras la recomendación de fijar un tag, la nota: «Para probar el instalador desde una copia local usa `uvx --no-cache --from <ruta o git+url> microsdd install`, para no reutilizar un wheel en caché».

## Alternativas descartadas
- **Smoke test con `uv run --no-project --quiet --python ">=3.10" .claude/hooks/pretool.py`** (réplica exacta del hook): más fiel, pero puede descargar un intérprete, depende de red/caché y complica la prueba (requiere `uv` real o skip). Queda como pregunta abierta para el líder.
- **Mantener `python3` como alternativa a `uv`**: contradice el objetivo; el hook no lo usa.
- **`sh .microharness/python.sh`** para init/smoke: depende de `sh` (no garantizado en Windows sin Git Bash) y añade un salto innecesario.
- **Exigir versión mínima de `uv`**: no hay requisito documentado.

## Invariantes y riesgos
- Invariante: ninguna escritura antes de que `check_target` y `check_uv` pasen (cero escrituras ante fallo de precondición).
- Invariante: el smoke test sigue exigiendo `deny` + «solo lectura».
- Riesgo: `uv --version` funciona pero `uv run --python ">=3.10"` no puede obtener un intérprete (sin red ni Python local); el hook bloquearía todo (`onFailure: block`, falla cerrada). El smoke con `sys.executable` no lo detecta (ver pregunta abierta).
- Riesgo: en Linux el directorio de `git` (`/usr/bin`) puede contener `python3` o `uv`; AC-03/AC-05 se omiten explícitamente en ese caso en lugar de dar falsos positivos.
- Riesgo: AC-06 observa `subprocess.run`; es el comportamiento exigido (qué se ejecuta), no un detalle interno arbitrario.
- Efecto secundario: se sustituyen dos pruebas de la tarea cerrada `instalador-uvx` (AC-08 y shim `.cmd`) porque cambia el requisito; quedan reemplazadas por sus equivalentes con `uv`.
- `docs/AGENT.md` y `docs/specificaciones.md` (fila `instalador-uvx`) quedan desactualizados; corresponde al líder.
