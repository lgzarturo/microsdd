# Estimación y plan — matriz nueva (22 oct)

## Presupuesto

| Concepto | Requests |
|---|---|
| Tope duro repo (proxy) | 100 |
| Rate limit proxy | 20/min espera/cola (no rechaza con 429) |
| Qué cuenta | Solo POST `/v1/messages` y `/v1/chat/completions` reenviados |
| Ya contados (prior conservador) | ~4–5 |
| Restante | ~95 |
| Matriz cheap N=3 | 30 celdas |
| `maxTurnsPerCell` | **3** → estimación 30×3 = **90** ≤ 100 |
| Gasto máximo | **$5** / repo (delta usage; aborta al ≥80%) |

Si el proxy o la cuota `:free` (cuando aplica) no dan para otra celda → resto `pending`.
Sin minN en ambos brazos → veredicto **NO CONCLUYENTE**.

## Modelo

Candidatos `:free` con `tools`/`tool_choice` (excl. familia nemotron rota), máx. 3 sondas:

1. `google/gemma-4-31b-it:free`
2. `google/gemma-4-26b-a4b-it:free`
3. `poolside/laguna-s-2.1:free`

Si todos fallan (404/cuota/agotado): fallback pago económico con tools —

- `openai/gpt-oss-20b` — ~$0.018 / $0.09 por 1M tokens (prompt/completion); tool use.
  Mismo ID preferido para alinear con CodeConductor cuando sea viable.

## No mezclar

Celdas de `archive-nemotron-cheap-partial-2026-10-19/` **fuera** del reporte
nuevo. Sin `priorReport` / sin fusionar las 16 viejas.
