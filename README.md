# MicroSDD for Claude Opus 5.5

> [!WARNING]
> MicroSDD es un **micro arnés por proyecto**: se instala en la raíz de cada repositorio Git, es agnóstico al stack y trabaja sobre el código base de ese repositorio. **No es un arnés global** ni una configuración de `~/.claude`; el instalador rechaza el directorio home y cualquier ruta bajo `~/.claude`.

> **Propósito:** código mínimo, correcto, verificable y trazable. Claude Code orquesta nativamente. No hay SDK, servidor, base de datos ni dependencia de Python aparte de la biblioteca estándar.

## 1. Requisitos

| Requisito | Versión | Para qué |
|---|---|---|
| **Python** | 3.10+ | Ejecuta `.microharness/sdd.py` y el hook `.claude/hooks/pretool.py` (solo biblioteca estándar). |
| **uv** | reciente, ejecutable real en `PATH` (`uv.exe` en Windows) | Hook en forma exec: `uv run --no-project --quiet --python ">=3.10" …/pretool.py`. |
| Git | reciente | Alcance por diff; el instalador exige la raíz del repo. |
| Claude Code | ≥ 2.1.295 | `onFailure: block`, agente predeterminado y `PreToolUse`. |

En **Windows 11** usa PowerShell 7 o `cmd` con los lanzadores del arnés; **no hace falta Git Bash** para el CLI del arnés. En Unix/macOS sigue disponible `sh .microharness/python.sh`.

Instalación recomendada de uv: https://docs.astral.sh/uv/

Comprobación rápida (misma semántica en todas las plataformas):

```bash
uv --version
python .microharness/sdd.py --version
python .microharness/sdd.py --help
```

```powershell
uv --version
python .microharness\sdd.py --version
.\.microharness\python.ps1 .microharness\sdd.py --help
```

Worktrees Git: `microsdd worktree sync <ruta>` (humano, TTY); ver [assets/windows-worktrees.md](assets/windows-worktrees.md). Detalle del lanzador: [assets/arnes-completo.md](assets/arnes-completo.md). CI: `.github/workflows/tests.yml` (unittest en Ubuntu y Windows).

## 2. Instalación por proyecto

Desde la raíz de un repositorio Git (idealmente rama nueva y working tree limpio):

```bash
uvx --from git+https://github.com/lgzarturo/microsdd microsdd install --dry-run
uvx --from git+https://github.com/lgzarturo/microsdd microsdd install
```

Conviene fijar un tag revisado: `uvx --from git+https://github.com/lgzarturo/microsdd@<tag> microsdd install`.

| Flag | Efecto |
|---|---|
| `--target RUTA` | Raíz del destino (debe ser `git rev-parse --show-toplevel`). |
| `--dry-run` | Plan sin escribir. |
| `--force` | Actualiza solo archivos propios del arnés en conflicto. |

**Fusión de `.claude/settings.json`:** si no existe, se crea desde el payload. Si existe, se hace respaldo `.bak.<UTC>` y se fusionan `agent`, `model`, `effortLevel` y la entrada `PreToolUse` de MicroSDD, conservando el resto; el manifiesto `.microharness/install.json` guarda lo añadido y los valores previos. Ya no se escribe `.claude/settings.microsdd.json` (si queda uno heredado, `uninstall` lo elimina). El instalador también crea o fusiona `.claude/settings.local.json` con `claudeMdExcludes` y `plansDirectory` solo si faltan (archivo local; no falla si no se versiona).

Tras instalar, versiona con `git add` explícito (nunca `git add .`) e inicia sesión:

```bash
claude --agent lider --model claude-opus-5-5 --effort medium
```

(Modelo y esfuerzo: los de `.microharness/config.json` o los defaults del proyecto.)

### Activar, desactivar y consultar

| Comando | Efecto |
|---|---|
| `microsdd status` | Solo lectura: `activo` / `parcial` / `inactivo` (también vía `/sdd status`). |
| `microsdd off` | Retira lo del manifiesto y restaura previos (respaldo `.bak`). Solo humano, TTY, sin `CLAUDECODE`. |
| `microsdd on` | Reaplica la fusión. Mismas restricciones que `off`. |
| `microsdd uninstall` | Quita MicroSDD según el manifiesto; conserva `docs/`, `spec/` y `memory.json`. |
| `microsdd worktree sync <ruta>` | Copia arnés y `docs/` a un worktree; memoria local (opcional `--with-memory`). Solo humano, TTY. |

Sin manifiesto, `on`/`off`/`uninstall` fallan con código 1. Tras `on`/`off`, reinicia Claude Code.

## 3. Uso mínimo

1. Abre el proyecto con `claude --agent lider` (o confía en `agent: lider` del settings fusionado).
2. Encarga el trabajo al líder (`/sdd …` o una petición concreta).
3. Flujo: líder → autor → (aprobación) → implementador → revisor → (aprobación de cierre). Tú apruebas en lenguaje natural. Con `agent_may_approve` (default **true**) el líder registra tu cita en `note` y ejecuta `approve`/`seal` con `--evidence @note:<id>`. No puede demostrar que la frase la escribiste tú. Modo estricto: `{"agent_may_approve": false}` en `.microharness/config.json`.

### ODD y RDD (1.3.0)

En `.microharness/config.json` (opcionales; defaults entre paréntesis):

| Clave | Default | Efecto |
|---|---|---|
| `odd_max_retries` | 3 | Tras fallos de pruebas/análisis, `note --fact … --evidence '<stack>' --for-task <slug> --for-phase odd-retry` cuenta reintentos; al llegar al límite detiene y registra. |
| `odd_rewrite_percent` | 80 | Si `old_string`(s) de Edit/MultiEdit cubren ≥ N% del archivo en disco, el hook lo deniega igual que un Write de reescritura. |
| `rdd_max_files` | 20 | Kill switch: deniega más ediciones si se superarían N archivos distintos del recibo. |
| `rdd_max_lines` | 500 | Kill switch de líneas: **defensa global del implementador** (aplica aunque `method.optional` no incluya RDD). Acumula un conteo **aproximado** por tarea en `.microharness/rdd_runtime.json` (no versionado; `init`/`limpiar_arnes` lo borran). |

- Progreso / descubrimientos: `note --progress '…' --evidence '…'` y `note --discovery '…' --evidence '…'` → `project.progress` / `project.discoveries`.
- Al aprobar la spec se genera un **recibo RDD** (`tasks.<slug>.receipt`) con digest y hashes del alcance; el hook rechaza rutas fuera de ese recibo (en Windows la comparación de rutas es case-insensitive; se sigue el destino real de symlinks).
- El implementador no puede usar `Write` sobre archivos existentes ni Edit/MultiEdit que reescriban casi todo el archivo.

Flujo completo, archivos, máquina de estados y `spec.json`: [assets/arnes-completo.md](assets/arnes-completo.md).

## 4. Más documentación

| Documento | Contenido |
|---|---|
| [assets/arnes-completo.md](assets/arnes-completo.md) | Lanzador, archivos, flujo, ciclo operativo, `spec.json`, obligaciones y fuentes |
| [assets/windows-worktrees.md](assets/windows-worktrees.md) | Windows, PowerShell y `worktree sync` |
| [assets/proceso-versionado.md](assets/proceso-versionado.md) | SemVer, API pública, instalación, releases |
| [assets/decisiones-diseno.md](assets/decisiones-diseno.md) | Decisiones de diseño y fuentes |
| [assets/eval-esfuerzo.md](assets/eval-esfuerzo.md) | Protocolo medium vs high (no ejecutado) |
| [assets/aprobacion-firmada-futuro.md](assets/aprobacion-firmada-futuro.md) | Aprobación firmada (futuro; no implementada en 1.1.2) |

## 5. Licencia

MicroSDD se distribuye bajo la licencia MIT. Copyright (c) 2026 Arturo López. Consulte [LICENSE](LICENSE).

Los archivos que `microsdd install` copia en otro repositorio siguen bajo MIT; conserve el aviso de copyright y de permiso (el instalador no los añade por usted).
