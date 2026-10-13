# PASOS: trabajo verificable

Orden TDD: pruebas RED primero, implementación mínima, README, verificación.

## Pruebas (RED) — `tests/test_installer.py`
- [ ] T01 (AC-01, AC-07, AC-09): cambiar `run_install` para inyectar `uv=` (por defecto `[sys.executable, '-c', 'print("uv 0.0.0")']`) en lugar de `python=`; adaptar `test_smoke_requires_reviewer_read_only_reason` a `uv=`.
- [ ] T02 (AC-02): reemplazar `test_broken_or_old_python3_fails_without_writing` por una prueba con `uv` inyectado que sale con 49: código 1, salida contiene `uv`, snapshot sin cambios.
- [ ] T03 (AC-03): prueba con `uv=None` y `PATH` = solo el directorio de `git` (omitir si allí existe `uv`/`uv.exe`): código 1, salida contiene `uv`, snapshot sin cambios.
- [ ] T04 (AC-04): reemplazar `test_windows_ignores_python3_cmd_shim` por la variante con `uv.cmd` (solo Windows): código 1, salida contiene `.cmd`, snapshot sin cambios.
- [ ] T05 (AC-05): prueba con `PATH` = solo el directorio de `git` (omitir si allí existe `python3`) y `uv` inyectado válido: código 0 y salida sin `python3`.
- [ ] T06 (AC-06): prueba que registra las llamadas a `installer.subprocess.run` (con `side_effect` al original) durante una instalación limpia: argv con `sdd.py`/`pretool.py` tienen `argv[0] == sys.executable`; ninguna llamada con `argv[0]` distinto de `sys.executable` tiene nombre base que empiece por `python3`.
- [ ] T07: ejecutar `python -m unittest discover -s tests -v` y confirmar que las pruebas nuevas/adaptadas fallan (RED) por la interfaz y el requisito antiguos.

## Implementación — `src/microsdd/installer.py`
- [ ] T08 (AC-02, AC-03, AC-04): sustituir `check_python` por `check_uv` y reescribir `remediation` para `uv` por SO; eliminar `VERSION_CODE`, la rama de alias de Store y `import re` si queda sin uso.
- [ ] T09 (AC-01, AC-05, AC-06): en `install()`, renombrar `python` a `uv`, llamar `check_uv`, ejecutar init y smoke con `sys.executable`; mensaje de error de init sin `python3`. `main()` pasa `uv=None`.
- [ ] T10 (AC-01..AC-07, AC-09): ejecutar la suite hasta verde (GREEN).

## Documentación — `README.md`
- [ ] T11 (AC-08): actualizar líneas 74 y 84 de la sección 2 y añadir la nota `uvx --no-cache --from <ruta o git+url> microsdd install`.
- [ ] T12 (AC-08): extraer solo la sección 2 de `README.md` (desde la línea que empieza por `## 2. ` hasta antes de la que empieza por `## 3. `) y comprobar que en esa sección no aparecen `python3 .microharness/sdd.py init` ni `python3.exe`, y que sí aparece `uvx --no-cache --from`.

## Verificación
- [ ] T13 (AC-01..AC-09): `sh .microharness/python.sh .microharness/sdd.py check instalador-sin-python3 --run` sin errores; `git status` solo muestra archivos de `scope.allowed_paths` más `spec/instalador-sin-python3/` y `.microharness/memory.json`.
