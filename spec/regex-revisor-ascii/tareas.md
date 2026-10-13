# PASOS: trabajo verificable

- [ ] T01 (AC-01, AC-02): En `tests/test_sdd.py`, clase `HookTests`, añadir `test_reviewer_git_allowlist`. Debe recorrer `('Bash', 'PowerShell')` y probar los permitidos de AC-01 con `assertIsNone` y los denegados de AC-02 con `assertIsNotNone`, con un `subTest(herramienta=…, comando=…)` por caso. Seguir el patrón de carga con `importlib` de las pruebas existentes.
- [ ] T02 (AC-03): En `tests/test_sdd.py`, añadir `test_reviewer_checker_ascii_digits`. Debe denegar `uv run --no-project --python 3.١٠ .microharness/sdd.py check fix-a --run` y la variante `--python '>=3.١٠'`.
- [ ] T03 (AC-01..AC-03): Ejecutar `python -m unittest discover -s tests -v`. Las pruebas nuevas de los casos peligrosos y de `3.١٠` deben fallar (TDD rojo) y las demás deben pasar.
- [ ] T04 (AC-03, AC-05): En `.claude/hooks/pretool.py`, cambiar las tres apariciones de `\d` del checker por `[0-9]`.
- [ ] T05 (AC-01, AC-02, AC-05): En `.claude/hooks/pretool.py`, sustituir la expresión Git por `git (diff|status)(?: (?!--output(?:[= ]|$)|--ext-diff(?: |$))[\w./:^~=+,-]+)*`, tal como está en `diseño.md`.
- [ ] T06 (AC-04): Ejecutar `python -m unittest discover -s tests -v`. Toda la suite debe pasar y las tres pruebas existentes del revisor no deben haberse modificado.
- [ ] T07 (AC-05): Revisar `git diff -- .claude/hooks/pretool.py`. Solo deben cambiar las dos expresiones y ningún otro archivo fuera de `allowed_paths`.
