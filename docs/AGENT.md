# Contexto del repositorio

- **Aplicación:** MicroSDD for Claude Opus 5.5, micro arnés SDD por proyecto para Claude Code (agentes `lider`, `autor`, `implementador`, `revisor`) más su instalador. Solo biblioteca estándar de Python 3.10+.
- **Punto de entrada:** `.microharness/sdd.py` (CLI de estados, aprobaciones y puerta de pruebas); instalador `microsdd install` (`src/microsdd/installer.py`, script declarado en `pyproject.toml`).
- **Comandos habituales:** pruebas `python -m unittest discover -s tests -v`; puerta `python .microharness/sdd.py check <slug> --run`; instalación en otro repo `uvx --from git+https://github.com/lgzarturo/microsdd microsdd install`. En la máquina del mantenedor (Windows) `python3` es el alias de Microsoft Store: usar `python`.
- **Límites operativos:** no editar fuera del alcance aprobado; revisión humana de cada spec y cierre.
- **Fuente de verdad:** código y pruebas existentes, después specs aceptadas y decisiones registradas.

> El líder completará únicamente datos observados; marcará explícitamente cualquier incertidumbre.
