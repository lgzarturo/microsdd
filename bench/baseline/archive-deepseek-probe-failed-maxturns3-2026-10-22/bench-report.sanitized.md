# Bench report (NO CONCLUYENTE)

- ts: `2026-10-22T14:54:55+00:00`
- cheap: `True` | N=3 | seed=42
- claim: `efficiency`
- success: base 0/1 -> treatment 0/0
- tokens delta: -58717.0 IC95 [0.0, 0.0]
- iterations delta: -4.0 IC95 [0.0, 0.0]
- costUsdTotal: 0.135517
- requests: 3/100
- baselineStatus: probe

| task | base success | treat success | delta tokens | IC95 |
|---|---|---|---|---|
| 01-correccion-localizada | 0/1 | 0/0 | -58717.0 | [0.0, 0.0] |

## Riesgos

- Proxy rate limit: 20 req/min (espera/cola, no 429); solo POST de mensajes cuentan al tope; :free tipico 50 o 1000 req/día según créditos.
- Candado: gasto máximo maxSpendUsd=0.49 por repo (usage antes/después; aborta al acercarse ratio=0.8); limit de key <= maxPaidLimitUsd=10; modelos :free o pago económico con tools.
- [No verificado] Política de datos y retención de modelos OpenRouter.
- Semilla Claude Code: seed=null (sin flag documentado).
- Presupuesto: maxTurnsPerCell=3, maxRequestsPerRun=100; proxy local cuenta cada HTTP a OpenRouter (incl. small-fast) y rechaza el 101+ (fail-closed si el contador es ilegible; tope acumulado entre intentos).
- minN desbloqueado (nb/nt >= expected) no implica veredicto favorable: efficiency o IC95 pueden seguir en NO CONCLUYENTE / RECHAZA.
