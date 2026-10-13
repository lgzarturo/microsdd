# PASOS: trabajo verificable

- [ ] T01 (AC-01, AC-02): en `tests/test_sdd.py`, pruebas nuevas de `new()` sin `config.json`, con ambas claves y con cada clave por separado (archivo en `sdd.MEMORY.parent / 'config.json'`). Ejecutar y comprobar que fallan (rojo).
- [ ] T02 (AC-03, AC-04, AC-05): pruebas nuevas de `validate()`: modelo distinto en `pendiente`/`proceso` con mensaje que contiene ambos modelos y `.microharness/config.json`; modelo igual sin error; `effort` inválido con lista de niveles; `effort` válido distinto del configurado sin error; tarea `terminado` sin error de modelo. Rojo.
- [ ] T03 (AC-06): pruebas nuevas de `main()` con los seis `config.json` inválidos para `new y` y `check fix-sesiones --no-scope`: código 1, `ERROR:` y `config.json` en stderr, sin `spec/y/` y `memory.json` byte a byte igual. Rojo.
- [ ] T04 (AC-01..AC-06): en `.microharness/sdd.py`, añadir `DEFAULT_MODEL`, `DEFAULT_EFFORT`, `EFFORTS` y `config()`; usarlos en `new()` (leyendo la configuración antes de escribir nada) y en `validate()` según el plan. Ejecutar T01-T03 (verde) y la suite completa.
- [ ] T05 (AC-08): actualizar `README.md` (secciones 3 y 6 y, si procede, una línea en la 8) con el archivo, formato, valores por defecto, exención de `terminado`, pasos manuales para cambiar de modelo y efecto sobre tareas abiertas.
- [ ] T06 (AC-09): crear `assets/eval-esfuerzo.md` con el protocolo y la declaración de no ejecutado, sin resultados.
- [ ] T07 (AC-10): actualizar D-04 en `assets/decisiones-diseno.md`.
- [ ] T08 (AC-07): comprobar `git diff --stat -- src/microsdd/installer.py pyproject.toml` vacío y ejecutar `sh .microharness/python.sh -m unittest discover -s tests -v` con código 0; `sh .microharness/python.sh .microharness/sdd.py check modelo-configurable --run`.
- [ ] T09 (AC-10): al cierre, el líder añade a `docs/arquitectura.md` el invariante de `.microharness/config.json`.
