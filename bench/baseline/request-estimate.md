# Estimación de requests por celda (run 39203441982)

Fuente: [Actions run 39203441982](https://github.com/lgzarturo/microsdd/actions/runs/39203441982)
(`cheap-partial`, veredicto `NO CONCLUYENTE`, 16 válidas / 14 pendientes).
Sin gastar requests nuevos en esta fase.

## Observado

| Señal | Valor |
|---|---|
| Celdas ejecutadas con resultado | 18 (16 ok/fail + 2 pending con `exitCode=1`) |
| Celdas ni lanzadas (corte) | 12 (04 y 05 completas) |
| `calls`/`num_turns` en reporte | `1` (subconteo; bug previo, no usable) |
| Tokens / duración | 80k–900k tokens; 40s–10 min → varias rondas HTTP reales + helper |
| Cuota `:free` típica sin créditos | 50 req/día |
| Smoke previo | 1 celda corta (`di hola`) |

## Estimación

Con ~50 RPD y ~16 celdas útiles antes del corte por `remaining < maxTurnsPerCell`:

**≈ 3 requests HTTP por celda** (modelo principal + small-fast / extras de Claude Code).

Tope por celda con `--max-turns 6`: hasta 6 turnos del modelo pedido, más llamadas helper no acotadas por ese flag → el **proxy local** es la fuente de verdad del conteo.

| Escenario (14 pendientes) | Requests estimados |
|---|---|
| Esperado (~3/celda) | ≈ 42 |
| Techo turnos (14 × 6) | 84 |
| Con buffer small-fast | ≤ 100 (tope duro del repo) |

## Plan para rellenar las 14 (sin lanzar en esta fase)

1. **No** relanzar cheap entero: 30 × 6 = 180 > `maxRequestsPerRun=100` → aborta a propósito.
2. Corrida de relleno solo de pendientes, en este orden:
   - 12 celdas de `04-config-docs` y `05-prueba-regresion` (nunca corridas).
   - 2 celdas `03-refactor` r2 (fallaron con cuota).
3. Arrancar con proxy (`max=100`), candado `$5`/`:free`, usage antes/después, `if: always()`.
4. Cortar si el contador del proxy o `remaining` no da para otra celda completa (`maxTurnsPerCell`).
5. Si tras las 14 queda margen (<100) y el veredicto sigue inconcluso, valorar repeticiones extra en otra fase — no en esta.

Presupuesto esperado del relleno: **~42** (cabe); peor caso controlado por proxy en **100**.
