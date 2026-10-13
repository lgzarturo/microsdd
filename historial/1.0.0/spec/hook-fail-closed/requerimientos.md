# QUÉ: requisitos

## Objetivo

Cerrar el riesgo R5: hoy `.claude/hooks/pretool.py` permite todo cuando el evento no trae un `agent_type` de los cuatro roles (`run()`, líneas 13-14: `return None`). La guardia debe pasar a denegar por defecto (fail-closed) las herramientas que vigila cuando no se reconoce al agente, e indicar cómo continuar.

## Hechos comprobados

- `run()` devuelve `None` (permitir) si `agent_type` falta, está vacío o no es `autor|implementador|revisor|lider`, con cualquier herramienta.
- El matcher de `.claude/settings.json` es `Write|Edit|MultiEdit|NotebookEdit|Bash|PowerShell`; las demás herramientas (Read, Grep, Glob, etc.) no llegan al hook.
- La sesión principal con `agent: lider` en `settings.json` sí envía `agent_type` al hook (hecho registrado en `.microharness/memory.json`: un Write del líder fuera del proyecto se denegó por la rama de roles).
- El smoke test del instalador (`src/microsdd/installer.py`, líneas 209-215) envía `agent_type: revisor` + `Edit` y espera `deny` con «solo lectura». Las pruebas actuales del hook (`HookTests`, `SettingsTests` en `tests/test_sdd.py`) siempre envían uno de los cuatro roles.
- El bloque `__main__` ya deniega cualquier excepción («Guardia inválida»).

## Supuestos (no verificados)

- Según la documentación de Claude Code (dato externo, no comprobado aquí), un subagente integrado como `Explore` o `general-purpose` envía su propio nombre en `agent_type`, y una sesión sin `--agent` ni `agent` en settings no lo envía. Por eso, tras el cambio, esos subagentes y esas sesiones no podrán usar Write/Edit/MultiEdit/NotebookEdit/Bash/PowerShell en un proyecto MicroSDD con el hook activo.

## Precondiciones

- Python 3.10+, solo biblioteca estándar.
- Esta tarea va antes de `bloquear-autoaprobacion` (orden de la serie en memoria); ambas tocan `pretool.py`.
- El implementador modifica `.claude/hooks/pretool.py` por Bash (el hook le niega `Write/Edit` en `.claude/`), como último cambio de código, después de ver las pruebas en RED.

## Requisitos EARS

- REQ-01: IF el evento no trae `agent_type`, o trae un valor vacío o `null`, o un valor distinto de `autor`, `implementador`, `revisor` o `lider` (comparación exacta, sensible a mayúsculas), AND `tool_name` es `Write`, `Edit`, `MultiEdit`, `NotebookEdit`, `Bash` o `PowerShell`, THEN la guardia SHALL denegar con un motivo que contenga `claude --agent lider` y mencione que se usa uno de los cuatro agentes.
- REQ-02: IF `agent_type` no es reconocido AND `tool_name` es cualquier otra herramienta (o falta), THEN la guardia SHALL permitir (`run()` devuelve `None`), igual que hoy.
- REQ-03: WHEN `agent_type` es uno de los cuatro roles, la guardia SHALL decidir exactamente como antes del cambio.
- REQ-04: WHEN el hook se ejecuta como script con un evento sin `agent_type` y una herramienta vigilada, THE hook SHALL imprimir en stdout el JSON `PreToolUse` con `permissionDecision: deny` y el motivo de REQ-01, y terminar con código 0.
- REQ-05: THE README SHALL explicar el comportamiento fail-closed, el mensaje, el impacto en sesiones sin agente y en subagentes ajenos a MicroSDD (p. ej. `Explore`, `general-purpose`) y cómo proceder.

## Criterios de aceptación

- AC-01: Para cada herramienta de {`Write`, `Edit`, `MultiEdit`, `NotebookEdit`, `Bash`, `PowerShell`} y cada evento con `agent_type` ausente, `''`, `None`, `'general-purpose'`, `'Explore'`, `'Lider'` y `' lider'`, `hook.run(...)` devuelve una cadena que contiene `claude --agent lider`. Para `Write`/`Edit` se incluye un `file_path` dentro del `cwd` del evento, y para `Bash`/`PowerShell` un comando inocuo (`git status`), de modo que la denegación no dependa de la ruta ni del comando.
- AC-02: Con `agent_type` ausente o `'general-purpose'`, `hook.run(...)` devuelve `None` para `tool_name` `Read`, `Grep`, `Glob`, `WebFetch` y para un evento sin `tool_name`.
- AC-03: Las pruebas existentes de `HookTests` y `SettingsTests` pasan sin modificación; además, con `tool_name: 'Bash'` y comando `git status`, `hook.run(...)` devuelve `None` para `agent_type` `lider`, `autor` e `implementador`, y el revisor sigue recibiendo «solo lectura» en `Edit`.
- AC-04: Ejecutar `pretool.py` con `sys.executable` (subproceso, stdin JSON): con `{"tool_name": "Write", "tool_input": {"file_path": "x"}}` el código de salida es 0 y stdout es un JSON con `hookSpecificOutput.permissionDecision == "deny"` y `permissionDecisionReason` que contiene `claude --agent lider`; con `{"agent_type": "lider", "tool_name": "Bash", "tool_input": {"command": "git status"}}` stdout queda vacío.
- AC-05: `python -m unittest discover -s tests -v` termina con código 0, incluidas las pruebas del smoke test del instalador (`tests/test_installer.py`) y `SettingsTests`.
- AC-06: `README.md` contiene una subsección (junto a «Bloqueo si falta uv») que indica: las seis herramientas denegadas, que Read/Grep/Glob y demás no cambian, el texto a seguir (`claude --agent lider`), el impacto en sesiones sin agente y en subagentes como `Explore` o `general-purpose` dentro de un proyecto MicroSDD, y cómo proceder (lanzar con `--agent lider`, delegar en los cuatro agentes o desactivar el hook fuera de Claude Code). La fila «Acceso por rol» de la sección 7 menciona la denegación de agentes no reconocidos.
- AC-07: `git diff --name-only` solo muestra rutas de `scope.allowed_paths`; `.claude/settings.json` y `src/microsdd/installer.py` no cambian.

## Fuera de alcance

- Cambiar el matcher de `settings.json`, el instalador o su smoke test, los agentes (`.claude/agents/*.md`) o `sdd.py`.
- Restringir `Bash`/`PowerShell` de `lider`, `autor` o `implementador` (corresponde a `bloquear-autoaprobacion`).
- Una variable o bandera para saltarse la denegación.
- Permitir subagentes ajenos (`Explore`, `general-purpose`) mediante lista blanca.
- Corregir otras frases del README no relacionadas (p. ej. la lista de herramientas de «Bloqueo si falta uv»).
