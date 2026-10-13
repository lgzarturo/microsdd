# PASOS: trabajo verificable

Archivos: `tests/test_sdd.py` (pruebas nuevas) y `.microharness/sdd.py` (solo `diff_files()`, excepción autorizada por el programador 2026-10-12).

- [ ] T01 (AC-05): ejecutar `python -m unittest discover -s tests -v` antes de cambiar nada y registrar que la suite existente pasa (línea base).
- [ ] T02 (AC-01, AC-02, AC-03, AC-04): en `tests/test_sdd.py`, añadir un auxiliar mínimo de prueba que haga `git init` en `sdd.ROOT`, configure `user.email` y `user.name` locales y cree un commit inicial (sin incluir `spec/fix-sesiones/`).
- [ ] T03 (AC-01): prueba RED: archivo rastreado no ASCII modificado tras el commit y `spec/x/diseño.md` sin seguimiento; `diff_files()` debe ser exactamente esas rutas y cada una debe existir con `(sdd.ROOT / ruta).is_file()`.
- [ ] T04 (AC-02): prueba RED: `validate('fix-sesiones')` no contiene error de fuera de scope para `spec/fix-sesiones/diseño.md`.
- [ ] T05 (AC-03): prueba RED: `code_fingerprint(['src/**'])` cambia al modificar el contenido de un archivo permitido no ASCII.
- [ ] T06 (AC-04): prueba RED: `src/con espacio.py` sin seguimiento aparece con su ruta exacta en `diff_files()` y existe en disco.
- [ ] T07 (AC-01, AC-02, AC-03): ejecutar la suite y confirmar que las pruebas de T03-T05 fallan con el código actual por el defecto descrito (no por errores de preparación). T06 puede pasar ya en RED; registrarlo.
- [ ] T08 (AC-01, AC-02, AC-03, AC-04): GREEN: en `.microharness/sdd.py`, `diff_files()`, añadir `-z` a ambos comandos git, reemplazar `text=True` por `encoding='utf-8'` en la llamada que los ejecuta y separar con `split('\0')` descartando vacíos. No tocar la detección de repositorio, `validate`, `code_fingerprint` ni el hook.
- [ ] T09 (AC-01, AC-02, AC-03, AC-04, AC-05): ejecutar `python -m unittest discover -s tests -v` y confirmar suite completa en verde.
- [ ] T10 (AC-02): ejecutar `python .microharness/sdd.py check fix-sdd-rutas-unicode` y confirmar que ya no aparece `spec/fix-sdd-rutas-unicode/diseño.md` como fuera de scope.
- [ ] T11 (AC-05): revisar `git diff` y confirmar que solo cambiaron `.microharness/sdd.py` (únicamente `diff_files()`) y `tests/test_sdd.py`, además de los archivos de esta spec.
