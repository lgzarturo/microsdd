# CÓMO: diseño mínimo

## Situación comprobada
- `.claude/hooks/pretool.py`, bloque `if tool in ('Bash', 'PowerShell') and agent == 'revisor'` (línea ~69): el comando pasa si cumple `re.fullmatch` con la expresión del checker o con la expresión Git:
  `git (diff|status)(?: (?!--output(?:[= ]|$)|--ext-diff(?: |$))[\w./:^~=+,-]+)*`
- Pruebas del hook: `tests/test_sdd.py`, clase `HookTests`, cargan el módulo con `importlib` y llaman a `hook.run(evento)`. `test_reviewer_git_allowlist` ya recorre `('Bash', 'PowerShell')`.
- Evaluación de `pretool.run` (autor), todas hoy PERMITIDAS: `--textconv`, `--textconv=x`, `-O/tmp/o`, `-O /tmp/o`, `-O`, `-Ofoo`, `-pO/tmp/o`, `-wO/tmp/o`, `-U0 -O/tmp/o`, `--open-files-in-pager`, `--open-files-in-pager=less`, `--no-index <a> <b>`, `--rotate-to=x`, `--skip-to=x`.
- Ya DENEGADAS: `git -c diff.external=x diff`, `git --config-env=a=b diff` (el token inicial está fijado a `git diff|status`).
- Comportamiento real de git 2.55.0 (repositorio temporal en el scratchpad):
  - `-O<archivo>` lee y aplica el orderfile; también agrupado (`-pO<f>`, `-wO<f>`). `-O <f>` toma `" <f>"` como ruta y falla. `-O` sin valor: error.
  - `--textconv` ejecuta el filtro configurado; **también lo ejecuta `git diff` sin opciones** (textconv activo por defecto en porcelana); `--no-textconv` lo desactiva. `--textconv=x`: error "no toma valores".
  - `--open-files-in-pager` y `--orderfile=`: "opción inválida" en `git diff` (son de `git grep`/no existen). Bloquearlo es solo defensa en profundidad.
  - Abreviaturas (`--textc`, `--outp=`): "opción inválida". Confirma en 2.55.0 el supuesto de `regex-revisor-ascii`.
  - `--no-index <a> <b>`: lee archivos fuera del repositorio (solo lectura).
- `git status -h` no muestra opciones que lean archivos arbitrarios ni ejecuten comandos (supuesto: limitado a esa salida de ayuda).

## Decisión y justificación
Cambio en una sola línea: ampliar el lookahead negativo por token de la expresión Git. Sin helpers, constantes ni cambios en el checker.

```
git (diff|status)(?: (?!--output(?:[= ]|$)|--ext-diff(?: |$)|--textconv(?:[= ]|$)|--open-files-in-pager(?:[= ]|$)|-[^ -]*O)[\w./:^~=+,-]+)*
```

- `--textconv(?:[= ]|$)`: deniega `--textconv` y `--textconv=…`; deja pasar `--no-textconv` (empieza por `--no-`).
- `--open-files-in-pager(?:[= ]|$)`: mismo patrón que `--output`.
- `-[^ -]*O`: token que empieza por un solo `-` (el segundo carácter no es `-`) y contiene `O` antes de un espacio. Cubre `-O`, `-O<f>`, `-pO<f>`, `-wO<f>`. No afecta a `--…`, a `--` ni a tokens que no empiezan por `-` (`Old.txt`).
- Se probó la expresión fuera del hook con `re.fullmatch`: acepta los casos de AC-02 y `git diff -- spec/x/diseño.md`; rechaza los de AC-01 y los casos peligrosos ya existentes (`$(…)`, `>`, `--output`, `--ext-diff`).

### Alternativas descartadas
- Helper Python que tokenice y valide opciones: más código para el mismo resultado (KISS).
- Bloquear solo `-O` exacto o `-O\S*`: deja pasar la forma agrupada `-pO<f>`, comprobada como efectiva.
- Allowlist de opciones por nombre: rompería usos legítimos no previstos; cambio mayor que el pedido (YAGNI).

## Invariantes y riesgos
- Invariante: expresión del checker, resto de `run()`, `strip()` y `fullmatch` sin cambios.
- Limitación (hecho): bloquear `--textconv` aporta poco, porque `git diff` ejecuta textconv por defecto si existe `diff.<driver>.textconv` + `.gitattributes`. El riesgo real depende de la configuración del repositorio, que el revisor no puede escribir (no edita archivos). Mitigación real fuera de alcance: exigir `--no-textconv`/`--no-ext-diff` o no permitir `git diff` sin opciones; requiere decisión del líder/humano.
- Falso positivo aceptado: tokens de opción corta con `O` en un valor, p. ej. `-SOops` o `-GOO`, y `-O…` después de `--` como ruta, quedan denegados. El revisor puede usar otra forma.
- `--no-index` sigue permitido: lectura de archivos fuera del repositorio. El revisor ya puede leer archivos con sus herramientas de lectura; no se bloquea sin decisión explícita.
- Otras opciones de lectura de valores (`--rotate-to=`, `--skip-to=`) solo filtran rutas; no leen archivos ni ejecutan comandos (comprobado `--rotate-to=g`).
- Efecto secundario: ninguno fuera del revisor.
- La guardia es *best effort*, no un sandbox.
