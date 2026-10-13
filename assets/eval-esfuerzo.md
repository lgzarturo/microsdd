# Mini-eval de esfuerzo: `medium` frente a `high`

> **Protocolo no ejecutado; no hay resultados.** Este documento solo describe cómo medir; no contiene cifras ni conclusiones.

## Objetivo

Decidir con datos si el esfuerzo por defecto del proyecto (`effort` en `.microharness/config.json`, `medium` si falta) debe subir a `high`, comparando calidad y costo de ambas configuraciones sobre las mismas tareas.

## Tareas tipo (5)

1. **Corrección localizada:** un defecto acotado a una función con prueba de regresión clara.
2. **Regla nueva:** una funcionalidad de una sola regla de negocio con AC verificables.
3. **Refactor sin cambio de conducta:** reorganización pequeña con la suite existente como red.
4. **Cambio de configuración o documentación:** ajuste sin lógica nueva que exige coherencia entre archivos.
5. **Prueba de regresión:** añadir una prueba para un defecto ya corregido, sin tocar código de producción.

## Procedimiento

1. Elegir una tarea real de cada tipo y redactar su spec; el humano la aprueba una sola vez.
2. Para cada tarea, ejecutar el ciclo completo dos veces desde el **mismo commit base** y con **specs aprobadas idénticas**: una con `medium` y otra con `high` (cambiando `config.json`, `.claude/settings.json` y el frontmatter de los agentes según el README, sección 6).
3. No reutilizar contexto entre ejecuciones; registrar cada una por separado.
4. El humano revisa ambos resultados sin saber, si es posible, qué esfuerzo produjo cada uno.

## Métricas por ejecución

- Iteraciones de revisión (rechazos del revisor hasta `APROBADO` o escalado).
- AC cumplidos sobre el total de la spec.
- Tokens consumidos y tiempo de reloj.
- Defectos detectados por el humano tras el cierre.

## Criterio de lectura

- Preferir `high` solo si mejora de forma consistente AC cumplidos o defectos humanos en varias tareas tipo, con un aumento de tokens y tiempo que el equipo acepte.
- Si las diferencias son pequeñas o inconsistentes con cinco tareas, mantener `medium` y no generalizar: la muestra es mínima.
- Registrar la decisión y su evidencia con `sdd.py note`, no en este documento.
