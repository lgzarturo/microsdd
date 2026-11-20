---
name: sdd-security
description: Auditoría de seguridad en tres capas bajo demanda; no sustituye el flujo MicroSDD ni instala herramientas.
disable-model-invocation: true
---
Solo se activa con **`/sdd-security`** (bajo demanda). No se invoca en el arranque del líder ni durante `approve`/`close` salvo petición explícita del programador. Ámbito por defecto: diff pendiente, rama actual frente a `main`/`master`, o rutas que indique el humano en `$ARGUMENTS`. No modifica código, no ejecuta `microsdd install`, no registra hooks ni CI, y no crea tareas `spec/` salvo que el humano pida un cambio correctivo aparte.

Antes de capa 1, lee `references/patrones-peligrosos.md` y `references/herramientas-bloqueo.md`. Las herramientas citadas en la referencia son orientación para el humano en su terminal; **esta skill no las instala ni las ejecuta** salvo que el programador autorice comandos concretos fuera del skill.

## Capas

### Capa 1 — Patrones (regex, lectura)

El **líder** (o quien ejecute el skill) recorre el árbol acotado con Grep/lectura y aplica los patrones **A** (alta confianza), **M** (contexto) y **B** (bajo) de `patrones-peligrosos.md`. Cada hallazgo incluye: id de patrón, archivo, línea aproximada, fragmento mínimo y si requiere confirmación manual (M/B).

### Capa 2 — Diff sin tocar código (revisor)

Cuando el líder solicita `/sdd-security`, delega al **revisor** la capa 2: revisar el diff real (sin Write/Edit), contrastar con capa 1, buscar regresiones de control (authz, validación, secretos, superficie HTTP) y marcar falsos positivos. El revisor no edita ni ejecuta suites pesadas; puede pedir al líder que corra `sdd.py check --run` si ya existe una tarea activa con pruebas.

### Capa 3 — Flujo de datos y pruebas dirigidas

Diseña o contrasta pruebas que demuestren **entrada → validación → persistencia → salida** en puntos sensibles (auth, pagos, PII, privilegios). Prioriza pruebas mínimas reproducibles con runners ya admitidos por el proyecto; si no hay base, lista casos de prueba propuestos sin implementarlos salvo tarea MicroSDD aparte.

## Formato de informe (obligatorio)

Entregar exactamente estas secciones, en español:

```text
## Resumen ejecutivo
(≤ 8 líneas: nivel de riesgo global, alcance revisado, decisión: continuar / corregir antes de merge)

## Alcance
(rama, commit/base, rutas, diff considerado)

## Capa 1 — Patrones
| Severidad | Patrón | Ubicación | Evidencia | Notas |
(Tabla: A/M/B, id patrón, ruta:línea, cita breve, FP o confirmado)

## Capa 2 — Diff (revisor)
(Hallazgos, omisiones de capa 1, controles rotos; dictamen APROBADO_SEGURIDAD | RECHAZADO_SEGURIDAD)

## Capa 3 — Flujo de datos
(Cadena por hallazgo relevante; pruebas existentes, propuestas o NO VERIFICADO)

## Acciones recomendadas
(Lista priorizada P0–P2; sin parches automáticos salvo tarea aparte)

## Herramientas sugeridas (humano, opcional)
(Solo nombres y propósito según herramientas-bloqueo.md; sin comandos de instalación)
```

## Integración con MicroSDD

- No sustituye `sdd.py check`, `approve` ni el dictamen del revisor de tarea.
- Un `RECHAZADO_SEGURIDAD` en capa 2 no bloquea el hook; el programador decide si abre tarea correctiva.
- Secretos o credenciales hallados: no pegar valores completos en el informe; rotar fuera de Claude Code.

Comandos de arnés según OS (si hace falta contexto de tarea): Unix/macOS `sh .microharness/python.sh .microharness/sdd.py …`; Windows `python .microharness\sdd.py …`.