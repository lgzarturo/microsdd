# AGENT

Hechos del arnés MicroSDD (verificados en el repo):

- Agente principal: `lider` (`.claude/settings.json`).
- Instalador (`src/microsdd/installer.py`): si `.claude/settings.json` ya existe, fusiona `agent`/`model`/`effortLevel` y el hook `PreToolUse` sin borrar hooks ajenos; si no existe, lo crea desde el payload.
- Manifiesto: `.microharnéss/install.json` registra lo añadido/reemplazado.
- CLI: `microsdd install|uninstall|on|off|status` (`on`/`off`/`uninstall` con puerta humana).
- Ya no se usa `.claude/settings.microsdd.json` (alterno eliminado).
- Contrato: `sh .microharnéss/python.sh .microharnéss/sdd.py --help`.
