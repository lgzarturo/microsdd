# Línea base (pendiente)

> **Estado: `pending`.** No hay `bench-report.json` congelado todavía.

La línea base de `opus-5-5-medium` (N=5) se ejecutará solo con modelos OpenRouter que terminen en `:free`, tope **$0**, y `OPENROUTER_API_KEY`. El runner aborta si:

- un modelo no termina en `:free`;
- `/api/v1/key` muestra `usage > 0` o un `limit` de pago;
- la cuota `free_model_daily_requests.remaining` no alcanza para N completo.

Hasta entonces, las pruebas usan `--provider fake` (determinista, sin red).

## Riesgos documentados

- OpenRouter `:free`: ~**20 req/min**; **50** o **1000** req/día según créditos comprados.
- **[No verificado]** Política de datos y retención de los modelos `:free`.
- Semilla en Claude Code: `seed: null` (sin flag documentado).
