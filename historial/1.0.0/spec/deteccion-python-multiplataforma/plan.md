# CÓMO: diseño mínimo

## Situación comprobada
- `.claude/settings.json`: único hook `PreToolUse`, matcher `Write|Edit|MultiEdit|NotebookEdit|Bash`, forma shell `python3 "${CLAUDE_PROJECT_DIR}/.claude/hooks/pretool.py"`. En Windows + Git Bash falla con exit 49 (stub de Store) y Claude Code lo trata como no bloqueante: guardia inactiva.
- Forma exec (según documentación oficial de hooks aportada por el líder): `command` + `args`, sin shell; `${CLAUDE_PROJECT_DIR}` se sustituye en `command` y en cada `args`; stdin igual; en Windows `command` debe ser un `.exe` real. `"onFailure": "block"` existe desde v2.1.295 (local 2.1.296).
- Probado por el líder: `uv run --no-project --quiet --python ">=3.10" .claude/hooks/pretool.py` recibe stdin y emite la decisión JSON (~0,22 s).
- `.microharness/sdd.py` `validate(run=True)` (líneas ~236-244) ejecuta `subprocess.run(command, cwd=ROOT, …)` sin shell sobre `testing.commands` y `mutation.command`.
- `.claude/hooks/pretool.py` (regex del revisor): `python(?:3)? \.microharness/sdd\.py check [a-z][a-z0-9-]* --run` o `git (diff|status)(?: [^;&|\n]+)?`.
- Menciones `python3 .microharness/sdd.py`: `README.md` (líneas 18-19, 22, 29-30, 101-136, ejemplo `["python3", "-m", "pytest", …]` en 164), `CLAUDE.md:11`, `.claude/agents/{autor,lider,revisor}.md`. `.claude/skills/sdd/SKILL.md` e `implementador.md` NO las contienen (se excluyen del alcance; el líder las había previsto). `docs/specificaciones.md:14` también la contiene, pero corresponde al líder.
- `tests/test_sdd.py`: `MicroSDDTests` (spec temporal con `sdd.ROOT` redirigido) y `HookTests` (carga `pretool.py` por ruta). Suite actual: 10 OK.
- `validate(scope=True)` omite del control de alcance los cambios en `.microharness/` y `CLAUDE.md`; sí controla `.claude/`, `README.md` y `tests/`.

## Decisión y justificación
1. **Hook en forma exec con uv** (`.claude/settings.json`), decisión del programador:
   ```json
   {"type": "command", "command": "uv",
    "args": ["run", "--no-project", "--quiet", "--python", ">=3.10", "${CLAUDE_PROJECT_DIR}/.claude/hooks/pretool.py"],
    "onFailure": "block"}
   ```
   Sin shell, el mismo JSON vale en los tres SO; `--no-project` evita sincronizar un `pyproject.toml` del repositorio anfitrión; `--quiet` mantiene stdout limpio para el JSON de decisión. `onFailure: block` convierte la ausencia de uv en bloqueo, no en guardia desactivada.
2. **Lanzador POSIX `.microharness/python.sh`** (nuevo, solo builtins de `sh` más los candidatos):
   - Sondeo común: `"$@" -c 'import sys; sys.exit(sys.version_info < (3, 10))' >/dev/null 2>&1`.
   - Si `MICROSDD_PYTHON` no está vacío: sondeo; si pasa, `exec "$MICROSDD_PYTHON" "$@"`; si no, mensaje y `exit 2` (**decisión sobre la sugerencia 3**: error explícito y sin degradar; quien define la variable expresa una elección deliberada, y usar en silencio otro intérprete ocultaría la configuración rota y podría ejecutar el arnés con un Python distinto del esperado. Coherente con fail-closed).
   - `command -v uv` → sondeo con `uv run --no-project --quiet --python '>=3.10' python -c …` → `exec uv run --no-project --quiet --python '>=3.10' python "$@"`. Se antepone `python` para que funcionen también argumentos como `-m unittest` o `-c`, no solo rutas `.py`.
   - `python3`, `python` → sondeo → `exec <cand> "$@"`.
   - `py -3` → sondeo → `exec py -3 "$@"`.
   - Ninguno: mensaje en español por stderr (instalar uv con su instalador oficial o Python ≥3.10; en Windows, desactivar los alias de ejecución de la Store o definir `MICROSDD_PYTHON`) y `exit 2`.
   - Cada candidato con `MICROSDD_PYTHON` puede contener solo una ruta (sin argumentos); se cita como `"$MICROSDD_PYTHON"`.
3. **`sdd.py check --run`**: en el bucle de ejecución, si `command[0] in ('python', 'python3')`, usar `[sys.executable, *command[1:]]`. Cambio de una línea; `sys.executable` es el intérprete que ya ejecuta el checker (≥3.10 si se lanzó con `python.sh` o uv). Se mantiene el mensaje `EJECUTANDO:` con el comando efectivo.
4. **Regex del revisor en `pretool.py`**: sustituir el primer `re.fullmatch` por uno con prefijos alternativos:
   ```text
   (?:python3?|py -3|sh \.microharness/python\.sh|uv run --no-project(?: --quiet)?(?: --python (?:'>=3\.\d+'|">=3\.\d+"|3\.\d+))?) \.microharness/sdd\.py check [a-z][a-z0-9-]* --run
   ```
   `fullmatch` y la ausencia de clases abiertas impiden `;&|`, saltos de línea, `$` y comillas invertidas. El valor de `--python` se exige entrecomillado si contiene `>` porque sin comillas el shell lo interpreta como redirección.
5. **Documentación**: reemplazar `python3 .microharness/sdd.py` por `sh .microharness/python.sh .microharness/sdd.py` en `README.md`, `CLAUDE.md` y `.claude/agents/{autor,lider,revisor}.md`; en `README.md`, reescribir la sección 1 (requisitos) con instalación por SO, y cambiar los ejemplos de `testing.commands` a `"python"`.

## Alternativas descartadas
- Mantener forma shell con cadena de detección inline (`python3 || python || py -3`): depende del shell, que en Windows puede ser PowerShell; frágil y difícil de probar.
- Hook vía `sh .microharness/python.sh`: en Windows sin Git Bash no hay `sh`, y en forma exec `sh` no siempre es un `.exe` resoluble.
- Hook con `python` en forma exec: en Windows puede resolver al stub o no existir; no garantiza ≥3.10.
- Lanzador en Python o `.ps1`: el primero no resuelve el huevo/gallina; el segundo está fuera de alcance.
- Caché del intérprete detectado: YAGNI; el sondeo cuesta milisegundos.
- Degradar en silencio si `MICROSDD_PYTHON` es inválido: oculta errores de configuración (ver decisión 2).

## Invariantes y riesgos
Invariantes:
- La guardia nunca queda inactiva en silencio: o se ejecuta `pretool.py` o la herramienta se bloquea.
- El lanzador nunca ejecuta con Python <3.10 ni con el stub de Store; sale con 2 si no hay intérprete válido.
- El lanzador no altera stdin, stdout, stderr ni el código de salida del programa lanzado (`exec`).
- La regex del revisor sigue siendo `fullmatch` sin metacaracteres de encadenamiento.
- Solo biblioteca estándar; sin dependencias nuevas de Python.

Riesgos:
- R-01 (alto) **Bloqueo total sin uv**: con `onFailure: block`, si uv no está en PATH, toda llamada `Write|Edit|MultiEdit|NotebookEdit|Bash` queda bloqueada para cualquier agente, incluida la sesión principal. Mitigación: documentarlo en README (precondición P-01) y recordar que `settings.json` puede editarse fuera de Claude Code. Es consecuencia aceptada de la decisión 1 del programador.
- R-02 (alto) **Autobloqueo durante la implementación**: si Claude Code recarga hooks en caliente, la nueva guardia (activa) impediría al implementador editar `.claude/` y `.microharness/` (prefijos prohibidos en `pretool.py`). Mitigación: `settings.json` es el último paso de código en `tareas.md`.
- R-03 (alto, ver dudas) **La excepción autorizada no está implementada en la guardia**: `pretool.py` prohíbe al implementador `.claude/`, `.microharness/` y `CLAUDE.md` con independencia de `allowed_paths`. En esta máquina la guardia está hoy inactiva (stub), por eso las ediciones pasarían; en un equipo con la guardia funcionando el implementador sería bloqueado. Este diseño no cambia esa regla.
- R-04 (medio) **Descarga de Python por uv**: `uv run --python >=3.10` puede descargar un Python gestionado la primera vez (latencia, red). Aceptado.
- R-05 (medio) **Pruebas del lanzador en Windows**: los falsos `python`/`python3` son scripts con shebang `#!/bin/sh`; dependen de que el `sh` de Git Bash los ejecute desde un PATH restringido. Se invoca `sh` por ruta absoluta (`shutil.which('sh')`) y el lanzador solo usa builtins, para que un PATH que contenga únicamente el directorio temporal sea suficiente.
- R-06 (bajo) **Control de alcance**: `validate` no comprueba alcance en `.microharness/` ni `CLAUDE.md`; el revisor debe verificar esos cambios por `git diff`.
- R-07 (bajo) La sustitución por `sys.executable` cambia el intérprete de comandos `python3 …` de proyectos anfitriones que dependan de un `python3` distinto (p. ej., virtualenv activado). Aceptado: el arnés exige ≥3.10 y la sustitución se limita al primer elemento exacto.

Efectos secundarios: la guardia pasa a estar activa en Windows donde antes fallaba en silencio; agentes y documentación pasan a usar `sh .microharness/python.sh`.
