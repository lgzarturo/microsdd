# QUÉ: requisitos

## Objetivo
Hacer que la guardia `PreToolUse` cubra también la herramienta `PowerShell` de Claude Code. El matcher del hook la incluirá y la allowlist de comandos del revisor se aplicará a `PowerShell` igual que a `Bash`. Es defensa en profundidad: hoy ningún agente con `tools:` declara `PowerShell`, pero si alguien la añade, la guardia no la cubriría.

## Hechos comprobados
- `.claude/settings.json` tiene un único `PreToolUse` con matcher `Write|Edit|MultiEdit|NotebookEdit|Bash`, forma exec con `uv` y `onFailure: block`.
- `.claude/hooks/pretool.py` solo restringe comandos del revisor cuando `tool == 'Bash'`. Con `tool_name: 'PowerShell'` devuelve `None` para cualquier comando; por ejemplo, permite `rm -rf src`.
- La herramienta PowerShell recibe el comando en `tool_input.command`, el mismo campo que Bash. Es un dato del líder basado en la documentación oficial de hooks; el autor no lo verificó.
- En `tests/test_sdd.py`, `SettingsTests.pretool_hook()` compara el matcher exacto `'Write|Edit|MultiEdit|NotebookEdit|Bash'`.
- En `README.md`, sección 7, la fila «Acceso por rol» menciona solo `Bash`.
- `pretool.py` niega al `implementador` cualquier edición bajo `.claude/` (`rel.startswith(('.claude/', ...))`), aunque la ruta esté en `allowed_paths`.

## Precondiciones
- PRE-01: el programador autoriza de forma explícita, solo para esta tarea, editar `.claude/settings.json` y `.claude/hooks/pretool.py`. El hook actual impide esas ediciones al implementador (ver riesgo R1 del diseño); el humano debe decidir cómo se aplican antes de implementar.

## Requisitos EARS
- REQ-01: WHEN el agente `revisor` invoca `PowerShell` con un comando que no está en la allowlist, THE guardia SHALL denegarlo con el mismo motivo que en `Bash`.
- REQ-02: WHEN el agente `revisor` invoca `PowerShell` con un comando de la allowlist (checker `check <slug> --run` con un prefijo admitido, `git status` o `git diff`), THE guardia SHALL permitirlo, es decir, devolver `None`.
- REQ-03: WHEN el agente `revisor` invoca `Bash`, THE guardia SHALL conservar exactamente su comportamiento actual.
- REQ-04: THE configuración `.claude/settings.json` SHALL enviar `PowerShell` al mismo hook `PreToolUse`, mantener las herramientas anteriores del matcher y dejar sin cambios `type`, `command`, `args` y `onFailure`.

## Criterios de aceptación
- AC-01: `hook.run({'agent_type': 'revisor', 'tool_name': 'PowerShell', 'tool_input': {'command': 'rm -rf src'}})` no devuelve `None`.
- AC-02: con `agent_type: 'revisor'` y `tool_name: 'PowerShell'`, `hook.run(...)` devuelve `None` para `python .microharness/sdd.py check fix-a --run` y para `git status`.
- AC-03: las pruebas existentes del revisor con `Bash` (`test_reviewer_edits_blocked`, `test_reviewer_checker_prefixes`) siguen pasando sin modificarse.
- AC-04: en `.claude/settings.json`, el conjunto de herramientas del matcher (separadas por `|`) es exactamente `{Write, Edit, MultiEdit, NotebookEdit, Bash, PowerShell}`. Sigue habiendo una sola entrada con un solo hook, y `type`, `command`, `args` y `onFailure` conservan sus valores actuales: `test_pretool_hook_exec_form_with_uv` pasa sin modificarse.
- AC-05: la fila «Acceso por rol» de `README.md` menciona `PowerShell` junto a `Bash`, y `README.md` no tiene más cambios.
- AC-06: `python -m unittest discover -s tests -v` pasa completo, y las pruebas nuevas o modificadas de AC-01 y AC-04 fallan antes del cambio de código (TDD).

## Fuera de alcance
- Endurecer la regex `git (diff|status)` o cambiar `\d` por `[0-9]`; eso corresponde a la tarea `regex-revisor-ascii`.
- Cambiar el frontmatter `tools:` de los agentes.
- Scripts `.ps1` y cualquier lógica nueva para PowerShell: análisis de su sintaxis propia, alias, etc.
- Restricciones de `PowerShell` para agentes distintos del revisor; hoy `Bash` tampoco las tiene.
- `docs/arquitectura.md`, que menciona el matcher: actualizarlo corresponde al líder, no al implementador.
