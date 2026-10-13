# Arquitectura comprobada

Solo componentes, interfaces e invariantes observados en el repositorio.

## Componentes

- **Arnés (se instala en cada proyecto):** `.claude/settings.json` (agente `lider`, modelo, esfuerzo, hook `PreToolUse`), `.claude/agents/*.md` (4 roles), `.claude/hooks/pretool.py` (límites de edición/Bash por agente, best effort), `.claude/skills/sdd/SKILL.md`, `.microharness/sdd.py` (máquina de tres estados, huellas SHA-256, alcance por `git diff`, puerta de pruebas) y `CLAUDE.md`.
- **Instalador (solo en este repositorio):** `pyproject.toml` (paquete `microsdd`, build con hatchling, sin dependencias de ejecución) y `src/microsdd/installer.py`. El wheel incluye los archivos del arnés como `microsdd/payload/...` mediante `force-include`.
- **Pruebas:** `tests/test_sdd.py` (controlador y hook) y `tests/test_installer.py` (instalador, incluido build real del wheel si hay `uv`).

## Invariantes

- `sdd.py` obtiene el diff con `git -z` y UTF-8 (`diff_files`); las rutas son relativas a la raíz Git, por eso el arnés debe vivir en la raíz del repositorio.
- El manifiesto del instalador vive en `installer.py` (`MANIFEST`) y `pyproject.toml` lo replica; `tests/test_installer.py` (AC-10) verifica la coherencia contra el wheel.
- El instalador no escribe nada antes de validar destino, `uv` (ejecutable real; en Windows `uv.exe`) y conflictos; ejecuta `sdd.py init` y el smoke test del hook con `sys.executable`, sin buscar ni ejecutar `python3`; nunca sobrescribe `CLAUDE.md` ni `.claude/settings.json` del destino (anexa un bloque marcado con `@CLAUDE.microsdd.md` y usa `.claude/settings.microsdd.json`); `--force` solo afecta archivos propios del arnés.
- Los `docs/` del destino los genera `sdd.py init`; los `docs/` de este repositorio describen a MicroSDD y no se distribuyen.
- `scripts/limpiar_arnes.py` (solo en este repositorio, no se distribuye): antes de un release exige árbol git limpio y todas las tareas en `terminado`; archiva `.microharness/memory.json`, `docs/` y `spec/<slug>/` en `historial/<versión>/` y restaura el estado inicial ejecutando `.microharness/sdd.py init`. No hace commit, tag ni push.
## Ejecución de Python (tarea `deteccion-python-multiplataforma`)

- **Hook `PreToolUse`** (`.claude/settings.json`, matcher `Write|Edit|MultiEdit|NotebookEdit|Bash|PowerShell`; la allowlist del revisor se aplica igual a `Bash` y `PowerShell`): forma exec, sin shell: `command: "uv"`, `args: ["run", "--no-project", "--quiet", "--python", ">=3.10", "${CLAUDE_PROJECT_DIR}/.claude/hooks/pretool.py"]`, `onFailure: "block"` (Claude Code ≥ 2.1.295). Invariante: si uv falta o el hook no arranca, la herramienta se bloquea (fail-closed). Requiere `uv` en `PATH` como ejecutable real.
- **Lanzador** `.microharness/python.sh` (POSIX `sh`, solo builtins): orden `MICROSDD_PYTHON` → `uv` → `python3` → `python` → `py -3`; cada candidato se valida con un sondeo ≥3.10; `exec` conserva stdin/stdout/stderr y código de salida; sin intérprete válido, o con `MICROSDD_PYTHON` inválido, sale con 2.
- **`sdd.py check --run`**: si el primer elemento de un comando es exactamente `python` o `python3`, se sustituye por `sys.executable`.
- **`sdd.py diff_files()`**: se conservó la variante `git -z` + UTF-8 de `fix-sdd-rutas-unicode`, que cubre lo mismo que `fix-quotepath-diff`.
- **Limitación observada (MSYS):** al lanzar el `sh` de Git Bash desde un proceso nativo de Windows, los argumentos sin espacios que contienen comillas llegan alterados; desde Git Bash no ocurre.
- **Versionado:** `sdd.py` declara `__version__` y ofrece `--version` y `release propose` (solo lectura, exige rama `main` y ninguna tarea en `proceso`). `scripts/limpiar_arnes.py <versión>` es el paso posterior que archiva el historial. `assets/` (decisiones de diseño y proceso de versionado) no se instala.
- **Memoria (tarea `memoria-atomica-lock`):** `dump()` escribe de forma atómica (temporal en el mismo directorio, `fsync`, `os.replace`, modo conservado). Las operaciones que mutan la memoria (`ensure_init`, `new`, `approve`, `review`, `seal`, `note`) toman un lock exclusivo reentrante en `.microharness/memory.lock` (`flock`/`msvcrt`, timeout 10 s → código 1); `check` no lo toma. `memory.lock` está en `.gitignore` y `release propose` lo tolera.
- **Recuento de pruebas (tarea `check-min-pruebas`):** `check --run` captura la salida (la reproduce en bytes), cuenta pruebas con `tests_ran()` (unittest, pytest, bun, Maven, Go; última coincidencia por formato) y exige por comando al menos `testing.min_tests` (int ≥1, por defecto 1). Mutación no contada; tareas `terminado` exentas.
- **Lista blanca de runners (tarea `lista-blanca-runners`):** `validate()` exige, si la tarea no está `terminado`, que `testing.commands` y `mutation.command` (si `enabled`) empiecen por un prefijo de `TEST_COMMANDS` o de `project.allowed_test_commands` (comparación por token; `sys.executable` equivale a `python`). La lista acota el ejecutable, no lo que ejecuta el runner.
