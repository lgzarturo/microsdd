# Línea base

> **Estado: `complete`.** DeepSeek cheap N=3 completo (30/30). Veredicto: **RECHAZA**.

## Fill + fusión (Arturo 22 oct 19:30 Cancún) — run 39878723841

| Campo | Valor |
|---|---|
| Modelo | `deepseek/deepseek-v4-flash` |
| HEAD fill | `ef3955f` |
| maxTurnsPerCell | 6 |
| Celdas | **30/30** (0 pending) |
| Success | base **11/15** → treatment **8/15** |
| Tokens Δ | **2085.0** IC95 **[-3921.0, 5342.0]** |
| Iterations Δ | **0.0** IC95 **[0.0, 0.0]** |
| Requests fill | **85 / 100** (presupuesto nuevo; prior=0) |
| Gasto usage Δ fill | **≈ $0.080** ≤ $0.10 (spendOk; approach $0.08) |
| Previas | 16 celdas run 39802356050 (candado $0.49; Δ ≈ $0.078) |
| Veredicto | **RECHAZA** (claim efficiency) |

## Archivos

- Resultado final: `bench-report.sanitized.*`, `fill-pending-2026-10-23/`
- Parcial 16/30: `archive-deepseek-cheap-partial-2026-10-22/`
- Sonda OK @6: `probe-maxturns6-ok-2026-10-22/`
- Sonda fallida @3: `archive-deepseek-probe-failed-maxturns3-2026-10-22/`
- gpt-oss / nemotron: archives (no mezclar)
