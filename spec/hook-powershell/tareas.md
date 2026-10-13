# PASOS: trabajo verificable

- [ ] T01 (AC-01, AC-02, AC-03; `tests/test_sdd.py`): añadir en `HookTests` una prueba que cargue `pretool.py` igual que las vecinas y compruebe que, con `tool_name: 'PowerShell'`, el revisor es denegado con `rm -rf src` y permitido con `python .microharness/sdd.py check fix-a --run` y con `git status`. Ejecutar la suite: debe fallar solo el caso denegado (TDD).
- [ ] T02 (AC-04; `tests/test_sdd.py`): en `SettingsTests.pretool_hook()`, cambiar la igualdad literal del matcher por `set(matcher.split('|')) == {'Write', 'Edit', 'MultiEdit', 'NotebookEdit', 'Bash', 'PowerShell'}` y mantener las aserciones de una entrada y un hook. Ejecutar la suite: deben fallar las pruebas de `SettingsTests` que usan `pretool_hook()` (TDD).
- [ ] T03 (AC-01, AC-02, AC-03; `.claude/hooks/pretool.py`): cambiar `if tool == 'Bash' and agent == 'revisor':` por `if tool in ('Bash', 'PowerShell') and agent == 'revisor':`, sin otros cambios. Antes hay que resolver R1, porque la guardia niega al implementador editar `.claude/`.
- [ ] T04 (AC-05; `README.md`): en la fila «Acceso por rol» de la sección 7, sustituir «`Bash`» por «`Bash`/`PowerShell`», sin otros cambios.
- [ ] T05 (AC-04; `.claude/settings.json`, último cambio): poner el matcher `Write|Edit|MultiEdit|NotebookEdit|Bash|PowerShell` sin tocar `type`, `command`, `args` ni `onFailure`. Antes hay que resolver R1.
- [ ] T06 (AC-03, AC-06): ejecutar `python -m unittest discover -s tests -v` (todo debe pasar) y `git diff --stat` (solo deben aparecer archivos de `allowed_paths`).
