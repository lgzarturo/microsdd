# Bench report (NO CONCLUYENTE)

- ts: `2026-10-22T14:09:47+00:00`
- cheap: `True` | N=3 | seed=42
- claim: `efficiency`
- success: base 0/14 -> treatment 0/11
- tokens delta: -16941.5 IC95 [-25424.0, 14825.0]
- iterations delta: -2.0 IC95 [-2.0, 0.0]
- costUsdTotal: 5.583272
- requests: 98/100
- baselineStatus: running-cheap

| task | base success | treat success | delta tokens | IC95 |
|---|---|---|---|---|
| 01-correccion-localizada | 0/3 | 0/2 | 9044.5 | [-31744.0, 18106.0] |
| 02-regla-nueva | 0/3 | 0/2 | -1047.5 | [-16987.0, 15731.0] |
| 03-refactor | 0/3 | 0/2 | 8240.0 | [-13793.0, 16624.0] |
| 04-config-docs | 0/3 | 0/3 | -19121.0 | [-33002.0, 17934.0] |
| 05-prueba-regresion | 0/2 | 0/2 | -16359.5 | [-32730.0, 11.0] |

## Riesgos

- Proxy rate limit: 20 req/min (fail-closed); :free tipico 50 o 1000 req/día según créditos.
- Candado: gasto máximo maxSpendUsd=5.0 por repo (usage antes/después; aborta al acercarse ratio=0.8); limit de key <= maxPaidLimitUsd=10; modelos :free o pago económico con tools.
- [No verificado] Política de datos y retención de modelos OpenRouter.
- Semilla Claude Code: seed=null (sin flag documentado).
- Presupuesto: maxTurnsPerCell=3, maxRequestsPerRun=100; proxy local cuenta cada HTTP a OpenRouter (incl. small-fast) y rechaza el 101+ (fail-closed si el contador es ilegible; tope acumulado entre intentos).
- minN desbloqueado (nb/nt >= expected) no implica veredicto favorable: efficiency o IC95 pueden seguir en NO CONCLUYENTE / RECHAZA.
