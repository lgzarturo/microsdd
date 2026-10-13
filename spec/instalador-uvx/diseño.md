# CÓMO: diseño mínimo

## Situación comprobada
Hechos verificados en el repositorio y en el entorno (aportados por el líder y contrastados donde fue posible):

1. En Windows, `python3` suele ser el stub de Microsoft Store (`WindowsApps`); los hooks de Claude Code corren en Git Bash y una salida distinta de 0/2 es no bloqueante, por lo que `.claude/hooks/pretool.py` queda inactivo en silencio. En esta máquina `python3` falla. Por eso el instalador debe EJECUTAR `python3` y leer su versión; `shutil.which` no basta.
2. Bajo uvx el PATH puede anteponer el entorno aislado: hay que buscar `python3` en un PATH sin el directorio `bin`/`Scripts` de `sys.prefix` cuando `sys.prefix != sys.base_prefix`. Se implementa como función pura sobre cadenas (testeable sin entorno real).
3. `CLAUDE.md` admite `@ruta` (relativa al archivo, sin diálogo si es interna al proyecto); los comentarios HTML de bloque se eliminan del contexto; si existe `AGENTS.md` y se crea `CLAUDE.md`, Claude deja de leer `AGENTS.md` (de ahí anteponer `@AGENTS.md`).
4. `.microharness/sdd.py` calcula el diff relativo a la raíz Git (`diff_files`, líneas 130-140; usa `ROOT` = padre de `.microharness`): el destino debe ser `git rev-parse --show-toplevel`.
5. `sdd.py init` (`ensure_init`, líneas 47-56) ya crea `docs/` (4 documentos), `spec/` y `memory.json` sin sobrescribir: se reutiliza por subprocess con `python3`; no se copian los `docs/` de este repositorio.
6. Todo `.md` en `.claude/agents/` se carga como agente: los archivos propios no usan alterno (un `lider.microsdd.md` duplicaría el agente).

7. (Enmienda, verificado por el revisor) En esta máquina existe `C:\Users\R2D2\AppData\Roaming\Python\Python312\Scripts\python3.CMD` (`python %*`) antes de `WindowsApps` en el PATH. `shutil.which('python3')` en Windows lo encuentra vía PATHEXT y la verificación pasaba, pero Git Bash (donde Claude Code corre el hook) no ejecuta `.CMD` y resuelve `python3` al stub de la Store (exit 49): el instalador aprobaba un entorno con el hook inactivo.
8. (Enmienda) `.claude/hooks/pretool.py` emite `deny` tanto en la regla del revisor (línea 17: "El revisor es solo lectura.") como en su rama de error "Guardia inválida" (línea 83): buscar solo `deny` deja pasar un hook roto.

Comprobado además en el árbol actual: existen `.claude/agents/{lider,autor,implementador,revisor}.md`, `.claude/hooks/pretool.py`, `.claude/skills/sdd/SKILL.md`, `.claude/settings.json` (con `agent: lider` y hook `PreToolUse` que invoca `python3`), `.microharness/sdd.py`, `CLAUDE.md`, `README.md`, `tests/test_sdd.py` (carga el módulo por ruta con `importlib.util`, líneas 8-11). No existen `pyproject.toml` ni `src/`. `pretool.py` emite `permissionDecision: "deny"` según `agent_type`.

Supuestos (no verificados aquí): disponibilidad de `uv` en la máquina de pruebas; comportamiento de hatchling con `force-include` hacia el wheel construido desde sdist (lo verifica AC-10).

## Decisión y justificación
Paquete Python mínimo `microsdd` ejecutable con uvx, solo biblioteca estándar.

Archivos:
- `pyproject.toml` (nuevo): `name="microsdd"`, `version="0.1.0"`, `requires-python=">=3.10"`, `dependencies=[]`, `[project.scripts] microsdd="microsdd.installer:main"`, `build-backend` hatchling con versión mínima fijada; `[tool.hatch.build.targets.wheel] packages=["src/microsdd"]`; `force-include` explícito por cada archivo del manifiesto hacia `microsdd/payload/<ruta>` (incluido `.claude/settings.json` y `CLAUDE.md`); `include` del sdist con esas rutas + `src` + `README.md` + `pyproject.toml`.
- `src/microsdd/__init__.py` (nuevo, mínimo).
- `src/microsdd/installer.py` (nuevo, solo stdlib): manifiesto como única fuente; payload en `Path(__file__).parent / "payload"`; función `install(source, target, *, python, home, force, dry_run)` con dependencias inyectables; `main()` con argparse (subcomando `install`, flags `--target`, `--dry-run`, `--force`).
- `tests/test_installer.py` (nuevo, unittest; importa `src/microsdd/installer.py` por ruta como `tests/test_sdd.py`; usa el propio repo como `source`).
- `README.md` (modificar).

Manifiesto:
| Origen | Destino | Clase | Si existe y difiere |
|---|---|---|---|
| `.claude/agents/{lider,autor,implementador,revisor}.md`, `.claude/hooks/pretool.py`, `.claude/skills/sdd/SKILL.md`, `.microharness/sdd.py` | misma ruta | propio | conflicto: exit 1 sin escribir; `--force` sobrescribe |
| `CLAUDE.md` (del repo) | `CLAUDE.microsdd.md` | propio | igual que arriba |
| generado | `CLAUDE.md` | compartido | anexar bloque una vez (marcador `<!-- microsdd:begin -->`); si falta, crear (con `@AGENTS.md` si existe `AGENTS.md`) |
| `.claude/settings.json` | misma ruta si falta | compartido | nunca se sobrescribe: escribir `.claude/settings.microsdd.json` (propio; si difiere, requiere `--force`) y avisar |
| cualquiera idéntico | — | — | se omite |

Bloque generado: entre `<!-- microsdd:begin -->` y `<!-- microsdd:end -->`, registro de uso ("MicroSDD for Claude Opus 5.5", micro arnés por proyecto, no global) e import `@CLAUDE.microsdd.md`. Se anexa respetando el fin de línea dominante (LF/CRLF) y asegurando salto antes del bloque.

Flujo `install` (planificar todo antes de escribir):
1. Banner (nombre, versión por `importlib.metadata` con fallback `dev`, alerta no global); `sys.stdout.reconfigure(errors="replace")`; sin emoji.
2. Destino == `Path.home()` o bajo `~/.claude` -> exit 1.
3. `git` disponible y destino == `git rev-parse --show-toplevel` (comparación con `resolve` + `os.path.normcase`) -> si no, exit 1.
4. `python3` del PATH filtrado se ejecuta y reporta >= 3.10 -> si no, exit 1 con remediación por SO (Windows: detectar `WindowsApps` y mencionar alias de ejecución; indicar que los shims `.cmd`/`.bat` no sirven para Git Bash; remediaciones como opciones). En Windows (`sys.platform == 'win32'`) se busca solo `python3.exe` (`shutil.which('python3.exe', path=<PATH filtrado>)`, que con extensión explícita ignora `.cmd`/`.bat`), equivalente a la resolución de Git Bash; en otros SO, `python3` sin cambios.
5. Árbol sucio -> advertencia.
6. Clasificar cada entrada: crear / sin cambios / alterno / anexar registro / actualizar (`--force`) / conflicto. Conflicto en propios sin `--force` -> exit 1 sin escribir.
7. `--dry-run` -> imprimir plan, exit 0.
8. Escribir (`shutil.copyfile`; bit ejecutable a `sdd.py` en POSIX).
9. `python3 .microharness/sdd.py init` + smoke del hook: enviar `{"agent_type":"revisor","tool_name":"Edit","tool_input":{}}` por stdin a `.claude/hooks/pretool.py`; la salida debe contener `deny` y el motivo "solo lectura" de la regla del revisor; un `deny` por "Guardia inválida" o un fallo de `init` -> exit 1 (los archivos ya escritos permanecen y se informa).
10. Próximos pasos: `git add <lista exacta>`, fusión de settings si aplica, `claude`.

Códigos de salida: 0 éxito o nada que hacer; 1 precondición, conflicto, o fallo de `init`/smoke después de escribir; 2 uso (argparse; sin subcomando no escribe).

Alternativas descartadas:
- Scripts PowerShell/sh: duplican lógica por SO; decisión humana a favor de uvx.
- `shutil.which("python3")` como verificación: no detecta el stub de Microsoft Store y en Windows acepta shims `.cmd` vía PATHEXT que Git Bash no ejecuta.
- Smoke test que solo busca `deny`: no distingue la regla real del revisor de la rama de error del hook.
- Alternos para archivos propios (`lider.microsdd.md`): duplicarían agentes cargados.
- Copiar `docs/` de este repo: `sdd.py init` ya los genera sin sobrescribir.
- Respaldo `.bak`, registro de hashes, desinstalador, plantillas o capas de abstracción adicionales: YAGNI.
- Dependencias de terceros (click, rich): stdlib basta.

## Invariantes y riesgos
Invariantes:
- Ninguna escritura ocurre antes de que todas las precondiciones y la clasificación terminen sin conflicto.
- `CLAUDE.md` y `.claude/settings.json` existentes nunca se sobrescriben; `CLAUDE.md` solo recibe un anexo único.
- `--force` solo afecta archivos propios del manifiesto.
- El manifiesto vive en un solo lugar (`installer.py`); `pyproject.toml` lo replica explícitamente y AC-10 verifica la coherencia.
- Sin dependencias en tiempo de ejecución.

Riesgos y mitigación:
- Duplicación manifiesto/`pyproject.toml` puede desincronizarse -> AC-10 compara el wheel contra el manifiesto.
- Rutas en Windows (mayúsculas, separadores, symlinks) en la comparación con `show-toplevel` -> `resolve` + `normcase`; prueba de subdirectorio (AC-07).
- En esta máquina `python3` falla: las pruebas deben inyectar el intérprete (`python=sys.executable` o falso), no depender del PATH real.
- Un fallo de `init` o del smoke deja archivos escritos con exit 1: aceptado (sin respaldo ni rollback, fuera de alcance); el README lo documenta.
- Exigir "solo lectura" acopla el smoke al texto de `pretool.py` línea 17; si ese texto cambia, el smoke fallará de forma visible.
- Pasos 9 (init y smoke) dependen de `python3` real del destino; en pruebas se usa el intérprete inyectado.
- Hatchling `force-include` con rutas que empiezan por punto y archivos fuera de `src`: verificado por AC-10 con build desde sdist.
- Uso de `uvx --from git+...` sin tag puede instalar cambios no revisados -> README recomienda fijar tag.

Efectos secundarios: en el destino se crean archivos del arnés, `docs/`, `spec/` y `.microharness/memory.json`; en este repo solo se añaden los archivos del alcance. El hook sigue inactivo en Windows si `python3` es el stub (fuera de alcance; el instalador lo detecta y aborta).
