# PASOS

- [x] T01 (AC-01, AC-02, AC-04): En `pretool.py`, propagar `agent` hasta `deny_or_allow_gated`; permitir `@note` solo si `agent == 'lider'` y `agent_may_approve`; mensaje claro si el rol no es líder.
- [x] T02 (AC-01, AC-02, AC-03, AC-04, AC-05, AC-06): Ampliar `tests/test_agent_may_approve.py` (autor/implementador bloqueados en approve/seal/allow-test-command; líder ok; rol ausente denegado; config false; TTL/reuse intactos).
- [x] T03 (AC-07): Bump `1.3.2` en `sdd.py` y `pyproject.toml`; CHANGELOG; README; `assets/proceso-versionado.md`; `assets/arnes-completo.md`.
- [x] T04 (AC-06): Ejecutar `unittest tests.test_agent_may_approve` y corregir regresiones mínimas.
