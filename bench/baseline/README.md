# Línea base

> **Estado: en curso (matriz nueva).** El cheap-partial de nemotron (16/14) está
> archivado en `archive-nemotron-cheap-partial-2026-10-19/` y **no es comparable**.

## Matriz nueva (22 oct 2026)

| Campo | Valor |
|---|---|
| Modelo | sonda `:free` ≤3; si fallan → pago económico con tools (ver reporte) |
| Diseño | cheap N=3, 5 tareas × 2 brazos = 30 celdas; sin mezclar celdas viejas |
| Tope HTTP | 100 acumulado/repo (proxy); rate limit 20/min fail-closed |
| Turnos | `maxTurnsPerCell=3` → 30×3=90 ≤ 100 |
| Candado | gasto máximo **$5/repo** (usage antes/después; aborta al acercarse); key limit ≤ $10 |

Ver `request-estimate.md`.

## Candado (regla Arturo 22 oct 8:37)

- Modelos `:free` preferidos; si fallan, pago económico con tool use.
- Gasto máximo **$5 por repo**: `usage` antes y después; aborta si el delta se acerca al tope.
- `limit` de la key finito y ≤ `maxPaidLimitUsd` (créditos en cuenta, p. ej. $10).
- Key solo en el proxy; nunca impresa. Fail-closed ante campos ausentes/tipos raros.
