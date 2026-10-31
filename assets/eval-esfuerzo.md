# Mini-eval de esfuerzo: `medium` frente a `high`

> **Protocolo de líneas base:** las 5 tareas tipo viven en `bench/tareas/` (m2).
> La línea base congelada de `opus-5-5-medium` (N=5) está **pendiente** — ver `bench/baseline/README.md`.
> Mientras tanto el runner se prueba con `--provider fake` (sin modelos ni gasto).

## Objetivo

Decidir con datos si el esfuerzo por defecto del proyecto (`effort` en `.microharness/config.json`, `medium` si falta) debe subir a `high`, comparando calidad y costo de ambas configuraciones sobre las mismas tareas.

## Tareas tipo (5)

1. **Corrección localizada:** un defecto acotado a una función con prueba de regresión clara. → `bench/tareas/01-correccion-localizada`
2. **Regla nueva:** una funcionalidad de una sola regla de negocio con AC verificables. → `bench/tareas/02-regla-nueva`
3. **Refactor sin cambio de conducta:** reorganización pequeña con la suite existente como red. → `bench/tareas/03-refactor`
4. **Cambio de configuración o documentación:** ajuste sin lógica nueva que exige coherencia entre archivos. → `bench/tareas/04-config-docs`
5. **Prueba de regresión:** un defecto reintroducido que la prueba de regresión existente detecta; se corrige el código sin tocar la prueba. → `bench/tareas/05-prueba-regresion`

## Procedimiento (bench m2)

1. Specs de bench ya aprobadas y congeladas en cada `bench/tareas/*/spec/` (no se mide la redacción).
2. `python .microharness/metrics.py bench run [--cheap] --provider fake|openrouter`
   - N=5 por celda (N=3 con `--cheap`, marca `cheap: true`).
   - Solo modelos con sufijo exacto `:free`; candado vía `OPENROUTER_API_KEY` + `/api/v1/key`:
     `limit` finito ≤ `maxPaidLimitUsd` (defecto 5); uso esperado $0;
     abortar si `usage` sube durante la corrida; fail-closed en campos inválidos.
3. `bench report` emite mediana [IQR], Δ con IC bootstrap 95 %, Wilson en éxito, veredicto `ACEPTA`/`RECHAZA`/`NO CONCLUYENTE`.
4. Resultados fuera del repo; hash del `bench-report.json` se anota al congelar la línea base.

## Métricas por ejecución

- Iteraciones de revisión (rechazos del revisor hasta `APROBADO` o escalado).
- AC cumplidos / `success`.
- Tokens, llamadas, costo y tiempo.
- Tasa de caché y `firstTry`.

## Riesgos

- OpenRouter `:free`: ~20 req/min; 50 o 1000 req/día según créditos.
- **[No verificado]** Política de datos y retención de los modelos `:free`.
- Semilla Claude Code: `seed: null`.

## Criterio de lectura

- Preferir `high` solo si mejora de forma consistente AC cumplidos o defectos humanos en varias tareas tipo, con un aumento de tokens y tiempo que el equipo acepte.
- Si las diferencias son pequeñas o inconsistentes con cinco tareas, mantener `medium` y no generalizar: la muestra es mínima.
- Registrar la decisión y su evidencia con `sdd.py note`, no en este documento.
