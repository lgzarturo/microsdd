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

## Plan para rellenar las 14

1. **No** relanzar cheap entero: 30 × 6 = 180 > `maxRequestsPerRun=100` → aborta a propósito.
2. Corrida de relleno solo de pendientes (`onlyCells`), en este orden:
   - 12 celdas de `04-config-docs` y `05-prueba-regresion` (nunca corridas).
   - 2 celdas `03-refactor` r2 (fallaron con cuota).
3. Arrancar con proxy (`max=100`), candado `$5`/`:free`, usage antes/después, `if: always()`.
4. **Tope acumulado entre intentos:** el contador no se reinicia. Smoke de CodeConductor gastó **4**; ese prior + smoke de este run + celdas ≤ 100.
5. Claude Code **pinneado a 2.1.197** (run 39203441982). `2.1.308+` rechaza `nvidia/nemotron-3-super-120b-a12b:free` (`unrecognized_model`).
6. Cortar si el contador del proxy o `remaining` no da para otra celda completa (`maxTurnsPerCell`). Abort mid-celda → resto `pending` + `write_report`.
7. **minN desbloqueado ≠ veredicto favorable:** cumplir `nb/nt >= expected` solo deja de forzar `NO CONCLUYENTE` por submuestreo; efficiency/IC95 pueden seguir inconclusos o rechazar.

Presupuesto esperado del relleno: **~42** + smoke (~4); peor caso controlado por proxy en **100**.
(Nota: `BENCH_PRIOR_REQUESTS=4` en el workflow es un margen conservador; los 4 del smoke CC cuentan en el tope de CodeConductor, no en el de microsdd.)

## Bloqueo 22 oct (relleno no lanzado)

Preflight vía proxy a OpenRouter (Anthropic `/v1/messages` y OpenAI `/v1/chat/completions`) para `nvidia/nemotron-3-super-120b-a12b:free` devolvió **404** del proveedor **Nvidia**:

`Function 'ac74040f-9fc9-4c5e-ac74-279ba5161d69': Not found for account '…'` (`is_byok: false`).

Runs: 39778368334, 39778590793, 39778769610, 39778989197, 39779161583.
Claude Code pin 2.1.197 OK; el fallo es backend NVIDIA, no el arnés. Sin cambio de modelo (las 16 celdas válidas usan este ID). Reintentar cuando Nvidia/OpenRouter recuperen el endpoint.
