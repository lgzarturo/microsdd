# PASOS: trabajo verificable

- [ ] T01 (AC-01, AC-02): En `tests/test_sdd.py`, clase `HookTests`, añadir `test_reviewer_git_extra_options` siguiendo el patrón de carga con `importlib` de `test_reviewer_git_allowlist`. Recorrer `('Bash', 'PowerShell')`: `assertIsNotNone` para los diez comandos de AC-01 y `assertIsNone` para los siete de AC-02, con `subTest(herramienta=…, comando=…)`. No modificar pruebas existentes.
- [ ] T02 (AC-01): Ejecutar `python -m unittest discover -s tests -v`. Los casos denegados de AC-01 deben fallar (TDD rojo); el resto de la suite debe pasar.
- [ ] T03 (AC-01, AC-02, AC-04): En `.claude/hooks/pretool.py`, mediante Bash (PRE-01), sustituir solo la expresión Git del bloque del revisor por la de `plan.md`: `git (diff|status)(?: (?!--output(?:[= ]|$)|--ext-diff(?: |$)|--textconv(?:[= ]|$)|--open-files-in-pager(?:[= ]|$)|-[^ -]*O)[\w./:^~=+,-]+)*`.
- [ ] T04 (AC-01, AC-02, AC-03): Ejecutar `python -m unittest discover -s tests -v`. Toda la suite debe pasar, incluidas las cinco pruebas existentes del revisor sin cambios.
- [ ] T05 (AC-04): Revisar `git diff -- .claude/hooks/pretool.py` y `git status --short`: solo cambia la expresión Git y ningún archivo fuera de `allowed_paths`.
