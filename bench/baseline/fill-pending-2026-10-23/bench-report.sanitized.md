# Bench report (RECHAZA)

- ts: `2026-10-23T00:42:49+00:00`
- cheap: `True` | N=3 | seed=42
- claim: `efficiency`
- success: base 11/15 -> treatment 8/15
- tokens delta: 2085.0 IC95 [-3921.0, 5342.0]
- iterations delta: 0.0 IC95 [0.0, 0.0]
- costUsdTotal: 7.9704735
- requests: 85/100
- baselineStatus: filling-pending

| task | base success | treat success | delta tokens | IC95 |
|---|---|---|---|---|
| 01-correccion-localizada | 2/3 | 1/3 | -378.0 | [-4781.0, 22536.0] |
| 02-regla-nueva | 1/3 | 1/3 | -12247.0 | [-18761.0, 2085.0] |
| 03-refactor | 3/3 | 3/3 | 20712.0 | [1802.0, 23698.0] |
| 04-config-docs | 3/3 | 1/3 | -13984.0 | [-113990.0, 38875.0] |
| 05-prueba-regresion | 2/3 | 2/3 | 5597.0 | [3026.0, 46678.0] |

## Riesgos

- Proxy rate limit: 20 req/min (espera/cola, no 429); solo POST de mensajes cuentan al tope; :free tipico 50 o 1000 req/día según créditos.
- Candado: gasto máximo maxSpendUsd=0.1 por repo (usage antes/después; aborta al acercarse ratio=0.8); limit de key <= maxPaidLimitUsd=10; modelos :free o pago económico con tools.
- [No verificado] Política de datos y retención de modelos OpenRouter.
- Semilla Claude Code: seed=null (sin flag documentado).
- Presupuesto: maxTurnsPerCell=6, maxRequestsPerRun=100; proxy local cuenta cada HTTP a OpenRouter (incl. small-fast) y rechaza el 101+ (fail-closed si el contador es ilegible; tope acumulado entre intentos).
- minN desbloqueado (nb/nt >= expected) no implica veredicto favorable: efficiency o IC95 pueden seguir en NO CONCLUYENTE / RECHAZA.
