# Proceso de versionado de MicroSDD

## Propósito y alcance

Este documento regula cómo se versiona el arnés MicroSDD: qué constituye su API pública, cómo se calcula cada incremento de versión, qué reglas rigen mientras la versión mayor sea 0, qué criterios deben cumplirse para declarar 1.0.0, cómo se nombran los tags y prereleases, cómo se ejecuta un release dentro del flujo MicroSDD y qué archivos forman una instalación.

Se basa en Semantic Versioning 2.0.0 (https://semver.org/lang/es/) y en Conventional Commits 1.0.0 (https://www.conventionalcommits.org/es/v1.0.0/), en la medida en que `commit-check` los valida.

`assets/` es material de consulta del repositorio del arnés y no forma parte de la instalación. Todo lo marcado como futuro o como propuesta en este documento no existe aún en el repositorio.

## Estado actual

- El árbol de trabajo prepara `1.4.0`: `CHANGELOG.md` incluye `[1.4.0]` y documenta `[1.3.1]`; `.microharness/sdd.py` define `__version__ = '1.4.0'`, replicada en `pyproject.toml`. Perfiles de modelo (`probado`|`experimental`) con `config.json` como fuente de verdad. Último tag publicado: `v1.2.1`. Orden de merge: **PR #12 primero** (solo-líder, sin bump), luego este PR (`1.4.0`).
- El árbol de trabajo prepara `1.3.0`: `CHANGELOG.md` incluye `[1.3.0]`; `.microharness/sdd.py` define `__version__ = '1.3.0'`, replicada en `pyproject.toml`. ODD/RDD ejecutables (reintentos, Write, progress, recibo, kill switch). Con `agent_may_approve` true, solo el líder usa `approve`/`seal`/`allow-test-command` con `@note`.


## API pública

- **API-06** · `.claude/settings.json` (agente predeterminado, modelo, esfuerzo y registro del hook, que el instalador crea o fusiona), la skill `/sdd` (incluido `/sdd on|off|status`), la skill `/sdd-security` (solo bajo demanda) y el esquema de `.microharness/install.json` (`schema_version` 1) del que dependen `uninstall`, `on` y `off`.

### Incluido

- `.claude/skills/sdd/SKILL.md`
- `.claude/skills/sdd-security/SKILL.md`
- `.claude/skills/sdd-security/references/patrones-peligrosos.md`
- `.claude/skills/sdd-security/references/herramientas-bloqueo.md`
