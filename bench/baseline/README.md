# Línea base

> **Estado: `cheap-partial` (matriz nueva).** Nemotron 16/14 archivado; no comparable.

## Cheap (N=3) — 2026-10-22 (run 39790751254)

| Campo | Valor |
|---|---|
| Modelo | `openai/gpt-oss-20b` (pago; `:free` en 429) |
| Precio | ~$0.018 / $0.09 por 1M (prompt/completion) |
| Run | https://github.com/lgzarturo/microsdd/actions/runs/39790751254 |
| Veredicto | `NO CONCLUYENTE` |
| Celdas válidas / pendientes | 25 / 5 (de 30) |
| Éxito | base 0/14 · treatment 0/11 |
| Requests | 98 / 100 |
| `usage` delta | ≈ $0.0347 (candado $5 OK) |
| Archivos | `bench-report.sanitized.*`, `usage-*.json`, `or-proxy-count.json`, `smoke.sanitized.json`, `probe.sanitized.json` |

## Candado (Arturo 22 oct)

- Gasto máximo **$5/repo** (usage antes/después; aborta al acercarse).
- Tope **100** HTTP acumulado (solo POST mensajes en head del PR; este run usó proxy previo).
- Key solo en el proxy.
