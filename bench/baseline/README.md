# Línea base

> **Estado: `filling-pending`.** Relleno de 14 celdas pending (r1 resto + r2) con presupuesto nuevo 100 req / $0.10.

## Fill pendiente (Arturo 22 oct 19:30 Cancún)

| Campo | Valor |
|---|---|
| Modelo | `deepseek/deepseek-v4-flash` |
| maxTurnsPerCell | 6 |
| Celdas a rellenar | **14** (vía `onlyCells` + `priorReport`) |
| Previas | 16 done (run 39802356050) |
| Presupuesto HTTP | **100** (reiniciado; prior=0) |
| Candado gasto | **$0.10** usage Δ (fail-closed; aborta ≥ $0.08) |
| Estimación | 14 × 6 = 84 ≤ 100 |

Veredicto final sobre las **30** celdas tras el fill.

## Archivos

- Parcial maxTurns=6: `bench-report.sanitized.*` (16 done + 14 pending) hasta que el fill lo reemplace
- Sonda OK: `probe-maxturns6-ok-2026-10-22/`
- Sonda fallida @3: `archive-deepseek-probe-failed-maxturns3-2026-10-22/`
- gpt-oss / nemotron: archives (no mezclar)
