# CÓMO: diseño mínimo

## Situación comprobada
- En `pretool.py`, la rama final de `run()` es `if tool == 'Bash' and agent == 'revisor':` y aplica dos `re.fullmatch` sobre `inputs.get('command', '').strip()`. Ninguna otra rama consulta `Bash`.
- El matcher de `settings.json` es `Write|Edit|MultiEdit|NotebookEdit|Bash`. Como no incluye `PowerShell`, el hook ni siquiera se invoca para esa herramienta.
- En `tests/test_sdd.py`, `HookTests` carga el módulo con `importlib` y llama a `hook.run(event)`; `SettingsTests.pretool_hook()` compara el matcher literal.
- `README.md:222`, fila «Acceso por rol»: «`Bash` y herramientas externas no son sandbox universal».

## Decisión y justificación
1. `pretool.py`: cambiar solo la condición a `if tool in ('Bash', 'PowerShell') and agent == 'revisor':`. Se mantienen la allowlist y el motivo de denegación, sin más lógica.
2. `settings.json`: matcher `Write|Edit|MultiEdit|NotebookEdit|Bash|PowerShell`. Nada más.
3. `tests/test_sdd.py`:
   - Nueva prueba en `HookTests` (por ejemplo, `test_reviewer_powershell_uses_bash_allowlist`) para AC-01 y AC-02, que cargue el hook igual que las pruebas vecinas.
   - En `SettingsTests.pretool_hook()`, sustituir la igualdad literal por la comparación de `set(matcher.split('|'))` con las seis herramientas (AC-04). Así se exige `PowerShell` y se conservan las anteriores sin depender del orden.
4. `README.md`: en la fila «Acceso por rol», cambiar «`Bash`» por «`Bash`/`PowerShell`». Justificación: la fila describe qué cubre el hook y, tras el cambio, quedaría incompleta. Si el líder prefiere no tocar README, se eliminan AC-05, T04 y `README.md` de `allowed_paths`.

Orden: primero las pruebas, después `pretool.py`, luego README y al final `settings.json`. Dejar la configuración para el final evita que una recarga en caliente de hooks deje el arnés con la configuración a medias mientras se edita.

## Alternativas descartadas
- Constante `SHELL_TOOLS`: una tupla de dos literales usada en un único sitio basta (YAGNI).
- Matcher separado para PowerShell: duplica la entrada y rompe la aserción `len(entries) == 1`.
- Reglas propias de la sintaxis de PowerShell (`;`, `|`, backtick como escape): la allowlist con `fullmatch` ya rechaza todo lo que no sea el comando exacto del checker. El endurecimiento de la regex de Git corresponde a `regex-revisor-ascii`.

## Invariantes
- `Bash` y `Write`/`Edit`/`MultiEdit`/`NotebookEdit` mantienen el mismo comportamiento para todos los agentes.
- `type`, `command`, `args` y `onFailure` del hook no cambian; la guardia sigue denegando cuando falla.
- `PowerShell` en agentes distintos del revisor sigue devolviendo `None`, igual que `Bash`.

## Riesgos
- R1 (bloqueante): el propio hook niega al `implementador` editar cualquier ruta bajo `.claude/`, aunque esté en `allowed_paths`. PRE-01 autoriza el cambio, pero la guardia lo impide. Opciones para que decida el humano: (a) el programador aplica a mano los dos cambios de una línea en `.claude/` (T03 y T05), y el implementador hace las pruebas y README; (b) otra vía que el humano apruebe. El implementador no debe usar `Bash`/`sed` para saltarse la guardia, y esta tarea no debe relajar `pretool.py`.
- R2: el nombre de herramienta `PowerShell` y el campo `tool_input.command` vienen de la documentación que citó el líder. Si el nombre real fuera otro, el matcher no lo cubriría, y las pruebas unitarias no lo detectarían porque usan el nombre supuesto.
- R3: con la regex actual, `git status` y `git diff` aceptan argumentos sin `;&|\n`. En PowerShell, otros metacaracteres (backtick, `$()`) podrían tener otro significado. Se acepta: es el mismo agujero que ya existe con `Bash` y se trata en `regex-revisor-ascii`.

## Efectos secundarios
- `docs/arquitectura.md` dejará de reflejar el matcher real; actualizarlo es tarea del líder al cerrar.
- Si el hook se recarga en caliente, el revisor quedará restringido también en PowerShell en cuanto se guarde `settings.json`.
