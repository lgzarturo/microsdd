---
name: sdd-security
description: Auditoría defensiva on-demand en tres capas (patrones, diff, pruebas); solo bajo solicitud explícita /sdd-security.
disable-model-invocation: true
---
Ejecuta una revisión defensiva del alcance indicado en: $ARGUMENTS

**Disparador:** solo invocación explícita `/sdd-security` por el programador o el líder. No se ejecuta en cierre habitual, ni en hooks, ni en `sdd.py check`, ni en CI.

**Límites (obligatorios):** no instales herramientas, no modifiques hooks, no alteres `.claude/settings.json`, no añadas pasos al instalador ni propongas jobs de CI. Este skill documenta y orienta; la ejecución de escáneres externos queda en manos del humano fuera de Claude Code (véase `references/herramientas-bloqueo.md`).

**Alcance por defecto:** diff de la tarea activa (`spec/<slug>/` y archivos en `spec.json`), o rutas que indique `$ARGUMENTS`. No escanees hosts ni terceros.

## Referencias (léelas antes de capa 1)

1. `references/patrones-peligrosos.md` — regex, severidad A/M/B y mitigación.
2. `references/herramientas-bloqueo.md` — herramientas recomendadas **sin** instalar desde el skill.

## Tres capas

### Capa 1 — Patrones (rápida, determinista)

- Aplica los patrones y criterios de `patrones-peligrosos.md` con Grep (o lectura puntual) sobre el alcance.
- Registra cada hallazgo con: archivo, línea aproximada, patrón/categoría, severidad (A/M/B), cita breve.
- No sustituyas la capa 2: los falsos positivos se resuelven allí.

### Capa 2 — Revisión del diff (manos fuera del código)

- Rol **revisor** o agente con la misma restricción: **no edites** código, tests ni configuración.
- Contrasta el diff real con la spec (EARS, AC, precondiciones de seguridad).
- Prioriza severidad **A** y **M** del inventario; eleva a A si el diff introduce superficie nueva (auth, red, deserialización, secretos).
- Sugiere reglas o consultas para linters estáticos (Semgrep, elttam, etc.) citando paquete/regla cuando aplique; **no** ejecutes instalaciones.
- Marca «sin evidencia en diff» cuando el riesgo es latente pero no tocado por el cambio.

### Capa 3 — Cobertura de pruebas y flujo de datos

- Trazar flujos entrada → validación → persistencia/salida para datos sensibles del alcance.
- Proponer casos de prueba concretos (negativos y positivos) que falten, sin escribir tests salvo que otra tarea lo autorice.
- Enlazar cada propuesta con categoría (XSS, inyección, CSRF, secretos expuestos, etc.) y severidad si no se cubre.

## Formato fijo del informe

Entrega **un solo** informe en este orden (secciones vacías con «Ninguno» si aplica):

```markdown
# Informe /sdd-security

## Alcance
- Slug / rama / commit (si aplica):
- Archivos revisados:

## Capa 1 — Patrones
| Severidad | Categoría | Archivo | Evidencia |
|-----------|-----------|---------|-----------|
| A/M/B     | …         | …       | …         |

## Capa 2 — Diff (sin edición)
### Hallazgos A
### Hallazgos M
### Hallazgos B
### Sugerencias linter (solo referencia; no instalar desde el skill)

## Capa 3 — Pruebas y flujo de datos
| Flujo | Riesgo | Prueba sugerida | Severidad si falta |
|-------|--------|-----------------|-------------------|

## Resumen ejecutivo
- Conteo A / M / B:
- Bloqueantes para merge (solo A en diff activo):
- Siguiente paso recomendado (humano):
```

## Coordinación MicroSDD

- El **líder** invoca este skill y adjunta el informe al cierre o a la revisión si hay hallazgos A en el diff.
- El **revisor** aplica capa 2 cuando el líder lo solicite explícitamente en la delegación (véase `.claude/agents/revisor.md`).
- Dictamen de spec (`APROBADO`/`RECHAZADO`) no se sustituye por este informe; un A en el diff activo debe reflejarse en `RECHAZADO` o corrección previa.
