# Estimación — baseline DeepSeek (22 oct; maxTurns=6)

## Presupuesto NUEVO (reiniciado)

| Concepto | Valor |
|---|---|
| Tope HTTP repo | **100** (contador desde 0; prior=0) |
| Candado gasto | **$0.49** usage Δ (aborta ≥80% = $0.392) |
| Ambos repos | ≤ $0.99 total (este repo $0.49) |
| Modelo | `deepseek/deepseek-v4-flash` ≈ $0.091 / $0.182 /1M |
| Sonda | 1 celda × ≤6 turnos ≈ 1–6 HTTP |
| Matriz N=3 | 30 celdas × 6 turnos = **180 > 100** → `allowPartialRun`; resto pending |

Orden matriz: r0 todas las tareas×brazos, luego r1, luego r2 (balanceado si corta).

gpt-oss-20b y sonda fallida @maxTurns=3 **archivados**; no fusionar celdas.

## Flujo

1. Sonda: `01-correccion-localizada` / `base` / rep 0 (maxTurns=6).
2. Si `success` falso → **parar** y reportar (sin matriz).
3. Si éxito → cheap N=3 intercalado por rep; corta en 100 con pending.
