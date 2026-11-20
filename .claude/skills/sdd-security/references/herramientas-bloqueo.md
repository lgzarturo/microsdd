# Herramientas recomendadas (referencia; no instalar desde el skill)

El skill `/sdd-security` **no** ejecuta instalaciones (`npm`, `pip`, `brew`, binarios) ni modifica hooks/CI.

## Secretos en repositorio

| Herramienta | Notas |
|-------------|-------|
| **Gitleaks** | Referencia feature-complete en 2026 para escaneo en git y working tree. |
| **Betterleaks** | Sucesor MIT; alternativa cuando se prioriza licencia abierta. |
| **TruffleHog** | En CI del equipo: `trufflehog --only-verified` para reducir ruido. |

## Semgrep (SAST)

Packs útiles: `p/java`, `p/kotlin`, `p/php`, `p/django`, `p/nextjs`, `p/owasp-top-ten`, `p/spring`.

Límites Pro orientativos (2026): Java ~181/241 reglas; Kotlin ~63/73.

## elttam (comunidad)

Packs comunitarios para **Spring**, **Jackson** y **XStream**; complementan `p/spring` y la capa 1.

## MicroSDD

| Permitido | Prohibido |
|-----------|-----------|
| Citar comando ejemplo en el informe | Instalar o añadir jobs CI desde el skill |
| Sugerir `semgrep --config p/spring` al humano | Descargar reglas en la sesión |

Orden sugerido (humano, fuera de Claude Code): secretos → Semgrep → elttam → TruffleHog verificado en CI si existe.
