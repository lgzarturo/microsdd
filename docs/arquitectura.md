# Arquitectura comprobada

Documentar solo componentes, interfaces, módulos e invariantes reales que afecten decisiones de implementación. Incluir rutas concretas y dependencias relevantes; evitar describir arquitectura deseada como si existiera.

## Ejecución de Python (tarea `deteccion-python-multiplataforma`)

- **Hook `PreToolUse`** (`.claude/settings.json`, matcher `Write|Edit|MultiEdit|NotebookEdit|Bash|PowerShell`; la allowlist del revisor se aplica igual a `Bash` y `PowerShell`): forma exec, sin shell: `command: "uv"`, `args: ["run", "--no-project", "--quiet", "--python", ">=3.10", "${CLAUDE_PROJECT_DIR}/.claude/hooks/pretool.py"]`, `onFailure: "block"` (Claude Code ≥ 2.1.295). Invariante: si uv falta o el hook no arranca, la herramienta se bloquea (fail-closed). Requiere `uv` en `PATH` como ejecutable real.
- **Lanzador** `.microharness/python.sh` (POSIX `sh`, solo builtins): orden `MICROSDD_PYTHON` → `uv` → `python3` → `python` → `py -3`; cada candidato se valida con un sondeo ≥3.10; `exec` conserva stdin/stdout/stderr y código de salida; sin intérprete válido, o con `MICROSDD_PYTHON` inválido, sale con 2.
- **`sdd.py check --run`**: si el primer elemento de un comando es exactamente `python` o `python3`, se sustituye por `sys.executable`.
- **`sdd.py diff_files()`**: usa `git -c core.quotePath=false` y decodifica UTF-8 (tarea `fix-quotepath-diff`), para rutas no ASCII como `diseño.md`.
- **Limitación observada (MSYS):** al lanzar el `sh` de Git Bash desde un proceso nativo de Windows, los argumentos sin espacios que contienen comillas llegan alterados; desde Git Bash no ocurre.
