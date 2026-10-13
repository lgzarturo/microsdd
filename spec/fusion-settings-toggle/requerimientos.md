# QUÉ: requisitos

## Objetivo
Que `agent: lider`, `model`, `effortLevel` y el hook `PreToolUse` de MicroSDD queden efectivos en `.claude/settings.json` aunque el proyecto destino ya tuviera ese archivo (p. ej., con hooks de graphify), sin perder lo ajeno; que exista un desinstalador que quite solo lo que añadió MicroSDD; y que el humano, y solo el humano, pueda activar, desactivar y consultar el arnés con `microsdd on|off|status`. Solicitud autorizada por el dueño, Arturo L. Gómez.

## Hechos comprobados
- `src/microsdd/installer.py`: `SETTINGS_ALT = '.claude/settings.microsdd.json'`; `plan()` etiqueta `alterno` si `settings.json` existe y difiere; `install()` imprime «fusionar manualmente»; `main()` solo tiene `install` (`--target`, `--dry-run`, `--force`). No existe `uninstall`.
- El fragmento canónico es el payload `.claude/settings.json` (empaquetado como `microsdd/payload/.claude/settings.json`). `tests/test_sdd.py` (`SettingsTests`) exige una sola entrada `PreToolUse` con matcher `Write|Edit|MultiEdit|NotebookEdit|Bash|PowerShell`, `command: uv`, `args: [run, --no-project, --quiet, --python, >=3.10, ${CLAUDE_PROJECT_DIR}/.claude/hooks/pretool.py]`, `onFailure: block`.
- `.claude/hooks/pretool.py` ya niega `Write|Edit|MultiEdit|NotebookEdit` sobre `.claude/` a los cuatro roles y a agentes no reconocidos; en `Bash`/`PowerShell` solo vigila `microharness|memory.json|sdd.py`, así que hoy permite `microsdd off`, `sed -i … .claude/settings.json` o `echo {} > .claude/settings.json`.
- `.microharness/sdd.py` rechaza `approve`/`seal` con `CLAUDECODE` definido o stdin no TTY/`None`.
- `tests/test_installer.py`: `test_different_settings_is_kept_and_alternate_written` y `test_modified_own_file_conflicts_without_force_and_updates_with_force` (espera `settings.json` intacto en `{}`) dependen del alterno.
- `tests/test_api_publica.py` exige que «Instalación / Incluido» de `assets/proceso-versionado.md` liste exactamente `MANIFEST`, sus destinos, `INIT_FILES` y `spec/`.
- `README.md` y `assets/proceso-versionado.md` documentan el alterno y la eliminación manual; `CLAUDE.md` línea 3 afirma «configurado en `.claude/settings.json`».

## Supuestos (no verificados)
- `HEAD:.claude/settings.json` conserva el hook (lo exige `SettingsTests`); el árbol de trabajo puede estar sin hooks por la sesión de Cursor. No se comprobó con Git: la shell estaba bloqueada.
- Claude Code ejecuta `Bash`/`PowerShell` con `CLAUDECODE` definido.
- `settings.json` es JSON estricto (sin comentarios).

## Precondiciones
- Python 3.10+ y solo biblioteca estándar.
- `.claude/settings.json` del árbol igual a `HEAD` antes de `check --run` (lo restaura el humano).
- Decisión D-01 del líder sobre quién edita `.claude/hooks/pretool.py`, `.claude/skills/sdd/SKILL.md` y `CLAUDE.md`.
- Las aprobaciones de spec y cierre las ejecuta el humano en su terminal.

## Requisitos EARS
- REQ-01: WHEN `install` se ejecuta y `.claude/settings.json` no existe, THE instalador SHALL crearlo idéntico al payload y registrar en `.microharness/install.json` que lo creó y qué añadió.
- REQ-02: WHEN `install` se ejecuta y `.claude/settings.json` existe, THE instalador SHALL fusionar `agent`, `model`, `effortLevel` y la entrada `PreToolUse` del payload conservando toda otra clave y hook, hacer antes el respaldo `.claude/settings.json.bak.<marca UTC>` y registrar lo añadido o reemplazado con su valor previo.
- REQ-03: THE instalador SHALL dejar de escribir `.claude/settings.microsdd.json`.
- REQ-04: WHEN la fusión no cambiaría nada, THE instalador SHALL no escribir `settings.json`, respaldo ni manifiesto.
- REQ-05: IF `settings.json` no es JSON válido, su raíz no es objeto, `hooks` no es objeto o `hooks.PreToolUse` no es lista, THEN `install`, `on`, `off` y `uninstall` SHALL terminar con código 1 sin escribir nada.
- REQ-06: WHEN el humano ejecuta `off`, THE CLI SHALL quitar lo registrado, restaurar los previos, hacer respaldo y marcar el manifiesto desactivado; WHEN ejecuta `on`, THE CLI SHALL reaplicar REQ-02.
- REQ-07: WHEN se ejecuta `status`, THE CLI SHALL informar `activo`, `inactivo` o `parcial` según el contenido real de `settings.json`, sin escribir ni exigir TTY.
- REQ-08: IF `on`, `off` o `uninstall` se ejecutan con `CLAUDECODE` definido o stdin no TTY, THEN THE CLI SHALL devolver 1 con `ERROR:` sin escribir.
- REQ-09: WHEN el humano ejecuta `uninstall`, THE CLI SHALL quitar archivos propios, `CLAUDE.microsdd.md`, el bloque de `CLAUDE.md`, lo registrado en `settings.json`, el manifiesto y el alterno heredado, y SHALL conservar `docs/`, `spec/`, `.microharness/memory.json` y lo ajeno.
- REQ-10: IF un archivo propio difiere del payload (sin `--force`) o no hay manifiesto, THEN `uninstall` SHALL devolver 1 sin escribir.
- REQ-11: WHEN `lider`, `autor` o `implementador` usan `Bash`/`PowerShell` para ejecutar `microsdd`/`installer.py` con `on`, `off` o `uninstall`, o mencionan `settings.json`/`settings.local.json` fuera de las formas de solo lectura permitidas, THE hook SHALL denegarlo remitiendo al humano.
- REQ-12: THE documentación SHALL describir el comportamiento nuevo y no afirmar nada que deje de ser cierto.

## Criterios de aceptación
«graphify» = `{"permissions": {"allow": ["Bash(graphify:*)"]}, "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "graphify-guard"}]}], "PostToolUse": [{"matcher": "Write", "hooks": [{"type": "command", "command": "graphify-index"}]}]}}`.

- AC-01: instalación limpia: código 0; `settings.json` byte a byte igual al payload; `.microharness/install.json` con `settings.created = true`; no existe `settings.microsdd.json`; el `git add` impreso incluye `.microharness/install.json` y ningún `.bak`.
- AC-02: fusión con graphify: código 0; `python -m json.tool .claude/settings.json` devuelve 0; `agent = "lider"`, `model = "claude-opus-5-5"`, `effortLevel = "medium"`; `permissions` y `hooks.PostToolUse` iguales a graphify; `hooks.PreToolUse` = entrada de graphify y después, una vez, la del payload; exactamente un `.bak.*` igual al original; sin `settings.microsdd.json`; la salida no contiene «fusionar manualmente». Sustituye a `test_different_settings_is_kept_and_alternate_written`.
- AC-03: con `{"agent": "otro", "model": "x"}`, `install` deja `lider` y `claude-opus-5-5`, guarda los previos y `off` (o `uninstall`) restaura `{"agent": "otro", "model": "x"}`.
- AC-04: un segundo `install` (limpio y con graphify) devuelve 0, árbol idéntico, sin segundo `.bak`, entrada del payload una sola vez; `test_second_run_is_idempotent` sigue pasando.
- AC-05: con `{no json`, `[]`, `{"hooks": []}` y `{"hooks": {"PreToolUse": {}}}`, `install` devuelve 1, menciona `.claude/settings.json` y el árbol queda idéntico; con graphify y `--dry-run` muestra `[fusionar] .claude/settings.json` sin escribir.
- AC-06: tras `install` con graphify, `off` devuelve 0, `settings.json` igual a graphify, respaldo nuevo, `settings.enabled = false`; segundo `off` sin cambios; tras instalación limpia, `off` deja `{}`.
- AC-07: tras `off`, `on` devuelve 0 y reproduce AC-02; segundo `on` sin cambios; `on`/`off` sin manifiesto devuelven 1 sin escribir.
- AC-08: `status` imprime `activo` tras `install`, `inactivo` tras `off` o sin `settings.json`, `parcial` si falta solo el hook o solo `agent`; código 0, no escribe, funciona con `CLAUDECODE` y sin TTY; con JSON inválido devuelve 1.
- AC-09: `main(['on'|'off'|'uninstall', '--target', repo])` con `CLAUDECODE` (aunque vacío), stdin no TTY o `sys.stdin = None` devuelve 1, `ERROR:`, árbol idéntico; sin `CLAUDECODE` y con TTY ejecuta.
- AC-10: con graphify, `CLAUDE.md` = `# Mio\nlinea\n`, `AGENTS.md` y un `settings.microsdd.json` heredado, `install` + `uninstall` dejan `settings.json` igual a graphify, `CLAUDE.md` byte a byte original, `AGENTS.md`, `docs/`, `spec/` y `memory.json` presentes, y eliminan los propios de `MANIFEST`, `CLAUDE.microsdd.md`, `install.json` y `settings.microsdd.json`; en instalación limpia elimina también `settings.json` y `CLAUDE.md` creados si no cambiaron.
- AC-11: si `.claude/agents/lider.md` difiere, `uninstall` devuelve 1 con `conflicto` sin escribir; con `--force` lo elimina y devuelve 0; sin `install.json` devuelve 1 sin escribir.
- AC-12: para `lider`, `autor`, `implementador` × `Bash`, `PowerShell`, `pretool.run()` deniega: `microsdd off`, `microsdd on`, `microsdd uninstall`, `uvx --from git+https://github.com/lgzarturo/microsdd microsdd off`, `python src/microsdd/installer.py off`, `python -m microsdd.installer uninstall`, `sh -c "microsdd off"`, `git -c alias.x=!microsdd x off`, `sed -i s/a/b/ .claude/settings.json`, `echo {} > .claude/settings.json`, `rm .claude/settings.local.json`, `cp a.json .claude/settings.json`, `python -m json.tool .claude/settings.json salida.json`; y permite: `microsdd status`, `uvx --from git+https://github.com/lgzarturo/microsdd microsdd status`, `git add .claude/settings.json`, `git diff .claude/settings.json`, `git status`, `git commit -m "feat(installer): microsdd on y off"`, `python -m json.tool .claude/settings.json`, `python3 -m json.tool .claude/settings.json`, `python -m unittest discover -s tests -v`, `sh .microharness/python.sh .microharness/sdd.py check fusion-settings-toggle`.
- AC-13: para los cuatro roles, `Write`/`Edit`/`MultiEdit`/`NotebookEdit` sobre `.claude/settings.json` y `.claude/settings.local.json` se deniegan (regresión); `uv run --no-project --quiet --python '>=3.10' .claude/hooks/pretool.py` con `{}` por stdin termina en 0 con stdout vacío (se omite sin `uv`).
- AC-14: `SKILL.md` documenta `/sdd on|off|status` (status: el líder lee e informa; on/off: entrega al humano el comando, no lo ejecuta); `CLAUDE.md` deja de afirmar sin condición la configuración; `proceso-versionado.md` no menciona `settings.microsdd.json`, lista `.microharness/install.json` en «Incluido» y actualiza API-05; `README.md` documenta fusión, respaldo, `uninstall`, `on`, `off`, `status` y solo cita `settings.microsdd.json` como heredado.
- AC-15: `python -m unittest discover -s tests -v` termina en 0 (con `tests/test_sdd.py` sin modificar); `git diff HEAD -- .claude/settings.json` vacío.

## Fuera de alcance
- Cambiar payload `.claude/settings.json`, `.claude/agents/`, `.microharness/sdd.py`, `python.sh`, `pyproject.toml`.
- Proteger `.claude/hooks/` frente a `Bash` (R-04).
- Adoptar instalaciones previas sin manifiesto.
- Borrar directorios vacíos, conservar el formato original de `settings.json`, JSON con comentarios.
- Que `off` quite el bloque de `CLAUDE.md`.
- `CHANGELOG.md` y SemVer del commit (D-03).
