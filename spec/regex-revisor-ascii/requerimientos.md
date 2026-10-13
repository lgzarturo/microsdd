# QUÉ: requisitos

## Objetivo
Endurecer las dos expresiones de la allowlist del revisor en `.claude/hooks/pretool.py`. El checker solo debe aceptar dígitos ASCII en la versión de Python. Las inspecciones Git (`git diff` y `git status`) no deben permitir ejecutar comandos, redirigir ni escribir archivos. Los usos legítimos de solo lectura deben seguir funcionando, incluidas las rutas no ASCII.

## Precondiciones
- PRE-01: el programador autorizó, solo para esta tarea, que el implementador edite `.claude/hooks/pretool.py`. Si la guardia activa lo deniega, el líder entrega el parche al humano; no se planean rodeos.
- Hecho comprobado: la expresión Git actual `git (diff|status)(?: [^;&|\n]+)?` permite, en Bash y PowerShell, `git diff $(rm -rf src)`, ``git diff `rm -rf src` ``, `git diff > README.md`, `git status < x` y `git diff --output=README.md`.
- Hecho comprobado: la expresión del checker usa `\d`, que en un `str` de Python acepta dígitos Unicode (`3.١٠`).

## Requisitos EARS
- REQ-01: WHEN el revisor ejecuta con `Bash` o `PowerShell` un comando `git diff` o `git status` cuyos argumentos son tokens de caracteres seguros separados por un único espacio, THE hook SHALL permitirlo (devolver `None`).
- REQ-02: IF un comando Git del revisor contiene `$`, comillas invertidas, `<`, `>`, paréntesis, `;`, `&`, `|`, saltos de línea, comillas, llaves o espacios dobles, THEN THE hook SHALL denegarlo.
- REQ-03: IF un comando Git del revisor incluye un token `--output`, `--output=…` o `--ext-diff`, THEN THE hook SHALL denegarlo.
- REQ-04: IF la versión indicada en `uv run … --python` contiene dígitos que no son ASCII, THEN THE hook SHALL denegar el comando del checker.
- REQ-05: THE hook SHALL mantener sin cambios el resto de su lógica y el comportamiento de los casos cubiertos por las pruebas actuales.

## Criterios de aceptación
- AC-01: En `Bash` y `PowerShell` (un `subTest` por comando) se permiten: `git diff`, `git status`, `git status --short`, `git diff --stat`, `git diff -w -- .microharness/sdd.py`, `git diff -U0 -- README.md`, `git diff HEAD~1 -- .claude/hooks/pretool.py` y `git diff -- spec/x/diseño.md`.
- AC-02: En `Bash` y `PowerShell` (un `subTest` por comando) se deniegan: `git diff $(rm -rf src)`, ``git diff `rm -rf src` ``, `git diff > README.md`, `git status < x`, `git diff --output=README.md`, `git diff --output README.md` y `git diff --ext-diff`.
- AC-03: Se deniega `uv run --no-project --python 3.١٠ .microharness/sdd.py check fix-a --run`, y también su variante entre comillas simples `'>=3.١٠'`.
- AC-04: `test_reviewer_edits_blocked`, `test_reviewer_checker_prefixes` y `test_reviewer_powershell_uses_allowlist` pasan sin modificarse, y la suite completa (`python -m unittest discover -s tests -v`) pasa.
- AC-05: El diff de `.claude/hooks/pretool.py` cambia solo las dos expresiones regulares del bloque del revisor.

## Fuera de alcance
- `.claude/settings.json`, `.microharness/sdd.py`, `docs/**`, `.microharness/memory.json`, agentes y skills.
- Otros subcomandos Git (`log`, `show`) y el soporte de reflogs con llaves (`HEAD@{1}`), globs o rutas con espacios o comillas.
- El bloqueo de `--no-index`, `--textconv` y abreviaturas de opciones largas (ver `diseño.md`).
- README: no se modifica; no afirma qué comandos Git admite el revisor (comprobado con búsqueda de `git diff`/`git status`).
