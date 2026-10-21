# PASOS: trabajo verificable

- [x] T01 (AC-01, AC-04): prueba RED de `seal` autónomo con lease y de
  `approve spec` bloqueado sin `@note`; implementar
  `has_active_spec_lease` + `maybe_require_human_terminal` con
  `slug`/`phase` en `.microharness/sdd.py`.
- [x] T02 (AC-02, AC-03): prueba RED de `approve close` autónomo en
  verde y de revocación por deriva (`plan.md` modificado);
  implementar rama autónoma en `approve close`.
- [x] T03 (AC-05): prueba RED de `spec/<slug>/testigo.md`;
  implementar `write_witness`, sello `witness` en memoria y entrada
  en `INTEGRITY_FIELDS`.
- [x] T04 (AC-06): prueba RED de `deny_or_allow_gated` (líder sin
  `@note` en `seal`/`approve close`; resto exige nota) y de `allow`
  explícito en `__main__`; implementar en `.claude/hooks/pretool.py`.
  Incluye actualización de `test_bloquear_autoaprobacion.py` y
  `test_hook_fail_closed.py` al contrato AC-06 (aprobada por el humano).
- [x] T05 (AC-01..AC-06): reescribir `.claude/agents/lider.md` en dos
  fases; ejecutar `check --run`, suite nueva y suite completa.
