# PASOS: trabajo verificable

- [ ] T01 (AC-01, AC-02, AC-03): en `tests/test_sdd.py`, añadir a `MicroSDDTests` una prueba con `skipUnless(shutil.which('git'))` que haga `git init` y `git config core.quotePath true` en `sdd.ROOT` (sin commits), cree `fuera/configuración.txt` y compruebe: `'spec/fix-sesiones/diseño.md'` en `sdd.diff_files()`; ningún error de `sdd.validate('fix-sesiones')` menciona `diseño.md`; y `'Archivo modificado fuera de scope: fuera/configuración.txt'` está en esos errores.
- [ ] T02 (AC-04): ejecutar `python -m unittest discover -s tests -v` y confirmar que la prueba nueva falla (rojo) antes de tocar `sdd.py`.
- [ ] T03 (AC-01, AC-02, AC-03): en `.microharness/sdd.py`, `diff_files()`, añadir `'-c', 'core.quotePath=false'` tras `'git'` en ambos comandos y sustituir `text=True` por `encoding='utf-8'` en el `subprocess.run` del bucle. Nada más.
- [ ] T04 (AC-04): ejecutar de nuevo la suite completa y confirmar que todo pasa.
- [ ] T05 (AC-02): verificar `python .microharness/sdd.py check fix-quotepath-diff` sin `--no-scope` y comprobar que no aparece error de alcance por `diseño.md`.
