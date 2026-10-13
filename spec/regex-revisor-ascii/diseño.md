# CÓMO: diseño mínimo

## Situación comprobada
- `.claude/hooks/pretool.py`, bloque `if tool in ('Bash', 'PowerShell') and agent == 'revisor'`: el comando se acepta si cumple `re.fullmatch` con la expresión del checker o con la de Git.
- La expresión Git `git (diff|status)(?: [^;&|\n]+)?` es una lista de exclusión: deja pasar `$()`, comillas invertidas, `<`, `>` y `--output=`.
- El checker usa `\d` en tres lugares; con un `str` de Python, `\d` acepta dígitos Unicode.
- Las pruebas del hook están en `tests/test_sdd.py`, clase `HookTests`. Cargan el módulo con `importlib` y llaman a `hook.run(evento)`.
- README, `.claude/agents/` y `CLAUDE.md` no mencionan comandos `git diff` ni `git status` del revisor (búsqueda sin resultados).

## Decisión y justificación
Cambio en una sola línea por expresión, sin funciones ni constantes nuevas.

1. Checker: las tres apariciones de `\d+` pasan a `[0-9]+`. No hay otro cambio.
2. Git: se pasa de una lista de exclusión a una lista de permitidos por token:

```
git (diff|status)(?: (?!--output(?:[= ]|$)|--ext-diff(?: |$))[\w./:^~=+,-]+)*
```

- Se conserva el grupo `(diff|status)` para que el cambio sea quirúrgico.
- `(?: TOKEN)*`: cero o más tokens, cada uno precedido de exactamente un espacio. Por eso se rechazan los espacios dobles, que nunca se necesitan.
- Clase `[\w./:^~=+,-]`:
  - `\w` sin `re.ASCII` cubre letras y dígitos Unicode y `_`, lo que admite `diseño.md`.
  - `.` y `/` sirven para rutas.
  - `:` sirve para `rev:path`.
  - `^` y `~` sirven para `HEAD^` y `HEAD~1`.
  - `=` sirve para `--stat=80`.
  - `+` y `,` aparecen en opciones o nombres poco comunes, pero no son peligrosos.
  - `-` va al final de la clase como literal.
  - Quedan fuera `$`, `` ` ``, `<`, `>`, `(`, `)`, `;`, `&`, `|`, `\n`, comillas, llaves, `*`, `?`, `!`, `#`, `%` y `\`.
- `@` se excluye a propósito, aunque se sugirió. En PowerShell, `@nombre` al inicio de un token es *splatting* de variables y expandiría contenido no visible para la regex. Sin llaves, su único uso Git es `@` como alias de `HEAD`, que se sustituye por `HEAD`. Excluirlo es más simple que validar su posición.
- Lookahead negativo por token: rechaza `--output` seguido de `=`, espacio o fin, y `--ext-diff` seguido de espacio o fin. Así siguen permitidas opciones legítimas como `--output-indicator-new=x`.
- Se probó en local con `python -c` que la expresión acepta los ocho casos de AC-01 y rechaza los siete de AC-02. También rechaza `git diff  --stat`, `git diff -- "a b"`, `HEAD@{1}`, `; rm x`, el salto de línea y `@x`. `3\.[0-9]+` rechaza `3.١٠`.

### Opciones evaluadas y no incluidas
- `--textconv`: `git diff` porcelana ya aplica textconv por defecto. Bloquear el flag no cambia nada (supuesto basado en la documentación de Git; no se verificó en este repositorio).
- `--no-index`: compara archivos arbitrarios, pero solo los lee. El revisor ya puede leer archivos. No se añade sin un riesgo concreto (KISS).
- `--ext-diff`: se bloquea porque el programador lo decidió. `git diff` porcelana ya puede usar `diff.external` por defecto, así que el bloqueo aporta poco; se documenta, no se discute.
- Abreviaturas (`--outp=x`): no se bloquean. Supuesto no verificado: `diff_opt_parse` de Git usa `PARSE_OPT_KEEP_UNKNOWN_OPT`, que desactiva las abreviaturas. La comprobación empírica en un repositorio temporal fue denegada por permisos.

### Alternativas descartadas
- Ampliar la lista de exclusión (`[^;&|\n$`<>…]`): mantiene el enfoque frágil y siempre deja algún carácter por cubrir.
- Tokenizar con `shlex` y validar en Python: añade lógica y dependería de reglas de comillas que difieren entre Bash y PowerShell.
- `re.ASCII`: rompería las rutas no ASCII exigidas.

## Invariantes y riesgos
- Invariante: el resto de `run()` queda sin cambios. Se mantiene `fullmatch` y el comando sigue pasando por `strip()`.
- Riesgo: algunos usos legítimos raros quedan denegados (rutas con espacios, globs, `HEAD@{n}`, `@`). Mitigación: la denegación se ve en el mensaje del hook y el revisor puede usar formas equivalentes.
- Riesgo: rutas en Unicode NFD (`n` seguida de U+0303). La marca combinante no es `\w` y la ruta se denegaría. Las rutas del repositorio están en NFC, así que se acepta.
- Riesgo: `~` al inicio de un token se expande a `$HOME` en Bash; `,` forma un arreglo en PowerShell. Ninguno ejecuta código ni escribe.
- Efecto secundario: ninguno fuera del revisor. Los demás agentes no pasan por estas expresiones.
- La guardia es *best effort*, no un sandbox.
