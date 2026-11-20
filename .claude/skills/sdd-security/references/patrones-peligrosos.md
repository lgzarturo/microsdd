# Patrones peligrosos (capa 1)

Severidad: **A** (alta), **M** (media), **B** (baja, higiene).

---

## Inyección de comandos (A)

- `Runtime\.getRuntime\(\)\.exec`, `subprocess\.(call|run|Popen)\([^)]*shell=True`, `os\.system\(`, `child_process\.exec\(` con cadena interpolada.

## Inyección de código / RCE (A)

- `eval\(`, `new Function\(`, `pickle\.loads?`, `yaml\.load\(` sin `SafeLoader`, `ObjectInputStream`, SpEL con `StandardEvaluationContext` y entrada externa.

## XSS (A/M)

- `dangerouslySetInnerHTML`, `innerHTML\s*=`, `\|safe` en plantillas, `v-html` con dato no confiable.

## Deserialización insegura (A)

- Java `readObject` / `ObjectInputStream`, XStream sin allowlist, Jackson `enableDefaultTyping`, PHP `unserialize\(` con entrada HTTP.

## XML / XXE (A/M)

- `DocumentBuilderFactory` / SAX sin desactivar DTD y entidades externas; `LIBXML_NOENT` en PHP.

## Criptografía y transporte (A/M)

- TLS obsoleto, `verify=False`, `http://` con secretos, `Random`/`Math\.random` para tokens de sesión.

## Cadena de suministro (M)

- Versiones `*`/`latest`, scripts `preinstall` no revisados, dependencias git sin commit fijo.

## Spring: texto plano vs `${SECRET_*}` (A/M)

- `password:` o `spring.datasource.password` en claro; patrón esperado `${SECRET_*}` / `${env:...}` (B si correcto).

## SQL concatenado o plantillas inseguras (A)

- SQL + concatenación, MyBatis `${`, `@Query` con SQL dinámico sin bind.

## CSRF desactivado (A/M)

- `csrf().disable()`, `@csrf_exempt`, cookies de sesión mal configuradas.

## Endpoints abiertos (A/M)

- `permitAll()` en mutaciones, `@Public` en POST sensibles, `security: []` en OpenAPI de escritura.

## CORS comodín (A/M)

- `Access-Control-Allow-Origin: *` con credenciales; `allowedOrigins("*")` con cookies.

## SpEL / plantillas (A)

- `@Value("#{...}")` con request, Thymeleaf `__${` con entrada sin sanitizar.

## Hash débil (A/M)

- MD5/SHA-1 para contraseñas (A); para integridad no crítica (M).

## Secretos expuestos al cliente (A)

- `NEXT_PUBLIC_` / `VITE_` / `REACT_APP_` con claves privilegiadas; material de firma en bundles.

## Uso

1. Barrer el alcance empezando por patrones **A**.
2. Volcar coincidencias en la tabla de capa 1 del informe.
3. Confirmar explotabilidad en capa 2.
