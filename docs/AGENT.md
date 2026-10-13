# Contexto del repositorio

- **Aplicación:** MicroSDD, miniarnés de desarrollo guiado por especificaciones para Claude Code (agentes `lider`, `autor`, `implementador`, `revisor`; controlador `.microharness/sdd.py`; guardia `.claude/hooks/pretool.py`).
- **Punto de entrada:** `.microharness/sdd.py` (CLI) y el hook `PreToolUse` de `.claude/settings.json`.
- **Comandos habituales (comprobados en Windows 11 + Git Bash):**
  - CLI: `sh .microharness/python.sh .microharness/sdd.py --help` (alternativa sin `sh`: `uv run --no-project --python ">=3.10" .microharness/sdd.py --help`).
  - Pruebas: `sh .microharness/python.sh -m unittest discover -s tests -v`.
  - En Windows `python3` puede ser el stub de Microsoft Store (exit 49 en Git Bash): no usarlo directamente.
- **Límites operativos:** no editar fuera del alcance aprobado; revisión humana de cada spec y cierre.
- **Fuente de verdad:** código y pruebas existentes, después specs aceptadas y decisiones registradas.

> El líder completará únicamente datos observados; marcará explícitamente cualquier incertidumbre.
