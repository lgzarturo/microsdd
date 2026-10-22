# Línea base

> **Estado: `cheap-partial`.** Hay un smoke + cheap (N=3) sanitizado en este directorio.
> La línea base N=5 completa sigue pendiente.

## Cheap (N=3) — 2026-10-19

| Campo | Valor |
|---|---|
| Modelo | `nvidia/nemotron-3-super-120b-a12b:free` |
| Run | https://github.com/lgzarturo/microsdd/actions/runs/39203441982 |
| Veredicto | `NO CONCLUYENTE` |
| Celdas válidas / pendientes | 16 / 14 (de 30) |
| `usage` antes → después | `0.0` → `0.0` (sin gasto) |
| Archivos | `bench-report.sanitized.json`, `bench-report.sanitized.md`, `usage-before.json`, `usage-after.json` |

Tareas 04 y 05 quedaron pendientes (cuota/restantes); varias celdas de 03 con `isError`.

Estimación y plan de relleno (14 pendientes, tope 100 HTTP/repo): ver `request-estimate.md`.

## Candado (regla Arturo)

- Solo modelos con sufijo exacto `:free`.
- La key debe tener `limit` numérico finito y ≤ `maxPaidLimitUsd` (por defecto **5**). Si `limit` es null/ilimitado o supera el tope → aborta.
- Uso esperado **$0** (modelos gratis). Se guarda `usage` antes de la corrida y se vuelve a leer después (o por tarea); si `usage` **sube** (delta > 0) → aborta y la corrida queda inválida.
- Todo campo ausente, null donde se espera número, de tipo inesperado o no parseable → fail-closed.

## Riesgos documentados

- OpenRouter `:free`: ~**20 req/min**; **50** o **1000** req/día según créditos comprados.
- **[No verificado]** Política de datos y retención de los modelos `:free`.
- Semilla en Claude Code: `seed: null` (sin flag documentado).
