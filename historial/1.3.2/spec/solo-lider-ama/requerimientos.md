# QUÉ: requisitos

## Objetivo

Con `agent_may_approve` activo (default true), el hook PreToolUse debe permitir `approve`, `seal` y `allow-test-command` con `--evidence @note:<id>` **solo** al rol `lider`. Autor, implementador y roles ausentes/desconocidos quedan bloqueados (fail closed), con mensaje claro. No cambia el default ni el comportamiento con `agent_may_approve: false`.

## Precondiciones

- Existe `.claude/hooks/pretool.py` con `deny_or_allow_gated` y `run()` que lee `event.get('agent_type')`.
- Existe `tests/test_agent_may_approve.py` con cobertura de `@note`, TTL 30 min y un solo uso.
- README y docs de API ya describen el flujo como «solo el líder».

## Requisitos EARS

- REQ-01: WHEN `agent_may_approve` es true y un agente con `agent_type` distinto de `lider` (incluidos `autor` e `implementador`) invoca `approve`, `seal` o `allow-test-command` con `--evidence @note:<id>` vía Bash/PowerShell, THE hook SHALL denegar la herramienta con un mensaje que indique que solo el líder puede usar esos subcomandos con evidencia `@note`.
- REQ-02: WHEN `agent_may_approve` es true y el agente `lider` invoca `approve`, `seal` o `allow-test-command` con `--evidence @note:<id>`, THE hook SHALL permitir el comando (sin denegar por rol).
- REQ-03: WHEN `agent_type` está ausente, vacío o no es uno de `autor`/`implementador`/`revisor`/`lider`, THE hook SHALL denegar Bash/PowerShell (fail closed; mismo mecanismo actual de `run()`).
- REQ-04: IF `agent_may_approve` es false, THEN THE hook SHALL seguir denegando `approve`/`seal`/`allow-test-command` aunque lleven `--evidence @note:<id>` (sin cambio de comportamiento).
- REQ-05: THE default de `agent_may_approve` SHALL permanecer true cuando la clave está ausente.
- REQ-06: THE CLI `sdd.py` SHALL seguir consumiendo `@note:<id>` con TTL ≤ 30 min (`NOTE_EVIDENCE_MAX_AGE_S`) y un solo uso; no se añade validación de rol en `sdd.py` porque hoy no vive ahí (la puerta de rol es el hook).
- REQ-07: THE documentación (README, CHANGELOG, `assets/proceso-versionado.md` API-01/API-05, `assets/arnes-completo.md`, agentes si aplica) SHALL afirmar explícitamente que solo el líder puede el atajo `@note` con `agent_may_approve` true.
- REQ-08: THE versión del arnés SHALL pasar a `1.3.2` (fix / PATCH) en `sdd.py`, `pyproject.toml`, CHANGELOG y estado de `assets/proceso-versionado.md`.

## Criterios de aceptación

- AC-01: Con config true, hook deniega a `autor` e `implementador` `approve`, `seal` y `allow-test-command` con `@note:<id>` (mensaje menciona líder / solo el líder).
- AC-02: Con config true, hook permite a `lider` los mismos tres subcomandos con `@note:<id>`.
- AC-03: Con `agent_type` ausente o vacío y Bash, hook deniega (fail closed).
- AC-04: Con config false, hook deniega a `lider` aunque use `@note:<id>`.
- AC-05: Pruebas existentes de nota expirada (>1800 s) y reutilización de nota siguen fallando en `sdd.py` como hoy.
- AC-06: `unittest` de `tests/test_agent_may_approve.py` pasa en el entorno (sin depender de TTY).
- AC-07: README / CHANGELOG / API-01·API-05 / arnes-completo alineados; versión `1.3.2`.

## Fuera de alcance

- Autenticación criptográfica de la cita humana.
- Cambiar el default de `agent_may_approve` o el modo estricto (`false`).
- Validación de rol dentro de `sdd.py` (no existe hoy; no se inventa).
- Tags, releases en GitHub ni merge a main.
- Refactors ajenos a la cadena `deny_or_allow_gated` / docs / tests / bump.
