# Patrones peligrosos (capa 1)

Convención: **A** = alta confianza (investigar de inmediato); **M** = requiere contexto; **B** = señal débil o estilo legacy. Ajusta el lenguaje del patrón al stack del repositorio (Java/Kotlin/Spring, PHP, Python/Django, JS/TS/Next.js, etc.).

## A — Inyección de comandos y procesos

| Id | Patrón (regex orientativa) | Notas |
|----|---------------------------|--------|
| A-CMD-01 | `(?i)(Runtime\.getRuntime\(\)\|ProcessBuilder\|os\.system\|subprocess\.(call\|run\|Popen))\s*\([^)]*\+` | Concatenación en shell/comando |
| A-CMD-02 | `(?i)shell\s*=\s*True` | `subprocess` con shell en Python |
| A-CMD-03 | `(?i)(exec\|execSync)\s*\(\s*[`'"][^`'"]*\+` | Node: comando construido |
| A-CMD-04 | `(?i)child_process` con template literal + variable sin lista blanca | Node |

## A — Inyección de código y plantillas

| Id | Patrón | Notas |
|----|--------|--------|
| A-CDE-01 | `(?i)eval\s*\(` | JS/Python/PHP |
| A-CDE-02 | `(?i)new\s+Function\s*\(` | JS |
| A-CDE-03 | `(?i)\bexec\s*\(` | Python legado |
| A-CDE-04 | `(?i)dangerouslySetInnerHTML` sin sanitizador visible | React |
| A-CDE-05 | `(?i)\$\{[^}]+\}` en SQL/Query sin prepared statement | Ver también SQL |

## A — XSS y salida HTML

| Id | Patrón | Notas |
|----|--------|--------|
| A-XSS-01 | `(?i)innerHTML\s*=` | DOM |
| A-XSS-02 | `(?i)document\.write\s*\(` | |
| A-XSS-03 | `(?i)\|safe` ausente en plantillas Django/Jinja con `{{` usuario | Confirmar escape |
| A-XSS-04 | `(?i)response\.write\([^)]*\$_(GET\|POST\|REQUEST)` | PHP reflejado |

## A — Deserialización insegura

| Id | Patrón | Notas |
|----|--------|--------|
| A-DSR-01 | `(?i)ObjectInputStream\|readObject\s*\(` | Java |
| A-DSR-02 | `(?i)pickle\.loads?\s*\(` | Python |
| A-DSR-03 | `(?i)yaml\.load\s*\([^)]*\)` sin `Loader=SafeLoader` | |
| A-DSR-04 | `(?i)JsonTypeInfo\.As\.(WRAPPER_ARRAY\|CLASS)` sin lista blanca | Jackson polimórfico |
| A-DSR-05 | `(?i)XStream` sin allowlist explícita | Ver elttam |

## A — XML (XXE / expansión)

| Id | Patrón | Notas |
|----|--------|--------|
| A-XML-01 | `(?i)DocumentBuilderFactory` sin `FEATURE_SECURE_PROCESSING` / sin desactivar DTD externo | Java |
| A-XML-02 | `(?i)lxml\.etree\.parse` sin `resolve_entities=False` | Python |
| A-XML-03 | `(?i)XmlReaderSettings` sin `DtdProcessing\.Prohibit` | .NET |

## A — Criptografía débil

| Id | Patrón | Notas |
|----|--------|--------|
| A-CRY-01 | `(?i)\b(MD5\|SHA1)\b` en contexto de contraseña o integridad | |
| A-CRY-02 | `(?i)DES\|RC4\|ECBMode` | |
| A-CRY-03 | `(?i)random\.random\(\)` para tokens/IDs de sesión | Usar `secrets` / CSPRNG |
| A-CRY-04 | `(?i)javax\.crypto\.spec\.DESKeySpec` | |

## A — Cadena de suministro y secretos en repo

| Id | Patrón | Notas |
|----|--------|--------|
| A-SUP-01 | `(?i)(AKIA[0-9A-Z]{16}\|BEGIN (RSA\|OPENSSH\|EC) PRIVATE KEY)` | Credencial material |
| A-SUP-02 | `(?i)password\s*=\s*['"][^'"]{3,}['"]` | Texto plano en fuente |
| A-SUP-03 | `(?i)api[_-]?key\s*=\s*['"][^'"]+['"]` | |
| A-SUP-04 | `-----BEGIN CERTIFICATE-----` junto a clave privada en mismo archivo | |

## M — Spring: plaintext vs placeholders

| Id | Patrón | Notas |
|----|--------|--------|
| M-SPR-01 | `(?i)(spring\.datasource\.(password\|username)\s*=\s*)(?!(\$\{SECRET_))\S` | Valor literal en `application.properties/yml` |
| M-SPR-02 | `(?i)\$\{(?!SECRET_)[a-zA-Z0-9_.-]+\}` en campos sensibles | Placeholder sin prefijo acordado `SECRET_*` |
| M-SPR-03 | `(?i)@Value\s*\(\s*"\$\{[^}]+\}"\s*\).*(password\|secret\|token)` | Confirmar origen externo |

## A/M — SQL concatenado y plantillas

| Id | Patrón | Notas |
|----|--------|--------|
| A-SQL-01 | `(?i)(SELECT\|INSERT\|UPDATE\|DELETE).*(['"]\s*\+\s*\|`.*\$\{)` | Concatenación |
| A-SQL-02 | `(?i)f['"][^'"]*(SELECT\|INSERT).*\{` | f-string SQL Python |
| A-SQL-03 | `(?i)execute\s*\(\s*["'].*%s.*%` | Formato inseguro |
| M-SQL-04 | `(?i)@\w+Query\s*\(\s*".*\+\s*` | JPQL dinámico |

## M — CSRF desactivado

| Id | Patrón | Notas |
|----|--------|--------|
| M-CSRF-01 | `(?i)csrf\.disable\s*\(\)` | Spring Security |
| M-CSRF-02 | `(?i)CSRF_COOKIE_SECURE\s*=\s*False` | Django settings |
| M-CSRF-03 | `@csrf_exempt` en vistas que mutan estado | Django |

## M — Endpoints abiertos y CORS

| Id | Patrón | Notas |
|----|--------|--------|
| M-EP-01 | `(?i)permitAll\s*\(\)` en rutas `POST`/`PUT`/`DELETE` | Spring |
| M-EP-02 | `(?i)@RestController` sin anotaciones de seguridad en método sensible | Revisar capa 2 |
| M-CORS-01 | `(?i)allowedOrigins\s*\(\s*["']\*["']\s*\)` | Wildcard con credenciales |
| M-CORS-02 | `(?i)Access-Control-Allow-Origin:\s*\*` con `Allow-Credentials:\s*true` | |

## A/M — SpEL y expresiones Spring

| Id | Patrón | Notas |
|----|--------|--------|
| A-SPEL-01 | `(?i)@PreAuthorize\s*\(\s*".*\+.*"\s*\)` | SpEL dinámico |
| M-SPEL-02 | `(?i)SpelExpressionParser.*getValue\s*\(.*user` | Entrada influenciada |

## B — Hash débil (no credencial)

| Id | Patrón | Notas |
|----|--------|--------|
| B-HASH-01 | `(?i)hashlib\.(md5\|sha1)\(` | Cache/ETag: confirmar |
| B-HASH-02 | `(?i)MessageDigest\.getInstance\s*\(\s*"(MD5\|SHA-1)"\s*\)` | |

## A/M — Secretos en cliente

| Id | Patrón | Notas |
|----|--------|--------|
| A-CLI-01 | `(?i)(NEXT_PUBLIC_\|VITE_\|REACT_APP_).*(SECRET\|API_KEY\|PRIVATE)` | Expuesto al navegador |
| M-CLI-02 | `(?i)client_secret` en bundle JS/TS bajo `public/` o `static/` | OAuth mal ubicado |

## Uso en capa 1

1. Compila una lista de ids a buscar según el stack detectado en `docs/arquitectura.md` o en extensiones del diff.
2. Para cada coincidencia, captura ≤ 120 caracteres de contexto.
3. No reportes valores secretos completos: sustituye por `***`.
4. En **M**, el informe debe decir qué evidencia falta para elevar a **A** o descartar.