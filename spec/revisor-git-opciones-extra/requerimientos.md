# QUÉ: requisitos

## Objetivo
Ampliar la allowlist Git del revisor en `.claude/hooks/pretool.py` (aplicada igual a `Bash` y `PowerShell`) para denegar también `--textconv`, `-O` (con valor pegado, separado, sin valor o agrupado con otras opciones cortas, p. ej. `-pO<archivo>`) y `--open-files-in-pager`. Los usos legítimos de solo lectura y el checker con sus lanzadores deben seguir permitidos.

## Precondiciones
- PRE-01: decisión humana previa: el implementador modifica `.claude/hooks/pretool.py` mediante Bash, porque la guardia le niega editar `.claude/` con `Edit`/`Write`. Solo puede cambiar la expresión Git del bloque del revisor.
- Hecho comprobado (líder y autor, evaluando `pretool.run` con `agent_type` revisor): hoy se permiten `git diff --textconv`, `git diff -O/tmp/o`, `git diff -O /tmp/o`, `git diff -pO/tmp/o`, `git diff -wO/tmp/o`, `git diff --open-files-in-pager` y `git diff --open-files-in-pager=less`.
- Hecho comprobado (git 2.55.0, repositorio temporal): `-O<archivo>` lee un orderfile arbitrario, también si va agrupado (`-pO<archivo>`, `-wO<archivo>`); `-O <archivo>` se interpreta como ruta con espacio inicial y falla; `--textconv` ejecuta el filtro `diff.<driver>.textconv` configurado.
- Hecho comprobado: `git -c …` y `git --config-env=…` ya se deniegan, porque la expresión exige que el comando empiece por `git diff` o `git status`.

## Requisitos EARS
- REQ-01: IF un comando `git diff` o `git status` del revisor contiene un token `--textconv` o `--textconv=…`, THEN THE hook SHALL denegarlo.
- REQ-02: IF un comando Git del revisor contiene un token que empieza por un solo `-` y que incluye `O` (opción corta `-O` sola, con valor pegado o agrupada), THEN THE hook SHALL denegarlo.
- REQ-03: IF un comando Git del revisor contiene un token `--open-files-in-pager` o `--open-files-in-pager=…`, THEN THE hook SHALL denegarlo.
- REQ-04: WHEN el revisor ejecuta con `Bash` o `PowerShell` un comando Git legítimo de solo lectura de los listados en AC-02, THE hook SHALL permitirlo (devolver `None`).
- REQ-05: THE hook SHALL mantener sin cambios la expresión del checker, el resto de `run()` y el comportamiento de los casos cubiertos por las pruebas existentes.

## Criterios de aceptación
- AC-01: En `Bash` y `PowerShell` (un `subTest` por herramienta y comando) se deniegan: `git diff --textconv`, `git diff --stat --textconv`, `git diff -O/tmp/o`, `git diff -O /tmp/o`, `git diff -O`, `git diff -pO/tmp/o`, `git diff -wO/tmp/o`, `git diff -U0 -O/tmp/o`, `git diff --open-files-in-pager` y `git diff --open-files-in-pager=less`.
- AC-02: En `Bash` y `PowerShell` (un `subTest` por herramienta y comando) se permiten: `git diff`, `git diff --stat HEAD~1 -- src/app.py`, `git diff --name-only HEAD`, `git status --short`, `git diff --no-textconv`, `git diff -U0 -- README.md` y `git diff -- Old.txt`.
- AC-03: Las pruebas existentes `test_reviewer_edits_blocked`, `test_reviewer_checker_prefixes`, `test_reviewer_powershell_uses_allowlist`, `test_reviewer_git_allowlist` y `test_reviewer_checker_ascii_digits` pasan sin modificarse (checker con sus lanzadores incluido), y la suite completa (`python -m unittest discover -s tests -v`) pasa.
- AC-04: El diff de `.claude/hooks/pretool.py` cambia solo la expresión Git del bloque del revisor; ningún archivo fuera de `allowed_paths` cambia.

## Fuera de alcance
- `--no-index`: hecho comprobado que permite comparar (leer) archivos fuera del repositorio; no se bloquea en esta tarea salvo decisión explícita del líder/humano (ver `plan.md`).
- `--ext-diff`, `--output` y la expresión del checker: ya cubiertos por `regex-revisor-ascii`; no se modifican.
- Configuración de Git (`diff.external`, `diff.<driver>.textconv`, `core.fsmonitor`, `core.pager`) que ya actúe por defecto: no se puede controlar desde la regex.
- `.claude/settings.json`, `.microharness/**`, `docs/**`, README, agentes y skills.
