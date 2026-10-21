# QUÉ: loop autónomo del líder con lease y testigo

## Objetivo

Permitir que, tras UNA única autorización humana de la especificación,
el líder ejecute el loop `implementador → sdd.py check --run → autor`
sin pedir más aprobaciones intermedias: `seal` y `approve close`
autónomos mientras el fingerprint de la spec no cambie, y generación
determinista de `spec/<slug>/testigo.md` al cerrar.

## Precondiciones

- Repo en `main` limpio; suite base 384 tests OK (skipped=4).
- Sin tareas en estado `proceso`.
- `agent_may_approve` en `true` (default).

## Requisitos EARS

- REQ-01: WHEN la spec fue aprobada por el humano (`approve <slug> spec`
  con `@note:<id>`) y la tarea está en `proceso`, THE `sdd.py` SHALL
  permitir `seal` y `approve <slug> close` con `--by lider` y evidencia
  de texto plano, sin exigir terminal humana ni `@note`.
- REQ-02: WHEN cualquier byte de `spec.json`, `requerimientos.md`,
  `plan.md` o `tareas.md` cambie tras `approve spec`, THE `sdd.py` SHALL
  invalidar el lease y volver a exigir autorización humana.
- REQ-03: WHEN el líder ejecuta `approve <slug> close` autónomo,
  THE `sdd.py` SHALL ejecutar las mismas puertas que el cierre humano
  (`review == APROBADO`, `review_fingerprint == code_fingerprint`,
  `validate(run=True)` en verde) y rechazar el cierre si alguna falla.
- REQ-04: WHEN `approve <slug> close` tiene éxito, THE `sdd.py` SHALL
  generar `spec/<slug>/testigo.md` con los sellos SHA-256 (spec, tests,
  código) y sellar su hash en memoria.
- REQ-05: WHEN el líder ejecuta `approve <slug> spec` o
  `allow-test-command`, THE `sdd.py` y el hook SHALL seguir exigiendo
  `@note:<id>` de fase correspondiente; el hook permite `seal` y
  `approve <slug> close` del líder sin `@note` y emite `allow` explícito
  en decisiones no bloqueadas.

## Criterios de aceptación

- AC-01: `seal` autónomo: tras `approve spec` con `@note`, `seal <slug>
  --by lider --evidence '<texto>'` sella sin TTY ni `@note`.
- AC-02: `approve close` autónomo: con `check --run` verde y revisión
  `APROBADO`, `approve <slug> close --by lider --evidence '<texto>'`
  cierra sin TTY ni `@note`.
- AC-03: deriva revoca: si `plan.md` (o `spec.json`) cambia tras
  `approve spec`, `seal` y `approve close` con texto plano fallan.
- AC-04: sin regresión: `approve <slug> spec` y `allow-test-command`
  con texto plano siguen exigiendo terminal humana (`ValueError`).
- AC-05: testigo: `approve close` genera `spec/<slug>/testigo.md` con
  fingerprint de spec, digest del recibo, `code_fingerprint` final,
  tests sellados y perímetro aplicado; su hash queda en memoria y
  protegido por integridad.
- AC-06: hook: `pretool.run` devuelve `None` para `seal` y
  `approve <slug> close` del líder sin `@note`; exige `@note` para
  `approve <slug> spec` y `allow-test-command` de no-líder o sin nota;
  el `__main__` emite `permissionDecision: allow` cuando no hay bloqueo
  y el agente es lider/autor/implementador.

## Fuera de alcance

- Eliminar `revisor.md` o reducir a 3 agentes.
- Cambiar `DEFAULT_MODEL` o `installer.py`; modo `agnostic`.
- Mover `bench.py`/`metrics.py`/`pricing.json` fuera de `.microharness/`.
- `AGENTS.md` raíz o flags `--target` del instalador.
