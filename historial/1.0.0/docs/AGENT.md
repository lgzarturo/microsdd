# Contexto del repositorio

- **Aplicación:** MicroSDD for Claude Opus 5.5, micro arnés SDD por proyecto para Claude Code (agentes `lider`, `autor`, `implementador`, `revisor`) más su instalador. Solo biblioteca estándar de Python 3.10+.
- **Punto de entrada:** `.microharness/sdd.py` (CLI de estados, aprobaciones y puerta de pruebas); instalador `microsdd install` (`src/microsdd/installer.py`, script declarado en `pyproject.toml`).
- **Comandos habituales (comprobados en Windows 11 + Git Bash):**
  - CLI: `sh .microharness/python.sh .microharness/sdd.py --help` (alternativa sin `sh`: `uv run --no-project --python ">=3.10" .microharness/sdd.py --help`).
  - Pruebas: `sh .microharness/python.sh -m unittest discover -s tests -v`.
  - Instalación en otro repositorio: `uvx --from git+https://github.com/lgzarturo/microsdd microsdd install`.
  - En Windows `python3` puede ser el stub de Microsoft Store (exit 49 en Git Bash): no usarlo directamente.
- **Límites operativos:** no editar fuera del alcance aprobado; revisión humana de cada spec y cierre.
- **Fuente de verdad:** código y pruebas existentes, después specs aceptadas y decisiones registradas.

> El líder completará únicamente datos observados; marcará explícitamente cualquier incertidumbre.
