# Arquitectura comprobada

Solo componentes, interfaces e invariantes observados en el repositorio.

## Componentes

- **Arnés (se instala en cada proyecto):** `.claude/settings.json` (agente `lider`, modelo, esfuerzo, hook `PreToolUse`), `.claude/agents/*.md` (4 roles), `.claude/hooks/pretool.py` (límites de edición/Bash por agente, best effort), `.claude/skills/sdd/SKILL.md`, `.microharness/sdd.py` (máquina de tres estados, huellas SHA-256, alcance por `git diff`, puerta de pruebas) y `CLAUDE.md`.
- **Instalador (solo en este repositorio):** `pyproject.toml` (paquete `microsdd`, build con hatchling, sin dependencias de ejecución) y `src/microsdd/installer.py`. El wheel incluye los archivos del arnés como `microsdd/payload/...` mediante `force-include`.
- **Pruebas:** `tests/test_sdd.py` (controlador y hook) y `tests/test_installer.py` (instalador, incluido build real del wheel si hay `uv`).

## Invariantes

- `sdd.py` obtiene el diff con `git -z` y UTF-8 (`diff_files`); las rutas son relativas a la raíz Git, por eso el arnés debe vivir en la raíz del repositorio.
- El manifiesto del instalador vive en `installer.py` (`MANIFEST`) y `pyproject.toml` lo replica; `tests/test_installer.py` (AC-10) verifica la coherencia contra el wheel.
- El instalador no escribe nada antes de validar destino, `python3` y conflictos; nunca sobrescribe `CLAUDE.md` ni `.claude/settings.json` del destino (anexa un bloque marcado con `@CLAUDE.microsdd.md` y usa `.claude/settings.microsdd.json`); `--force` solo afecta archivos propios del arnés.
- Los `docs/` del destino los genera `sdd.py init`; los `docs/` de este repositorio describen a MicroSDD y no se distribuyen.
- El hook se invoca como `python3`; en Windows corre en Git Bash, por lo que solo un `python3.exe` real lo activa.
- `scripts/limpiar_arnes.py` (solo en este repositorio, no se distribuye): antes de un release exige árbol git limpio y todas las tareas en `terminado`; archiva `.microharness/memory.json`, `docs/` y `spec/<slug>/` en `historial/<versión>/` y restaura el estado inicial ejecutando `.microharness/sdd.py init`. No hace commit, tag ni push.
