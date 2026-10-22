# Bench report (NO CONCLUYENTE)

- ts: `2026-10-22T15:21:10+00:00`
- cheap: `True` | N=3 | seed=42
- claim: `efficiency`
- success: base 6/8 -> treatment 4/8
- tokens delta: 2212.5 IC95 [-12247.0, 19645.0]
- iterations delta: 0.0 IC95 [0.0, 0.0]
- costUsdTotal: 4.360013
- requests: 97/100
- baselineStatus: running-cheap

| task | base success | treat success | delta tokens | IC95 |
|---|---|---|---|---|
| 01-correccion-localizada | 1/2 | 0/2 | 10032.5 | [-2471.0, 22536.0] |
| 02-regla-nueva | 1/2 | 1/2 | -5081.0 | [-12247.0, 2085.0] |
| 03-refactor | 2/2 | 2/2 | 13140.0 | [2582.0, 23698.0] |
| 04-config-docs | 1/1 | 0/1 | -99291.0 | [-99291.0, -99291.0] |
| 05-prueba-regresion | 1/1 | 1/1 | 24070.0 | [24070.0, 24070.0] |

## Riesgos

- Proxy rate limit: 20 req/min (espera/cola, no 429); solo POST de mensajes cuentan al tope; :free tipico 50 o 1000 req/día según créditos.
- Candado: gasto máximo maxSpendUsd=0.49 por repo (usage antes/después; aborta al acercarse ratio=0.8); limit de key <= maxPaidLimitUsd=10; modelos :free o pago económico con tools.
- [No verificado] Política de datos y retención de modelos OpenRouter.
- Semilla Claude Code: seed=null (sin flag documentado).
- Presupuesto: maxTurnsPerCell=6, maxRequestsPerRun=100; proxy local cuenta cada HTTP a OpenRouter (incl. small-fast) y rechaza el 101+ (fail-closed si el contador es ilegible; tope acumulado entre intentos).
- minN desbloqueado (nb/nt >= expected) no implica veredicto favorable: efficiency o IC95 pueden seguir en NO CONCLUYENTE / RECHAZA.
