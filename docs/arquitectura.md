# arquitectura

- MicroSDD: arnés local (`.microharnéss/sdd.py`) + payload Claude (`.claude/`) + instalador Python (`src/microsdd/`).
- Fusión de settings: `install`/`on` escriben `.claude/settings.json` fusionado; `.microharnéss/install.json` guarda previos; `off`/`uninstall` restauran.
- Guardia: `.claude/hooks/pretool.py` (PreToolUse) bloquea que el agente desactive o edite la guardia fuera de alcance.
