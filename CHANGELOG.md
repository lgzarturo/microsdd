# Registro de cambios

Formato y reglas: `assets/proceso-versionado.md` (R-04). Entradas derivadas de los asuntos de commit; se omiten los commits de merge, que no aportan cambios propios (su contenido figura en los commits integrados).

## [1.5.3] - 2026-10-21

### Corregido
- `hook`: reconoce rutas absolutas de Windows (`X:\...`) en comandos shell; `windows-latest` vuelve a verde en CI

### Documentación / SemVer
- Nota: el tag `v1.5.2` se publicó sobre el commit de archivado sin bump (código en `1.5.1`); este release publica el contenido como `1.5.3` sin mover el tag.

## [1.5.1] - 2026-10-21

### Corregido
- `metrics`: `HARNESS_VERSION` rezagado en `1.4.0`; ahora coherente con la versión del paquete (`1.5.1`)

## [1.5.0] - 2026-10-21

### Añadido
- `sdd`: loop autónomo del líder con lease por fingerprint de spec (`seal` y `approve close` sin `@note` bajo lease íntegro) y testigo quirúrgico `spec/<slug>/testigo.md` sellado al cerrar
- `bench`: provider Claude Code/OpenRouter y workflow cheap
- `bench`: m2 — suite de 5 tareas, runner fake y prompt-diff
- `metrics`: módulo opcional harness-telemetry/v1 y hooks async

### Corregido
- `bench`: presupuesto de solicitudes por turnos y corte por cuota
- `hook`: permite al implementador editar bench.py y metrics.py
- `bench`: test CLI acepta baselineStatus cheap-partial
- `bench`: veredicto sin datos, diagnóstico Claude y smoke Actions
- `bench`: candado OpenRouter con limit ≤$5 y delta de usage
- `bench`: reporte ASCII-compatible con cp1252
- `bench`: evita Unicode en el reporte por consola Windows
- `metrics`: hashea bytes reales del esquema (sin normalizar CRLF)
- `metrics`: compatibilidad Windows en hash del esquema y estado

## [1.4.0] - 2026-10-17

### Añadido
- `sdd` / modelo: `config.json` es la fuente de verdad de `model`/`effort`; perfiles con `status` `probado`|`experimental` (default built-in `opus-5-5-medium` = `claude-opus-5-5` + `medium`, **probado**; el resto experimental salvo evidencia en el repo)
- `sdd` / `check`: valida alineación de `.claude/settings.json` (`model`, `effortLevel`) y del frontmatter de los cuatro agentes con la config; reporta diferencias
- `instalador`: aplica modelo/esfuerzo efectivos del `config.json` del destino (o defaults) a settings y frontmatter al instalar/fusionar
- `sdd` / `new`: copia `profile_status: "experimental"` en `spec.json` cuando el runtime no es un perfil probado
- `tests`: `tests/test_model_profiles.py`

### Corregido
- Incluye el cambio de [PR #12](https://github.com/lgzarturo/microsdd/pull/12) (sin bump propio): con `agent_may_approve` true, solo el rol `lider` puede `approve`/`seal`/`allow-test-command` con `--evidence @note:<id>`

### Documentación / SemVer
- Estado real antes de este PR: último tag `v1.2.1`; código y CHANGELOG en `1.3.0` (ODD/RDD, sin tag); existe `historial/1.3.1/` sin entrada `[1.3.1]` ni bump de paquete.
- **Orden de merge:** 1) mergear [#12](https://github.com/lgzarturo/microsdd/pull/12) (solo-líder, **sin** tocar versión ni `historial/`); 2) mergear este PR → `main` queda en **`1.4.0`**.
- Conservar `historial/1.3.1/` (archivo prematuro). No crear `historial/1.3.2/`.
- Tags pendientes tras ambos merges (no ejecutar aquí): `v1.3.0` (ODD/RDD), `v1.3.1` (opcional, sobre el fix ODD / archivo), `v1.4.0` (este release).

## [1.3.1] - 2026-10-17

### Corregido
- `hook` / ODD: reescritura vía Edit/MultiEdit, líneas acumuladas del kill switch y recibo RDD (casefold / symlinks)
- Nota: `historial/1.3.1/` archivó el arnés tras ese fix, pero el paquete no se subió a `1.3.1` en su momento; esta entrada cierra el hueco en el CHANGELOG. Tag `v1.3.1` opcional a posteriori.

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
