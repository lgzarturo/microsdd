# MicroSDD for Claude Opus 5.5

> [!WARNING]
> MicroSDD es un **micro arnés por proyecto**: se instala en la raíz de cada repositorio Git, es agnóstico al stack y trabaja sobre el código base de ese repositorio. **No es un arnés global** ni una configuración de `~/.claude`; el instalador rechaza el directorio home y cualquier ruta bajo `~/.claude`.

> **Propósito:** código mínimo, correcto, verificable y trazable. Claude Code orquesta nativamente. No hay SDK, servidor, base de datos ni dependencia de Python aparte de la biblioteca estándar.

## 1. Requisitos

| Requisito | Versión | Para qué |
|---|---|---|
| **Python** | 3.10+ | Ejecuta `.microharness/sdd.py` y el hook `.claude/hooks/pretool.py` (solo biblioteca estándar). |
| **uv** | reciente, ejecutable real en `PATH` (`uv.exe` en Windows) | Hook en forma exec: `uv run --no-project --quiet --python ">=3.10" …/pretool.py`. |
| `sh` POSIX | macOS/Linux; Git Bash en Windows | Lanzador `.microharness/python.sh`. |
| Git | reciente | Alcance por diff; el instalador exige la raíz del repo. |
| Claude Code | ≥ 2.1.295 | `onFailure: block`, agente predeterminado y `PreToolUse`. |

Instalación recomendada de uv: https://docs.astral.sh/uv/ (macOS/Linux: curl del instalador oficial; Windows: script PowerShell oficial). En Windows hace falta Git for Windows para `sh`.

Comprobación rápida:

```bash
uv --version
sh .microharness/python.sh --version
sh .microharness/python.sh .microharness/sdd.py --help
```

Detalle del lanzador, lista blanca de runners, `min_tests`, sesiones sin rol y límites del MVP: [assets/arnes-completo.md](assets/arnes-completo.md). CI: `.github/workflows/tests.yml` (unittest). Detalle de seguridad 1.1.2 (H1–H5): [CHANGELOG](CHANGELOG.md) y [aprobacion-firmada-futuro.md](assets/aprobacion-firmada-futuro.md).

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

### Activar, desactivar y consultar

| Comando | Efecto |
|---|---|
| `microsdd status` | Solo lectura: `activo` / `parcial` / `inactivo` (también vía `/sdd status`). |
| `microsdd off` | Retira lo del manifiesto y restaura previos (respaldo `.bak`). Solo humano, TTY, sin `CLAUDECODE`. |
| `microsdd on` | Reaplica la fusión. Mismas restricciones que `off`. |
| `microsdd uninstall` | Quita MicroSDD según el manifiesto; conserva `docs/`, `spec/` y `memory.json`. |

Sin manifiesto, `on`/`off`/`uninstall` fallan con código 1. Tras `on`/`off`, reinicia Claude Code.

## 3. Uso mínimo

1. Abre el proyecto con `claude --agent lider` (o confía en `agent: lider` del settings fusionado).
2. Encarga el trabajo al líder (`/sdd …` o una petición concreta).
3. El líder delega en autor → implementador → revisor; **tú** apruebas `spec` y `close` en tu terminal (fuera de Claude Code).

Flujo completo, archivos, máquina de estados y `spec.json`: [assets/arnes-completo.md](assets/arnes-completo.md).

## 4. Más documentación

| Documento | Contenido |
|---|---|
| [assets/arnes-completo.md](assets/arnes-completo.md) | Lanzador, archivos, flujo, ciclo operativo, `spec.json`, obligaciones y fuentes |
| [assets/proceso-versionado.md](assets/proceso-versionado.md) | SemVer, API pública, instalación, releases |
| [assets/decisiones-diseno.md](assets/decisiones-diseno.md) | Decisiones de diseño y fuentes |
| [assets/eval-esfuerzo.md](assets/eval-esfuerzo.md) | Protocolo medium vs high (no ejecutado) |
| [assets/aprobacion-firmada-futuro.md](assets/aprobacion-firmada-futuro.md) | Aprobación firmada (futuro; no implementada en 1.1.2) |

## 5. Licencia

MicroSDD se distribuye bajo la licencia MIT. Copyright (c) 2026 Arturo López. Consulte [LICENSE](LICENSE).

Los archivos que `microsdd install` copia en otro repositorio siguen bajo MIT; conserve el aviso de copyright y de permiso (el instalador no los añade por usted).
