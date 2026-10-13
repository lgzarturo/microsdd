# QUÉ: requisitos

## Objetivo
Alinear el instalador `microsdd install` (`src/microsdd/installer.py`) con el hook actual: exigir como precondición `uv` ejecutable real en `PATH` (lo que el hook necesita realmente) en lugar de `python3`, y ejecutar `sdd.py init` y el smoke test del hook sin invocar `python3`.

Motivo comprobado: `.claude/settings.json` lanza el hook en forma exec con `uv run --no-project --quiet --python ">=3.10" …` y `onFailure: block`; el hook ya no depende de `python3`. Sin embargo, `check_python()` (líneas 88-106) exige `python3` (en Windows `python3.exe`) que se ejecute y reporte ≥3.10, e `install()` (líneas 214 y 218) ejecuta `sdd.py init` y el smoke test con ese `python3`. En Windows 11 + Git Bash, `python3` es el stub de Microsoft Store (exit 49) y el instalador se niega a instalar aunque el arnés funcionaría. `README.md` (líneas 74 y 84) documenta el requisito de `python3`.

## Precondiciones
- P-01: Para ejecutar el instalador: Python ≥3.10 (lo garantiza `requires-python = ">=3.10"` de `pyproject.toml` al lanzarlo con `uvx`) y `git` en `PATH`.
- P-02: Para que la instalación prospere: `uv` en `PATH` como ejecutable real (en Windows `uv.exe`; los shims `.cmd`/`.bat` no sirven en forma exec).
- P-03: Para las pruebas: Python ≥3.10 y `git`; las pruebas específicas de Windows se omiten con `skipUnless` en otros SO.
- P-04: Sin dependencias de terceros (solo biblioteca estándar).

## Requisitos EARS
- REQ-01: WHEN `microsdd install` se ejecute sin un intérprete inyectado, THE instalador SHALL buscar `uv` en el `PATH` (filtrado con `filter_path`), en Windows exclusivamente `uv.exe`, y comprobar que `uv --version` termina con código 0 antes de escribir cualquier archivo.
- REQ-02: IF `uv` no se encuentra, no se puede ejecutar o `uv --version` termina con código distinto de 0, THEN el instalador SHALL terminar con código 1, sin escribir nada, mostrando un mensaje que nombre `uv` y explique cómo instalarlo según el SO (en Windows, que se exige `uv.exe` y no un shim `.cmd`/`.bat`).
- REQ-03: THE instalador SHALL NOT exigir, buscar ni ejecutar `python3` en ningún punto (precondición, `sdd.py init` ni smoke test).
- REQ-04: WHEN la instalación haya escrito los archivos, THE instalador SHALL ejecutar `.microharness/sdd.py init` y el smoke test de `.claude/hooks/pretool.py` con `sys.executable` (el intérprete que ya ejecuta el instalador).
- REQ-05: IF `sdd.py init` falla, THEN el instalador SHALL terminar con código 1 con un mensaje que no mencione `python3`.
- REQ-06: WHERE `README.md` describa la instalación, THE texto SHALL indicar que se exige `uv` ejecutable real (en Windows `uv.exe`) en lugar de `python3`, que `sdd.py init` y el smoke test se ejecutan con el Python del propio instalador, y SHALL incluir la nota de usar `uvx --no-cache --from <ruta o git+url> microsdd install` al probar el instalador desde una copia local.
- REQ-07: THE resto del comportamiento del instalador (validación de destino, plan, idempotencia, conflictos, `--force`, `--dry-run`, alterno de settings, verificación de «solo lectura» del smoke test, códigos 0/1/2) SHALL mantenerse sin cambios.

## Criterios de aceptación
- AC-01 (REQ-01): Con un `uv` inyectado que termina con código 0 (p. ej. `[sys.executable, '-c', 'print("uv 0.0.0")']`), la instalación limpia termina con código 0 y deja los archivos del manifiesto, `docs/`, `spec/` y `.microharness/memory.json` igual que hoy (prueba AC-01 existente adaptada).
- AC-02 (REQ-02): Con un `uv` inyectado que termina con código distinto de 0 (p. ej. sale con 49), el instalador termina con código 1, la salida contiene `uv` y el snapshot del repositorio no cambia.
- AC-03 (REQ-01, REQ-02): Con `uv=None` y `PATH` restringido al directorio de `git` (sin `uv` ni `uv.exe`; si existiera, la prueba se omite), el instalador termina con código 1, la salida contiene `uv` y el snapshot no cambia.
- AC-04 (REQ-01, REQ-02, solo Windows): Con `uv=None` y `PATH` = [directorio con `uv.cmd` que reenvía a algo válido, directorio de `git`], el instalador termina con código 1, la salida contiene `.cmd` y el snapshot no cambia.
- AC-05 (REQ-03): Con `PATH` restringido al directorio de `git` sin `python3` (la prueba se omite si `shutil.which('python3', path=…)` lo encuentra) y un `uv` inyectado válido, el instalador termina con código 0 y la salida no contiene `python3`.
- AC-06 (REQ-03, REQ-04): Durante una instalación limpia con `uv` inyectado válido, todas las llamadas a `subprocess.run` cuyo argv incluya `.microharness/sdd.py` o `.claude/hooks/pretool.py` tienen `argv[0] == sys.executable`, y ninguna llamada con `argv[0]` distinto de `sys.executable` tiene un nombre base que empiece por `python3`.
- AC-07 (REQ-07): El smoke test sigue exigiendo `deny` por «solo lectura»: con un `pretool.py` que deniega por otro motivo, el instalador termina con código 1 (prueba AC-13 existente adaptada al nuevo parámetro).
- AC-08 (REQ-06): `README.md` no contiene `python3 .microharness/sdd.py init` ni la frase que exige `python3.exe`; la sección 2 menciona `uv.exe`/`uv` como requisito verificado por el instalador y contiene literalmente `uvx --no-cache --from`.
- AC-09 (REQ-07): `python -m unittest discover -s tests -v` termina con código 0; las pruebas existentes de idempotencia, CLAUDE.md, settings alterno, conflictos/`--force`, `--dry-run`, destinos inválidos, filtro de PATH, banner/uso, licencia y wheel siguen pasando (solo cambia el parámetro inyectado).

## Fuera de alcance
- Cambiar el hook (`.claude/settings.json`, `.claude/hooks/pretool.py`), el lanzador `.microharness/python.sh`, `.microharness/sdd.py`, `assets/`, `scripts/`, `pyproject.toml` ni el proceso de release.
- Ejecutar el smoke test a través de `uv run` (ver diseño, alternativa descartada y pregunta abierta).
- Instalar `uv` o Python automáticamente; verificar la versión mínima de `uv`.
- `docs/**` y `.microharness/memory.json` (los actualiza el líder; `docs/AGENT.md` y `docs/specificaciones.md` mencionan el requisito antiguo de `python3`).
- `tests/test_sdd.py` (protegido en tareas previas; no se toca).
