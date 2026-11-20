# Herramientas de bloqueo y análisis (referencia humana)

**No instalar ni ejecutar desde la skill `/sdd-security`.** El programador las corre en su terminal o en CI cuando lo decida. Esta página solo alinea criterios con capa 1–3.

## Secretos en Git e historial

| Herramienta | Rol | Notas 2026 |
|-------------|-----|------------|
| **Betterleaks** | Sucesor comunitario orientado a MIT de detección de secretos | Útil cuando la política del equipo exige licencia permisiva; comparar reglas con Gitleaks antes de adoptar |
| **Gitleaks** | Escaneo de secretos maduro y ampliamente usado | Considerado **completo en funcionalidad** para pre-commit/CI estándar; mantener reglas actualizadas |
| **TruffleHog** | Búsqueda profunda con verificación | Preferir **`--only-verified`** en CI para reducir ruido; complementa, no sustituye, revisión de diff |

Recomendación práctica: pre-commit local con Gitleaks o Betterleaks según licencia; CI con TruffleHog `--only-verified` en pushes a ramas protegidas.

## Análisis estático (Semgrep)

Paquetes de reglas útiles (nombres de conjunto oficiales / comunitarios):

- `p/java`, `p/kotlin`, `p/php`, `p/django`, `p/nextjs`
- `p/owasp-top-ten` (transversal)
- `p/spring` (endpoints, SpEL, configuración)

**Límites Semgrep Pro (orientativos, 2026):** reglas Pro adicionales en Java (~181 frente ~241 en catálogo extendido) y Kotlin (~63 frente ~73). El tier gratuito/Open Source cubre OWASP básico; Pro aporta reglas Spring/JPA y hardening empresarial. Documentar en el informe si un hallazgo depende de regla Pro no disponible.

## Investigación Spring / Jackson / XStream

Consultar advisories y labs de **elttam** para:

- deserialización Jackson (`@JsonTypeInfo`, gadgets comunes)
- configuración Spring Security (CSRF, `permitAll`, CORS)
- XStream sin allowlist

La capa 2 del revisor debe contrastar diff con esos patrones cuando el stack sea JVM.

## Relación con las capas del skill

| Capa | Herramienta típica | Quién ejecuta |
|------|-------------------|---------------|
| 1 | Regex de `patrones-peligrosos.md` + Grep del agente | Líder / skill |
| 2 | Revisión humana del diff (revisor) | Subagente revisor |
| 3 | Pruebas de flujo de datos (`pytest`, `unittest`, tests de integración existentes) | Implementador en tarea MicroSDD, o humano |
| Opcional | Gitleaks/Betterleaks/TruffleHog, Semgrep | **Solo humano/CI** |

## Lo que esta skill no hace

- No añade entradas a `.github/workflows/`.
- No modifica `.claude/hooks/pretool.py`.
- No ejecuta `microsdd install` ni altera `MANIFEST`.
- No sustituye pentest ni DAST; complementa el flujo de entrega con evidencia documental.