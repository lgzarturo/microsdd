# Bench report (NO CONCLUYENTE)

- ts: `2026-10-19T06:03:36+00:00`
- cheap: `True` | N=3 | seed=42
- claim: `efficiency`
- success: base 7/8 -> treatment 8/8
- tokens delta: 30910.5 IC95 [-174707.5, 389934.5]
- iterations delta: 0.0 IC95 [0.0, 0.0]
- costUsdTotal: 10.776873
- baselineStatus: running-cheap

| task | base success | treat success | delta tokens | IC95 |
|---|---|---|---|---|
| 01-correccion-localizada | 2/3 | 3/3 | -125349.0 | [-306286.0, 579237.0] |
| 02-regla-nueva | 3/3 | 3/3 | 368398.0 | [61749.0, 393694.0] |
| 03-refactor | 2/2 | 2/2 | 14177.0 | [-66053.0, 94407.0] |
| 04-config-docs | 0/0 | 0/0 | 0 | [0.0, 0.0] |
| 05-prueba-regresion | 0/0 | 0/0 | 0 | [0.0, 0.0] |

## Riesgos

- OpenRouter :free: ~20 req/min; 50 o 1000 req/día según créditos.
- Candado: modelos :free; limit de key <= maxPaidLimitUsd (5); usage no debe subir durante la corrida.
- [No verificado] Política de datos y retención de modelos :free de OpenRouter.
- Semilla Claude Code: seed=null (sin flag documentado).
