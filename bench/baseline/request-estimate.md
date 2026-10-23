# Estimación — fill pending DeepSeek (22 oct 19:30 Cancún)

## Presupuesto NUEVO (reiniciado)

| Concepto | Valor |
|---|---|
| Tope HTTP repo | **100** (contador desde 0; prior=0) |
| Candado gasto | **$0.10** usage Δ (aborta ≥80% = $0.08) |
| Modelo | `deepseek/deepseek-v4-flash` ≈ $0.091 / $0.182 /1M |
| Celdas a rellenar | **14** (r1: 04+05 ×2; r2: 5 tareas ×2) |
| Estimación | 14 × 6 turnos = **84 ≤ 100** |
| Previas | 16 celdas (run 39802356050) vía `priorReport` |

## Flujo

1. Actions fill-only: `onlyCells` = 14 pending + `priorReport` de las 16.
2. Fusiona → veredicto sobre 30 celdas.
3. Sin sonda (ya OK @ maxTurns=6). Sin mezclar gpt-oss/nemotron.
