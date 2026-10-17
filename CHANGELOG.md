# Registro de cambios

Formato y reglas: `assets/proceso-versionado.md` (R-04). Entradas derivadas de los asuntos de commit; se omiten los commits de merge, que no aportan cambios propios (su contenido figura en los commits integrados).

## [1.3.0] - 2026-10-17

### Añadido
- `sdd` / ODD: `odd_max_retries` en `config.json` (default 3); `note --for-phase odd-retry` registra reintentos con stacktrace y detiene al llegar al límite
- `sdd` / ODD: `note --progress` / `--discovery` escriben en `project.progress` y `project.discoveries` (schema vacío en `init`)
- `hook` / ODD: bloquea `Write` del implementador sobre archivos existentes; Edit/MultiEdit si `old_string` cubre ≥ `odd_rewrite_percent` (default 80%) del disco
- `sdd` / RDD: al `approve … spec` genera `receipt` (digest + hashes de archivos del alcance); el hook rechaza rutas fuera del recibo (casefold en Windows; destino real de symlinks)
- `hook` / RDD: kill switch `rdd_max_files` (default 20) y `rdd_max_lines` (default 500, **ado aproximado por tarea en `rdd_runtime.json` no versionado; defensa global del implementador)
- `tests`: `tests/test_odd_rdd.py`

## [1.2.1] - 2026-10-15

### Añadido
- `docs`: definiciones operativas de SDD (primario), ODD (Organic-Driven Development: fragmentar–validar–reintentar–note) y RDD (Receive-Driven, cuatro lentes) en agentes y `assets/arnes-completo.md`

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

### Añadido
- definir espacio de memoria (bd91f95)
- documento base para el contexto (bb78aba)
- definición del agente líder (c203f0d)
- definición del agente autor (36d0181)
- definición del agente implementador (f1cd53b)
- hook simple para el orquestador (9629e37)
- definición del flujo sdd para el arnés (471508d)
- `instalador`: instalación por proyecto con uvx (b19fe30)
- `release`: archiva el historial del arnés y restaura el estado inicial (ff1e241)
- `arnes`: detecta y usa Python >=3.10 en cualquier SO, con uv (4c1ef0e)
- `hook`: aplica la guardia del revisor también a PowerShell (8bd4842)
- `sdd`: añade --version y release propose (9778355)
- migrar de diseño.md por plan.md (cddb31a)
- `sdd`: añade subcomando note para observaciones y decisiones (446ca07)
- `sdd`: exige un mínimo de pruebas ejecutadas en check --run (77755eb)
- `sdd`: restringe testing.commands a una lista blanca de runners (3798da3)
- `sdd`: lee modelo y esfuerzo por defecto de .microharness/config.json (9f7c57d)
- `sdd`: detecta alteraciones del historial de memory.json respecto a HEAD (c924414)

### Corregido
- `sdd`: decodifica rutas no ASCII del diff de git (5aba938)
- `sdd`: devuelve rutas no ASCII literales en diff_files (07a4d8d)
- `sdd`: hashes de sellos y specs estables ante CRLF; *.sh con LF (b74c472)
- `sdd`: sellos de pruebas solo se comparan hasta el cierre (7700d3d)
- `hook`: endurece las expresiones permitidas al revisor (e784119)
- `instalador`: exige uv en lugar de python3 y usa sys.executable para init (61bd1ee)
- `hook`: deniega --textconv, -O y --open-files-in-pager al revisor (ad11369)
- `sdd`: escribe memory.json de forma atómica y con lock exclusivo (ffe55d6)
- `hook`: deniega edición y shell a agentes sin rol MicroSDD (5caba80)

### Otros
- información del micro arness sdd (1e73336)
- convenciones, carpeta de trabajo (d3fae00)
- reglas del mini Claude conciso. (54dbf1c)
- buenas prácticas cheatsheet (29611d8)
- información base del arnés (c34c96a)
- se define el requerimiento python3 para el arnés (ee71e32)
- definición del agente revisor (8034cb2)
- `assets`: registra decisiones de diseño del arnés (4f2b274)
- `assets`: define proceso de versionado semver del arnés (aeea32c)
- `licencia`: publica el proyecto bajo licencia MIT (7972c91)
- `assets`: actualiza API pública e instalación del proceso de versionado (5bd110e)
