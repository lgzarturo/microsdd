# CÓMO: normalizar `X:\...` antes del rechazo de backslash

## Situación comprobada

- `split_segments` (pretool.py:397) y `tokens` (pretool.py:439)
  rechazan con `[$`\\\n\r…]` cualquier comando con `\`.
- En Windows, `REPO / SDD` es `D:\a\...\sdd.py` → `check_shell`
  devuelve `msg_unparseable()` → DENY. En Linux la ruta usa `/`
  → parsea → `deny_or_allow_gated` permite seal del líder.
- Contrato de tests: absoluta-Windows = reconocida (allow líder);
  relativa-con-backslash = evasiva (deny); no-líderes = deny
  (vía `deny_or_allow_gated`, líneas 333-348).
- Solo 2 expectativas con backslash en tests (líneas 62 y 150 de
  `test_bloquear_autoaprobacion.py`), ambas relativas → intactas.

## Decisión y justificación

Helper `_slashes_for_win_abs(cmd)`: reescribe `\` → `/` solo dentro
de tokens de ruta absoluta Windows (`(?<![A-Za-z0-9_])[A-Za-z]:\\…`
hasta delimitador shell). Aplicado al inicio de `split_segments`
y `tokens`, antes del regex de rechazo:

1. `python3 D:\a\...\sdd.py seal ...` → `python3 D:/a/.../sdd.py
   seal ...` → shlex limpio → forma reconocida → allow líder,
   deny no-líder (sin cambiar `deny_or_allow_gated`).
2. `python3 .microharness\sdd.py ...` → sin letra-unidad → intacto
   → sigue rechazado → deny.
3. `foo:D:\x` (letra precedida de palabra) → no toca → deny
   conservador; `F=D:\x` y `"D:\x"` sí normalizan (delimitador).
4. No tocar shlex ni el regex de rechazo: el cambio es solo la
   pre-normalización (KISS, fail-closed intacto).

Hipótesis descartada: relajar el test a `as_posix` ocultaría el bug
real (agentes Windows emiten `D:\...`); el hook debe reconocerlo.

## Invariantes y riesgos

- Invariante: todo comando sin letra-unidad se comporta igual que
  antes; solo cambian comandos con token `[A-Za-z]:\`.
- Riesgo: shlex posix altera `\` aunque pasara el regex (por eso se
  normaliza ANTES, no se elimina del regex).
- Estrategia `tdd`: regresión en rojo → fix → verde → suite.
