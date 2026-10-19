# Línea base

> **Estado:** ver `baselineStatus` en `bench/config.json` y los reportes en este directorio.

La línea base de `opus-5-5-medium` (N=5) y el smoke cheap (N=3, `cheap: true`) se ejecutan solo con modelos OpenRouter que terminen en el sufijo exacto `:free`, con `OPENROUTER_API_KEY`.

## Candado (regla Arturo)

- Solo modelos con sufijo exacto `:free`.
- La key debe tener `limit` numérico finito y ≤ `maxPaidLimitUsd` (por defecto **5**). Si `limit` es null/ilimitado o supera el tope → aborta.
- Uso esperado **$0** (modelos gratis). Se guarda `usage` antes de la corrida y se vuelve a leer después (o por tarea); si `usage` **sube** (delta > 0) → aborta y la corrida queda inválida.
- Todo campo ausente, null donde se espera número, de tipo inesperado o no parseable → fail-closed.

El runner también aborta si la cuota `free_model_daily_requests.remaining` no alcanza para N completo.

Hasta tener resultados reales, las pruebas usan `--provider fake` (determinista, sin red).

## Riesgos documentados

- OpenRouter `:free`: ~**20 req/min**; **50** o **1000** req/día según créditos comprados.
- **[No verificado]** Política de datos y retención de los modelos `:free`.
- Semilla en Claude Code: `seed: null` (sin flag documentado).
