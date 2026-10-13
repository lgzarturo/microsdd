# PASOS: trabajo verificable

Antes de delegar: el líder resuelve D-01 y D-02 y el humano restaura `.claude/settings.json` a `HEAD`. Aprobación (humano, en su terminal):
`sh .microharness/python.sh .microharness/sdd.py approve fusion-settings-toggle spec --by 'Arturo L. Gómez' --evidence '<texto>'`

## RED (pruebas primero)
- [x] T01 (AC-01, AC-02, AC-03, AC-04, AC-05): `tests/test_installer.py`: reemplazar `test_different_settings_is_kept_and_alternate_written` por la fusión con graphify (incluye `json.tool` con `sys.executable -m json.tool`); ajustar `test_modified_own_file_conflicts_without_force_and_updates_with_force` (tras el primer `install`, `settings.json` queda fusionado y `--force` no lo vuelve a cambiar); añadir casos de AC-01, AC-03, AC-04 y AC-05.
- [x] T02 (AC-06, AC-07, AC-08, AC-09, AC-10, AC-11): archivo nuevo `tests/test_fusion_settings.py`: `toggle`, `status`, `uninstall` y `main()` con `mock.patch.dict(os.environ)` y `sys.stdin` sustituido (TTY verdadero/falso, `None`), usando `snapshot()` para comprobar que no se escribe.
- [x] T03 (AC-12, AC-13): en `tests/test_fusion_settings.py`: `pretool.run()` con las listas de AC-12 (roles × herramientas, `subTest`) y las ediciones de AC-13 con `cwd` temporal; arranque del hook con `uv` (`skipUnless(shutil.which('uv'))`, `subprocess.run([...], input='{}')`).
- [x] T04 (AC-14): `tests/test_api_publica.py`: incluir `installer.INSTALL_RECORD` en los conjuntos de AC-03/AC-04; en `tests/test_fusion_settings.py`, comprobar que `assets/proceso-versionado.md` no contiene `settings.microsdd.json`.
- [x] T05 (AC-01..AC-14): `python -m unittest discover -s tests -v`: las nuevas fallan (RED) y el resto pasa. El líder lo informa al humano.

## GREEN
- [x] T06 (AC-01, AC-02, AC-03, AC-04, AC-05): `src/microsdd/installer.py`: `merge`, `backup`, manifiesto `INSTALL_RECORD`, etiqueta `fusionar`, validación JSON en `plan()`, quitar `SETTINGS_ALT`, aviso de alterno heredado, `git add` con el manifiesto.
- [x] T07 (AC-06, AC-07, AC-08, AC-09): `src/microsdd/installer.py`: `unmerge`, `toggle`, `status`, `human_gate` y subcomandos `on`, `off`, `status` en `main()`.
- [x] T08 (AC-10, AC-11): `src/microsdd/installer.py`: `uninstall` con precomprobación, `--force` y restauración de `CLAUDE.md`.
- [x] T09 (AC-14): `README.md` y `assets/proceso-versionado.md` según el plan, punto 12.
- [x] T10 (AC-14): según D-01: `.claude/skills/sdd/SKILL.md` y `CLAUDE.md` línea 3.
- [x] T11 (AC-12, AC-13): último, según D-01: `.claude/hooks/pretool.py`: `TOGGLE_RE`, `SETTINGS_RE`, `guard_bash` y su llamada en `run()`; fail-closed, revisor y `protected_bash` sin cambios.

## Verificación
- [x] T12 (AC-15): `python -m unittest discover -s tests -v` termina en 0; `git diff --stat` solo muestra rutas de `scope.allowed_paths`; `git diff HEAD -- .claude/settings.json` vacío; `tests/test_sdd.py` sin cambios.
- [ ] T13 (AC-01..AC-15): el revisor ejecuta `sh .microharness/python.sh .microharness/sdd.py check fusion-settings-toggle --run` y emite el dictamen; el líder lo registra con `sdd.py review`.
- [ ] T14 (AC-14, AC-15): cierre: el humano aprueba en su terminal (`approve fusion-settings-toggle close`); el líder ejecuta `commit-check` con el asunto acordado en D-03 y hace el commit con `git add` explícito.
