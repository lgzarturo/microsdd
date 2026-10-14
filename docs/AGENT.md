# AGENT

Hechos del arnés MicroSDD (verificados en el repo):

- Agente principal: `lider` (`.claude/settings.json`).
- Instalador (`src/microsdd/installer.py`): si `.claude/settings.json` ya existe, fusiona `agent`/`model`/`effortLevel` y el hook `PreToolUse` sin borrar hooks ajenos; si no existe, lo crea desde el payload.
- Manifiesto: `.microharness/install.json` registra lo añadido/reemplazado.
- CLI instalador: `microsdd install|uninstall|on|off|status|worktree` (`on`/`off`/`uninstall`/`worktree sync` con puerta humana).
- Ya no se usa `.claude/settings.microsdd.json` (alterno eliminado).
- Contrato del arnés (preferido): `python .microharness/sdd.py --help`; Unix: `sh .microharness/python.sh .microharness/sdd.py --help`; Windows: `python .microharness\sdd.py --help` o `.\.microharness\python.ps1`.
- Worktrees: `microsdd worktree sync <ruta>` copia arnés y `docs/`; `memory.json` es local al worktree (ver `assets/windows-worktrees.md`).
