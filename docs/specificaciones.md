# Índice de especificaciones

Cada tarea va en `spec/<slug>/` con exactamente cuatro documentos: `requerimientos.md`, `diseño.md`, `tareas.md`, `spec.json`.

- Estado: `pendiente`, `proceso`, `terminado` (únicos estados).
- Flujo: solicitud → autor → aprobación humana de spec → implementador → revisor y check → aprobación humana de cierre → commit.
- Rechazo: registra motivo en `.microharness/memory.json` y vuelve a `proceso` si quedan intentos; si necesita decisión humana o agota intentos, `pendiente`.
- Un cambio en requisitos aprobado reinicia revisión de impacto y requiere nueva aprobación.
- SDD es obligatorio; ODD = Organic Driven Development solo si se define operativamente para esa tarea. RDD es ambiguo: no se activa sin definición explícita; ninguno sustituye los criterios de aceptación.
- Se exige resultado ejecutado de pruebas declaradas antes de cerrar. Pruebas selladas se comparan contra hashes SHA-256; cambio autorizado requiere nuevo sellado humano. No es DRM ni garantía criptográfica frente a quien controle el repo.

| Tarea | Estado | Resumen |
|---|---|---|
| `fix-sdd-rutas-unicode` | terminado | `diff_files()` usa `git -z` y UTF-8: rutas no ASCII (p. ej. `diseño.md`) ya no rompen el alcance ni la huella |
| `instalador-uvx` | terminado | Instalador por proyecto `uvx ... microsdd install`: idempotente, sin pisar archivos compartidos, exige `python3` real (en Windows `python3.exe`) |
| `licencia-mit` | terminado | Licencia MIT (2026, Arturo López) en `LICENSE`, metadatos PEP 639 en `pyproject.toml` y sección 10 del README |
| `limpieza-historial-release` | terminado | `scripts/limpiar_arnes.py <versión>` archiva memoria, docs y specs en `historial/<versión>/` y restaura el estado de `sdd.py init` antes de un release |
| `regex-revisor-ascii` | terminado | Allowlist del revisor: versión con `[0-9]`; `git diff/status` solo con tokens seguros, sin `--output` ni `--ext-diff`. |
| `hook-powershell` | terminado | Matcher del hook incluye `PowerShell`; la allowlist del revisor se aplica a `Bash` y `PowerShell`. |
| `sellos-solo-en-proceso` | terminado | `validate` compara `sealed_tests` solo mientras la tarea no esté `terminado`; tras el cierre el sello es histórico. |
| `eol-hashes-estables` | terminado | `hash_file` y `spec_fingerprint` normalizan CRLF→LF; `.gitattributes` fija `*.sh text eol=lf`. |
| `deteccion-python-multiplataforma` | terminado | Hook en forma exec con uv y `onFailure: block`; lanzador `.microharness/python.sh` con detección de Python ≥3.10; `check --run` usa `sys.executable`. |
| `fix-quotepath-diff` | terminado | `diff_files()` devuelve rutas no ASCII literales (`core.quotePath=false` + UTF-8); `check` deja de fallar en falso por `diseño.md`. |
| `fundamentos-diseno` | terminado | Registro de decisiones de diseño del arnés en `assets/decisiones-diseno.md` (no se instala) |
| `proceso-versionado` | terminado | Proceso de versionado SemVer del arnés en `assets/proceso-versionado.md`; `assets/` excluido de la instalación |
| `herramienta-release` | terminado | `sdd.py --version` (`__version__`) y `sdd.py release propose` (solo lectura: propone la versión desde Conventional Commits) |
