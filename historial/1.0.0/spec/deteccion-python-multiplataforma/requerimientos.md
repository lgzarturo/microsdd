# QUÉ: requisitos

## Objetivo
Que el arnés MicroSDD (hook `PreToolUse`, CLI `.microharness/sdd.py` y puerta de pruebas `check --run`) localice y use un intérprete Python ≥3.10 funcional en Windows, macOS y Linux, con preferencia por uv, y que falle de forma cerrada y explícita cuando no exista ninguno. Python ≥3.10 es requisito duro.

Motivo comprobado: el hook actual se declara en forma shell como `python3 "${CLAUDE_PROJECT_DIR}/.claude/hooks/pretool.py"`. En Windows con Git Bash, `python3` resuelve al stub de Microsoft Store (exit 49), Claude Code lo trata como error no bloqueante y la guardia queda inactiva en silencio. Además, `check --run` ejecuta `testing.commands` sin shell, de modo que `"python3"` también resuelve al stub.

## Precondiciones
- P-01: Para el hook: `uv` instalado y resoluble en `PATH` como ejecutable real (en Windows, `uv.exe`; los shims `.cmd`/`.bat` no sirven en forma exec).
- P-02: Para `"onFailure": "block"`: Claude Code ≥ v2.1.295 (versión local comprobada: 2.1.296).
- P-03: Para el lanzador `.microharness/python.sh`: un `sh` POSIX disponible (macOS/Linux nativo; en Windows, Git Bash).
- P-04: Al menos uno de: `MICROSDD_PYTHON`, `uv`, `python3`, `python` o `py -3` que proporcione Python ≥3.10. Sin ello, el arnés no funciona (falla cerrada, ver REQ-05).

## Requisitos EARS
- REQ-01: WHEN Claude Code dispare el hook `PreToolUse` para `Write|Edit|MultiEdit|NotebookEdit|Bash`, THE configuración `.claude/settings.json` SHALL ejecutar `.claude/hooks/pretool.py` en forma exec con `command` `uv` y `args` `run --no-project --quiet --python >=3.10 ${CLAUDE_PROJECT_DIR}/.claude/hooks/pretool.py`, sin depender de `python3` ni de un shell.
- REQ-02: IF el hook no puede arrancar o falla, THEN Claude Code SHALL bloquear la herramienta (`"onFailure": "block"`), en lugar de continuar sin guardia.
- REQ-03: WHEN se invoque `sh .microharness/python.sh <args…>`, THE lanzador SHALL probar los candidatos en el orden `MICROSDD_PYTHON` → `uv` → `python3` → `python` → `py -3`, validar cada uno con el sondeo `-c 'import sys; sys.exit(sys.version_info < (3, 10))'` y ejecutar `<args…>` con el primero válido mediante `exec`, preservando stdin, stdout, stderr y el código de salida.
- REQ-04: IF `MICROSDD_PYTHON` está definido y no supera el sondeo, THEN el lanzador SHALL terminar con código 2 y un mensaje en español por stderr que nombre `MICROSDD_PYTHON`, sin recurrir a otros candidatos.
- REQ-05: IF ningún candidato supera el sondeo, THEN el lanzador SHALL terminar con código 2 y un mensaje en español por stderr que indique cómo instalar uv o Python ≥3.10.
- REQ-06: WHEN `sdd.py check <slug> --run` ejecute un comando de `testing.commands` (o `mutation.command`) cuyo primer elemento sea exactamente `python` o `python3`, THE checker SHALL sustituir ese elemento por `sys.executable`; los demás comandos se ejecutan sin cambios.
- REQ-07: WHEN el agente `revisor` solicite Bash, THE guardia SHALL permitir `<prefijo> .microharness/sdd.py check <slug> --run` con prefijo `python`, `python3`, `py -3`, `sh .microharness/python.sh` o `uv run --no-project [--quiet] [--python <versión entrecomillada o 3.N>]`, y SHALL seguir denegando cualquier otro comando, incluidos los que contengan `;`, `&`, `|`, saltos de línea, `$` o comillas invertidas.
- REQ-08: WHERE la documentación del proyecto indique cómo invocar el CLI, THE texto SHALL usar la invocación portable `sh .microharness/python.sh .microharness/sdd.py …` en lugar de `python3 .microharness/sdd.py …`.

## Criterios de aceptación
- AC-01: Dado `.claude/settings.json`, al leer el hook de `PreToolUse`: `type` es `command`, `command` es `uv`, `args` es exactamente `["run", "--no-project", "--quiet", "--python", ">=3.10", "${CLAUDE_PROJECT_DIR}/.claude/hooks/pretool.py"]`, `onFailure` es `block` y el matcher sigue siendo `Write|Edit|MultiEdit|NotebookEdit|Bash`. Si `uv` está en PATH, ejecutar ese `command`+`args` (con `${CLAUDE_PROJECT_DIR}` sustituido) pasando por stdin un evento `{"agent_type":"revisor","tool_name":"Edit","tool_input":{}}` produce por stdout un JSON con `permissionDecision` `deny`; sin uv, la prueba de integración se salta.
- AC-02: Con `MICROSDD_PYTHON` sin definir y un PATH controlado donde `python3` sale con 49 y `python` reenvía a un Python ≥3.10 (sin uv), `sh .microharness/python.sh -c "<lee stdin, lo escribe en mayúsculas y sale con 7>"` con stdin `hola` imprime `HOLA` y termina con código 7.
- AC-03: Con `MICROSDD_PYTHON` apuntando a un Python ≥3.10 y un `python` en PATH que imprime un marcador distinto, el lanzador usa `MICROSDD_PYTHON` (la salida no contiene el marcador del falso `python`).
- AC-04: Con `MICROSDD_PYTHON` apuntando a un ejecutable que sale con 49 (o inexistente) y un `python` válido en PATH, el lanzador termina con código 2, stderr contiene `MICROSDD_PYTHON` y no se ejecuta el comando solicitado.
- AC-05: Con `MICROSDD_PYTHON` sin definir y un PATH donde solo existe un `python3` que sale con 49, el lanzador termina con código 2 y stderr contiene `uv` y `Python`.
- AC-06: Con una spec cuyo `testing.commands` es `[["python3", "-c", "<escribe sys.executable en un archivo>"]]`, `sdd.validate(slug, run=True)` devuelve `[]` y el archivo contiene exactamente `sys.executable` del proceso de pruebas; lo mismo con `"python"`. Un comando con primer elemento distinto (p. ej. `sys.executable` explícito) se ejecuta sin sustitución.
- AC-07: `pretool.run` con `agent_type` `revisor` y `tool_name` `Bash` devuelve `None` para cada uno de: `python .microharness/sdd.py check fix-a --run`, `python3 …`, `py -3 …`, `sh .microharness/python.sh .microharness/sdd.py check fix-a --run`, `uv run --no-project --quiet --python '>=3.10' .microharness/sdd.py check fix-a --run`, `uv run --no-project .microharness/sdd.py check fix-a --run`; y devuelve un motivo (no `None`) para: `sh .microharness/python.sh .microharness/sdd.py check fix-a --run; rm -rf src`, `uv run --no-project --python >=3.10 .microharness/sdd.py check fix-a --run` (sin comillas: redirección), `uv run .microharness/sdd.py check fix-a --run` (sin `--no-project`), `sh other.sh .microharness/sdd.py check fix-a --run` y `rm -rf src`.
- AC-08: Tras el cambio, `git grep -n "python3 .microharness/sdd.py"` no devuelve coincidencias en `README.md`, `CLAUDE.md` ni `.claude/agents/*.md`; `README.md` contiene una sección de requisitos/instalación por SO que menciona uv como opción recomendada, el stub de Microsoft Store en Windows, `MICROSDD_PYTHON` y qué ocurre en Windows sin Git Bash (el hook funciona vía uv en forma exec; el lanzador `.sh` requiere `sh`).
- AC-09: `python -m unittest discover -s tests -v` termina con código 0; las pruebas del lanzador se marcan como saltadas (no fallidas) cuando no hay `sh` disponible.

## Fuera de alcance
- Añadir la herramienta `PowerShell` al matcher del hook (se tratará aparte).
- Scripts `.ps1`, `.cmd` o `.bat`.
- Caché del intérprete detectado, empaquetado (uvx, hatchling, `pyproject.toml`, LICENSE) o instalación automática de uv/Python.
- Cambios en `docs/**` y `.microharness/memory.json` (los actualiza el líder).
- Cambiar la lógica de autorización de `pretool.py` salvo la expresión regular de Bash del revisor.
- `.claude/skills/sdd/SKILL.md` y `.claude/agents/implementador.md`: comprobado que no mencionan `python3` ni `sdd.py`.
