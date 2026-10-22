# Estimación — baseline DeepSeek (22 oct 9:51 Cancún)

## Presupuesto NUEVO (reiniciado)

| Concepto | Valor |
|---|---|
| Tope HTTP repo | **100** (contador desde 0; prior=0) |
| Candado gasto | **$0.49** usage Δ (aborta ≥80% = $0.392) |
| Ambos repos | ≤ $0.99 total (este repo $0.49) |
| Modelo | `deepseek/deepseek-v4-flash` ≈ $0.091 / $0.182 /1M |
| Sonda | 1 celda × ≤3 turnos ≈ 1–5 HTTP |
| Matriz N=3 | 30 celdas × 3 turnos = 90 ≤ resto tras sonda |

gpt-oss-20b (98/100, Δ≈$0.035) **archivado**; no fusionar celdas.

## Flujo

1. Sonda: `01-correccion-localizada` / `base` / rep 0.
2. Si `success` falso → **parar** y reportar (sin matriz).
3. Si éxito → cheap N=3 balanceado por brazo en Actions.
