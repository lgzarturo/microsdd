# Registro de cambios

Formato y reglas: `assets/proceso-versionado.md` (R-04). Entradas derivadas de los asuntos de commit; se omiten los commits de merge, que no aportan cambios propios (su contenido figura en los commits integrados).

## [1.2.1] - 2026-10-15

### Añadido
- `docs`: definiciones operativas de SDD (primario), ODD (Outcomes-Driven) y RDD (Receive-Driven, cuatro lentes) en agentes y `assets/arnes-completo.md`

### Otros
- `docs`: pulido conciso y model-agnóstico de `.claude/agents/{autor,implementador,lider,revisor}.md` (sin cambiar el flujo `agent_may_approve` / `@note`)

## [1.2.0] - 2026-10-14

### Incompatible
- `sdd`: `seal` exige `--evidence`; con `agent_may_approve` el hook puede permitir approve/seal/allow-test-command con `@note`

### Añadido
- `sdd`: `agent_may_approve` en `config.json` (default true); notas con id y `--for-task`/`--for-phase`; consumo `@note:<id>` (máx. 30 min)
- `sdd`: subcomando `allow-test-command`
- `hook`: permite approve/seal/allow-test-command solo con `--evidence @note:<id>` si el modo está activo
- `tests`: `tests/test_agent_may_approve.py`

## [1.1.3] - 2026-10-13

### Incompatible
- Ninguno (compatible con 1.1.2).

### Añadido
- `instalador`: `microsdd worktree sync <ruta>` con puerta humana (TTY, sin `CLAUDECODE`); copia arnés y `docs/`; memoria local al worktree; `--with-memory` copia explícita
- `.microharness/python.ps1` y `.microharness/python.cmd` (Windows); preferencia documentada `python .microharness/sdd.py`
- `hook`: lanzadores Windows (`python.exe`, `py -3`, `& python`, `python.ps1`, `python.cmd`, `pwsh`/`powershell -File`); mensajes OS-aware
- `tests`: `tests/test_windows_1113.py`
- `assets/windows-worktrees.md`; plantilla CI matrix en `assets/ci-matrix-windows.yml` (aplicar a `.github/workflows/tests.yml` con permiso `workflow`)

### Corregido
- `sdd`: mensaje de lock (`reintenta`); ejemplos OS-aware en `approve`/`seal`

## [1.1.2] - 2026-10-13

### Incompatible
- `sdd`: `approve`/`seal` exigen TTY y ausencia de `CLAUDECODE` también al importar (no solo en `main`)
- `hook`: planes solo en raíz de `~/.claude/plans/*.md` y solo el líder; cadenas con settings/protegidos denegadas aunque el primer segmento sea lectura

### Corregido
- `hook`: `jq -i`/`--in-place` no cuenta como lectura de settings
- `hook`: `cat settings && rm …` y similares → denegación por encadenado (H5)
- `hook`: `head`/`tail`/`grep`/`rg` permiten leer settings(.local).json
- `hook`: líder/autor no escriben ejecutables ni shebang bajo `docs/` ni `spec/`; Bash deniega `python[3] docs|spec/*.py`

### Añadido
- `sdd`: mutadores de memoria (`approve`/`seal`/`note`/`review`) rechazan si `memory_integrity` ya falla
- `assets`: documenta aprobación firmada como trabajo futuro (sin implementar firmas)
- `tests`: `tests/test_security_1112.py` (H1–H5)

## [1.1.1] - 2026-10-13

### Corregido
- `hook`: parte Bash/PowerShell por `&&`/`||`/`;` y valida cada segmento (cierra bypass `check && approve`)
- `hook`: detecta `approve`/`seal` con cualquier lanzador o ruta; mensajes accionables
- `hook`: permite `cat`/`jq` de settings(.local).json; Write de `~/.claude/plans/*.md`; `git commit -m` aunque el mensaje mencione sdd.py

### Añadido
- `instalador`: crea o fusiona `.claude/settings.local.json` (`claudeMdExcludes`, `plansDirectory`) sin pisar claves existentes
- `ci`: workflow GitHub Actions `tests.yml` con unittest en Python 3.12
- `tests`: regresión de bypass en `tests/test_hook_bypass_111.py`

## [1.1.0] - 2026-10-13

### Incompatible
- `instalador`: fusiona `.claude/settings.json` en lugar de escribir `settings.microsdd.json` (3dc8f0a)

### Añadido
- `instalador`: manifiesto `.microharness/install.json` (3dc8f0a)
- `instalador`: `microsdd on|off|status|uninstall` con puerta humana (3dc8f0a)
- `hook`: deniega que el agente desactive el arnés o edite settings desde Bash/PowerShell (3dc8f0a)

### Otros
- `docs`: documenta fusión, toggle y desinstalación; README reducido con detalle en `assets/arnes-completo.md`
- `assets`: actualiza «Estado actual» del proceso de versionado hacia 1.1.0

## [1.0.0] - 2026-10-13

### Incompatible
- `spec`: renombra diseño.md a plan.md en las 15 tareas (289b996)
- `docs`: renombra convensiones.md y specificaciones.md (64e4733)
- `hook`: impide que los agentes aprueben, sellen o editen la memoria

