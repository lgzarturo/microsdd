# CÓMO: lease por fingerprint + testigo determinista

## Situación comprobada

- `sdd.py` exige terminal humana o `@note:<id>` de un solo uso en
  `approve` (spec/close), `seal` y `allow-test-command`
  (`maybe_require_human_terminal`), sin distinguir autorización inicial
  de transiciones internas del loop.
- `approve spec` ya congela `fingerprint = spec_fingerprint(...)` en
  memoria y genera `receipt`; `validate` ya detecta spec alterada
  post-aprobación. La base del lease existe.
- `approve close` ya valida `review == APROBADO`,
  `review_fingerprint == code_fingerprint` y `validate(run=True)`.
- `pretool.py` devuelve `None` en casos seguros sin emitir `allow`
  explícito, lo que provoca prompts de Bash; `deny_or_allow_gated`
  exige `@note` en las tres operaciones gated sin distinguir fases.

## Decisión y justificación

KISS: reutilizar el `fingerprint` de `approve spec` como lease.

1. `has_active_spec_lease(slug)`: `True` si estado es `proceso`,
   existe `approvals.spec.fingerprint` y coincide con
   `spec_fingerprint` actual. Cualquier byte distinto revoca.
2. `maybe_require_human_terminal(action, evidence, slug, phase)`:
   `approve spec` y `allow-test-command` siempre exigen humano/`@note`;
   `seal` y `approve close` con `--by lider` pasan con texto plano si
   hay lease activo. `approve close` conserva todas sus puertas.
3. `write_witness(path, spec, task_mem)`: genera
   `spec/<slug>/testigo.md` (sellos spec/recibo/código, tests
   sellados, perímetro aplicado) dentro de `approve close`; su hash se
   guarda en `tasks.<slug>.witness` y se protege en
   `INTEGRITY_FIELDS` con evento `aprobación_close`.
4. Hook: `deny_or_allow_gated` permite al líder `seal` y
   `approve <slug> close` sin `@note` (la seguridad real vive en
   `sdd.py`, que valida el lease); resto igual. `__main__` emite
   `permissionDecision: allow` cuando `run` no bloquea y el agente es
   lider/autor/implementador.
5. `lider.md`: reescribir puntos 3 y 6 como Fase 1 (única autorización
   de spec) + Fase 2 (loop autónomo hasta testigo y cierre).

## Invariantes y riesgos

- Invariante: el líder nunca auto-aprueba un plan; solo transiciona
  con lease íntegro. `approve spec` sin `@note` sigue bloqueado.
- Invariante: `approve close` autónomo ejecuta idénticas puertas que
  el humano; un test en rojo o un archivo fuera de alcance lo rechaza.
- Riesgo: hook permisivo sin `sdd.py` actualizado. Mitigación: la
  autorización real está en `sdd.py`; el hook solo reduce fricción.
- Sin cambios en `DEFAULT_MODEL`, `AGENT_NAMES`, instalador ni bench
  (fases 2-4 del plan v2.0 quedan fuera).
