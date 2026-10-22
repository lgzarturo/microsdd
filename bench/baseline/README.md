# Línea base

> **Estado: `cheap-partial`.** Sonda DeepSeek OK @ maxTurns=6 → matriz N=3 intercalada; corte en 97/100 con 14 pending.

## Corrida DeepSeek (22 oct 2026) — run 39802356050

| Campo | Valor |
|---|---|
| Modelo | `deepseek/deepseek-v4-flash` |
| Precio | $0.091 / $0.182 por 1M |
| HEAD | `eb3d43e` |
| maxTurnsPerCell | **6** (`allowPartialRun`) |
| Sonda | `01-correccion-localizada` / `base` / r0 → **success** (6 req, Δ ≈ $0.0033) |
| Matriz | N=3 intercalada por rep (r0→r1→r2) |
| Celdas | **16 done** (10 ok / 6 fail) + **14 pending** |
| Balance | r0: 10/10; r1: 6/10; r2: 0/10 pending |
| Success | base 6/8 → treatment 4/8 |
| Requests | **97 / 100** (prior sonda 6 incluido) |
| Gasto usage Δ matriz | **≈ $0.075** (candado $0.49 OK; spendOk) |
| Gasto total sonda+matriz | **≈ $0.078** |
| Veredicto | `NO CONCLUYENTE` |

## Archivos

- Sonda OK: `probe-maxturns6-ok-2026-10-22/`
- Sonda fallida @3: `archive-deepseek-probe-failed-maxturns3-2026-10-22/`
- gpt-oss parcial: `archive-gpt-oss-20b-cheap-partial-2026-10-22/`
- nemotron parcial: `archive-nemotron-cheap-partial-2026-10-19/`
